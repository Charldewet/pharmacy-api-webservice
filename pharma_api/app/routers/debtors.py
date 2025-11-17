"""
Debtor management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from typing import List, Optional
from datetime import datetime
import os
import sys
import tempfile
import csv
import io
from pathlib import Path

# Add project root to Python path to import PDF_PARSER_COMPLETE
# This ensures PDF_PARSER_COMPLETE.py in the project root is importable
# Path calculation: from pharma_api/app/routers/debtors.py go up 3 levels to project root
_project_root = Path(__file__).resolve().parents[3]
_project_root_str = str(_project_root)
if _project_root_str not in sys.path:
    sys.path.insert(0, _project_root_str)

# Try to import PDF_PARSER_COMPLETE, fallback to error if not found
try:
    from PDF_PARSER_COMPLETE import extract_debtors_strictest_names
except ImportError:
    # Check if file exists in project root
    pdf_parser_file = _project_root / "PDF_PARSER_COMPLETE.py"
    if pdf_parser_file.exists():
        # File exists but import failed - might be a syntax error
        raise ImportError(
            f"PDF_PARSER_COMPLETE.py exists at {pdf_parser_file} but could not be imported. "
            "Please check for syntax errors in the file."
        )
    else:
        raise ImportError(
            f"PDF_PARSER_COMPLETE module not found. "
            f"Expected PDF_PARSER_COMPLETE.py at: {pdf_parser_file}. "
            f"Project root: {_project_root_str}"
        )

from ..db import get_conn
from ..auth import get_current_user_id
from ..schemas import (
    Debtor, DebtorPage, DebtorStatistics, UploadDebtorReportResponse,
    SendEmailRequest, SendSMSRequest, SendCommunicationResponse,
    CommunicationResult, CommunicationError, CommunicationLog, DebtorReport,
    DownloadCSVRequest, DownloadPDFRequest
)
from ..utils.debtors import (
    is_medical_aid_control_account,
    create_email_template, create_sms_template, decrypt_api_key,
    debtor_to_dict
)

router = APIRouter(prefix="/pharmacies/{pharmacy_id}/debtors", tags=["debtors"])


def check_pharmacy_access(user_id: int, pharmacy_id: int, require_write: bool = False) -> None:
    """Check if user has access to a pharmacy"""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT can_read, can_write
            FROM pharma.user_pharmacies
            WHERE user_id = %s AND pharmacy_id = %s
        """, (user_id, pharmacy_id))
        
        access = cur.fetchone()
        if not access:
            raise HTTPException(status_code=403, detail=f"Access denied to pharmacy {pharmacy_id}")
        
        if not access['can_read']:
            raise HTTPException(status_code=403, detail=f"Read access denied to pharmacy {pharmacy_id}")
        
        if require_write and not access['can_write']:
            raise HTTPException(status_code=403, detail=f"Write access denied to pharmacy {pharmacy_id}")


@router.post("/upload", response_model=UploadDebtorReportResponse)
def upload_debtor_report(
    pharmacy_id: int,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id)
):
    """Upload and process a debtor report PDF"""
    check_pharmacy_access(user_id, pharmacy_id, require_write=True)
    
    # Verify pharmacy exists
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT pharmacy_id, name FROM pharma.pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
        pharmacy = cur.fetchone()
        if not pharmacy:
            raise HTTPException(status_code=404, detail=f"Pharmacy {pharmacy_id} not found")
    
    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        content = file.file.read()
        tmp_file.write(content)
        tmp_path = Path(tmp_file.name)
    
    try:
        # Parse PDF
        df = extract_debtors_strictest_names(str(tmp_path))
        
        # Create report record
        with get_conn() as conn, conn.cursor() as cur:
            # IMPORTANT: Delete ALL existing debtors for this pharmacy first (complete replacement)
            cur.execute("DELETE FROM pharma.debtors WHERE pharmacy_id = %s", (pharmacy_id,))
            deleted_count = cur.rowcount
            
            cur.execute("""
                INSERT INTO pharma.debtor_reports 
                (pharmacy_id, filename, file_path, uploaded_by, status)
                VALUES (%s, %s, %s, %s, 'processing')
                RETURNING id
            """, (pharmacy_id, file.filename, str(tmp_path), user_id))
            report_id = cur.fetchone()['id']
            
            # Process and save debtors
            total_outstanding = 0.0
            debtors_data = []
            
            for _, row in df.iterrows():
                # Check if medical aid account
                is_medical_aid = is_medical_aid_control_account(row.get('name', ''))
                
                # Insert new debtor (no need to check for existing since we deleted all)
                cur.execute("""
                    INSERT INTO pharma.debtors
                    (pharmacy_id, report_id, acc_no, name, current, d30, d60, d90, d120, d150, d180, balance, email, phone, is_medical_aid_control)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at, updated_at
                """, (
                    pharmacy_id,
                    report_id,
                    str(row['acc_no']),
                    str(row['name']),
                    float(row.get('current', 0) or 0),
                    float(row.get('d30', 0) or 0),
                    float(row.get('d60', 0) or 0),
                    float(row.get('d90', 0) or 0),
                    float(row.get('d120', 0) or 0),
                    float(row.get('d150', 0) or 0),
                    float(row.get('d180', 0) or 0),
                    float(row.get('balance', 0) or 0),
                    row.get('email') or None,
                    row.get('phone') or None,
                    is_medical_aid
                ))
                new_debtor = cur.fetchone()
                debtor_id = new_debtor['id']
                
                if not is_medical_aid:
                    total_outstanding += float(row.get('balance', 0) or 0)
                
                # Get full debtor record
                cur.execute("""
                    SELECT * FROM pharma.debtors WHERE id = %s
                """, (debtor_id,))
                debtor_row = cur.fetchone()
                debtors_data.append(debtor_to_dict(debtor_row))
            
            # Update report
            non_medical_aid_count = len([d for d in debtors_data if not d['is_medical_aid_control']])
            cur.execute("""
                UPDATE pharma.debtor_reports SET
                    total_accounts = %s,
                    total_outstanding = %s,
                    status = 'completed'
                WHERE id = %s
            """, (non_medical_aid_count, total_outstanding, report_id))
            
            conn.commit()
        
        return UploadDebtorReportResponse(
            report_id=report_id,
            total_accounts=non_medical_aid_count,
            total_outstanding=total_outstanding,
            debtors=debtors_data
        )
        
    except Exception as e:
        # Update report status to failed
        with get_conn() as conn, conn.cursor() as cur:
            try:
                cur.execute("""
                    UPDATE pharma.debtor_reports SET
                        status = 'failed',
                        error_message = %s
                    WHERE id = %s
                """, (str(e), report_id))
                conn.commit()
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
    finally:
        # Clean up temp file
        try:
            if tmp_path.exists():
                os.unlink(tmp_path)
        except:
            pass


@router.get("/reports", response_model=List[DebtorReport])
def get_debtor_reports(
    pharmacy_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """Get list of all uploaded debtor reports for a pharmacy"""
    check_pharmacy_access(user_id, pharmacy_id)
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT * FROM pharma.debtor_reports
            WHERE pharmacy_id = %s
            ORDER BY uploaded_at DESC
        """, (pharmacy_id,))
        
        reports = cur.fetchall()
        return [
            DebtorReport(
                id=report['id'],
                pharmacy_id=report['pharmacy_id'],
                filename=report['filename'],
                file_path=report.get('file_path'),
                uploaded_at=report['uploaded_at'],
                uploaded_by=report.get('uploaded_by'),
                total_accounts=report['total_accounts'],
                total_outstanding=float(report['total_outstanding']),
                status=report['status'],
                error_message=report.get('error_message')
            )
            for report in reports
        ]


@router.get("", response_model=DebtorPage)
def get_debtors(
    pharmacy_id: int,
    min_balance: Optional[float] = Query(None),
    ageing_buckets: Optional[str] = Query(None),
    has_email: Optional[bool] = Query(None),
    has_phone: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    exclude_medical_aid: bool = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=1000),
    user_id: int = Depends(get_current_user_id)
):
    """Get list of debtors with filtering and pagination"""
    check_pharmacy_access(user_id, pharmacy_id)
    
    with get_conn() as conn, conn.cursor() as cur:
        # Build query
        query = """
            SELECT * FROM pharma.debtors
            WHERE pharmacy_id = %s
        """
        params = [pharmacy_id]
        
        if exclude_medical_aid:
            query += " AND is_medical_aid_control = FALSE"
        
        if min_balance is not None:
            query += " AND (d60 + d90 + d120 + d150 + d180) > %s"
            params.append(min_balance)
        
        if ageing_buckets:
            buckets = [b.strip() for b in ageing_buckets.split(',') if b.strip()]
            if buckets:
                conditions = []
                for bucket in buckets:
                    if bucket in ['d30', 'd60', 'd90', 'd120', 'd150', 'd180']:
                        conditions.append(f"{bucket} > 0")
                if conditions:
                    query += " AND (" + " OR ".join(conditions) + ")"
        
        if has_email:
            query += " AND email IS NOT NULL AND email != ''"
        
        if has_phone:
            query += " AND phone IS NOT NULL AND phone != ''"
        
        if search:
            query += " AND (acc_no ILIKE %s OR name ILIKE %s OR email ILIKE %s OR phone ILIKE %s)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as subq"
        cur.execute(count_query, params)
        total = cur.fetchone()['total']
        
        # Add pagination
        query += " ORDER BY balance DESC LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        debtors = [debtor_to_dict(row) for row in rows]
        pages = (total + per_page - 1) // per_page
        
        return DebtorPage(
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            debtors=debtors
        )


@router.get("/statistics", response_model=DebtorStatistics)
def get_statistics(
    pharmacy_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """Get debtor statistics for a pharmacy"""
    check_pharmacy_access(user_id, pharmacy_id)
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total_accounts,
                COALESCE(SUM(balance), 0) as total_outstanding,
                COALESCE(SUM(current), 0) as current,
                COALESCE(SUM(d30), 0) as d30,
                COALESCE(SUM(d60), 0) as d60,
                COALESCE(SUM(d90), 0) as d90,
                COALESCE(SUM(d120), 0) as d120,
                COALESCE(SUM(d150), 0) as d150,
                COALESCE(SUM(d180), 0) as d180
            FROM pharma.debtors
            WHERE pharmacy_id = %s AND is_medical_aid_control = FALSE
        """, (pharmacy_id,))
        
        stats = cur.fetchone()
        
        return DebtorStatistics(
            total_accounts=stats['total_accounts'] or 0,
            total_outstanding=float(stats['total_outstanding'] or 0),
            current=float(stats['current'] or 0),
            d30=float(stats['d30'] or 0),
            d60=float(stats['d60'] or 0),
            d90=float(stats['d90'] or 0),
            d120=float(stats['d120'] or 0),
            d150=float(stats['d150'] or 0),
            d180=float(stats['d180'] or 0)
        )


@router.post("/send-email", response_model=SendCommunicationResponse)
def send_email(
    pharmacy_id: int,
    request: SendEmailRequest,
    user_id: int = Depends(get_current_user_id)
):
    """Send email reminders to debtors"""
    check_pharmacy_access(user_id, pharmacy_id, require_write=True)
    
    # Get pharmacy info
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT pharmacy_id, name, email, phone, banking_account, bank_name, sendgrid_api_key
            FROM pharma.pharmacies
            WHERE pharmacy_id = %s
        """, (pharmacy_id,))
        pharmacy = cur.fetchone()
        if not pharmacy:
            raise HTTPException(status_code=404, detail=f"Pharmacy {pharmacy_id} not found")
        
        # Get debtors
        cur.execute("""
            SELECT * FROM pharma.debtors
            WHERE pharmacy_id = %s AND id = ANY(%s) AND is_medical_aid_control = FALSE
        """, (pharmacy_id, request.debtor_ids))
        debtors = cur.fetchall()
        
        if not debtors:
            raise HTTPException(status_code=404, detail="No debtors found")
        
        # Check if SendGrid API key is configured
        if not pharmacy.get('sendgrid_api_key'):
            raise HTTPException(status_code=400, detail="SendGrid API key not configured for this pharmacy")
        
        sent = []
        errors = []
        
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            # Decrypt API key
            api_key = decrypt_api_key(pharmacy['sendgrid_api_key'])
            sg = sendgrid.SendGridAPIClient(api_key)
            
            for debtor_row in debtors:
                debtor = debtor_to_dict(debtor_row)
                
                if not debtor['email']:
                    errors.append(CommunicationError(
                        debtor_id=debtor['id'],
                        error="No email address"
                    ))
                    continue
                
                # Calculate arrears for selected buckets
                arrears_60_plus = sum([
                    debtor.get(bucket, 0) for bucket in request.ageing_buckets
                    if bucket in ['d60', 'd90', 'd120', 'd150', 'd180']
                ])
                
                # Create email content
                subject = f"Reminder: Account Overdue at {pharmacy['name']}"
                html_content = create_email_template(debtor, pharmacy, arrears_60_plus)
                
                try:
                    # Send via SendGrid
                    from_email = Email(pharmacy.get('email') or 'no-reply@example.com', pharmacy['name'])
                    to_email = To(debtor['email'])
                    mail = Mail(from_email, to_email, subject, Content('text/html', html_content))
                    response = sg.client.mail.send.post(request_body=mail.get())
                    
                    # Log communication
                    cur.execute("""
                        INSERT INTO pharma.communication_logs
                        (pharmacy_id, debtor_id, communication_type, recipient, subject, message, status, external_id, sent_at)
                        VALUES (%s, %s, 'email', %s, %s, %s, 'sent', %s, NOW())
                    """, (
                        pharmacy_id, debtor['id'], debtor['email'], subject, html_content,
                        str(response.status_code)
                    ))
                    
                    sent.append(CommunicationResult(
                        debtor_id=debtor['id'],
                        email=debtor['email'],
                        status='sent',
                        external_id=str(response.status_code)
                    ))
                    
                except Exception as e:
                    # Log failed communication
                    cur.execute("""
                        INSERT INTO pharma.communication_logs
                        (pharmacy_id, debtor_id, communication_type, recipient, subject, message, status, error_message)
                        VALUES (%s, %s, 'email', %s, %s, %s, 'failed', %s)
                    """, (
                        pharmacy_id, debtor['id'], debtor['email'], subject, html_content, str(e)
                    ))
                    
                    errors.append(CommunicationError(
                        debtor_id=debtor['id'],
                        error=str(e)
                    ))
            
            conn.commit()
            
        except ImportError:
            raise HTTPException(status_code=500, detail="SendGrid library not installed")
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Error sending emails: {str(e)}")
        
        return SendCommunicationResponse(sent=sent, errors=errors)


@router.post("/send-sms", response_model=SendCommunicationResponse)
def send_sms(
    pharmacy_id: int,
    request: SendSMSRequest,
    user_id: int = Depends(get_current_user_id)
):
    """Send SMS reminders to debtors"""
    check_pharmacy_access(user_id, pharmacy_id, require_write=True)
    
    # Get pharmacy info
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT pharmacy_id, name, email, phone, banking_account, bank_name, 
                   smsportal_client_id, smsportal_api_secret
            FROM pharma.pharmacies
            WHERE pharmacy_id = %s
        """, (pharmacy_id,))
        pharmacy = cur.fetchone()
        if not pharmacy:
            raise HTTPException(status_code=404, detail=f"Pharmacy {pharmacy_id} not found")
        
        # Get debtors
        cur.execute("""
            SELECT * FROM pharma.debtors
            WHERE pharmacy_id = %s AND id = ANY(%s) AND is_medical_aid_control = FALSE
        """, (pharmacy_id, request.debtor_ids))
        debtors = cur.fetchall()
        
        if not debtors:
            raise HTTPException(status_code=404, detail="No debtors found")
        
        # Check if SMS Portal credentials are configured
        if not pharmacy.get('smsportal_client_id') or not pharmacy.get('smsportal_api_secret'):
            raise HTTPException(status_code=400, detail="SMS Portal credentials not configured for this pharmacy")
        
        sent = []
        errors = []
        
        try:
            import requests
            
            # Decrypt credentials
            client_id = decrypt_api_key(pharmacy['smsportal_client_id'])
            api_secret = decrypt_api_key(pharmacy['smsportal_api_secret'])
            
            # SMS Portal API endpoint (adjust based on actual API)
            sms_url = "https://api.smsportal.com/v1/send"  # Update with actual endpoint
            
            for debtor_row in debtors:
                debtor = debtor_to_dict(debtor_row)
                
                if not debtor['phone']:
                    errors.append(CommunicationError(
                        debtor_id=debtor['id'],
                        error="No phone number"
                    ))
                    continue
                
                # Calculate arrears
                arrears_60_plus = sum([
                    debtor.get(bucket, 0) for bucket in request.ageing_buckets
                    if bucket in ['d60', 'd90', 'd120', 'd150', 'd180']
                ])
                
                # Create SMS content
                message = create_sms_template(debtor, pharmacy, arrears_60_plus)
                
                try:
                    # Send via SMS Portal
                    headers = {
                        'Authorization': f'Bearer {api_secret}',  # Adjust based on actual API
                        'Content-Type': 'application/json'
                    }
                    payload = {
                        'destination': debtor['phone'],
                        'content': message,
                        'clientId': client_id
                    }
                    
                    response = requests.post(sms_url, json=payload, headers=headers)
                    response.raise_for_status()
                    result = response.json()
                    
                    # Log communication
                    external_id = result.get('id') or result.get('messageId', '')
                    cur.execute("""
                        INSERT INTO pharma.communication_logs
                        (pharmacy_id, debtor_id, communication_type, recipient, message, status, external_id, sent_at)
                        VALUES (%s, %s, 'sms', %s, %s, 'sent', %s, NOW())
                    """, (
                        pharmacy_id, debtor['id'], debtor['phone'], message, external_id
                    ))
                    
                    sent.append(CommunicationResult(
                        debtor_id=debtor['id'],
                        phone=debtor['phone'],
                        status='sent',
                        external_id=external_id
                    ))
                    
                except Exception as e:
                    # Log failed communication
                    cur.execute("""
                        INSERT INTO pharma.communication_logs
                        (pharmacy_id, debtor_id, communication_type, recipient, message, status, error_message)
                        VALUES (%s, %s, 'sms', %s, %s, 'failed', %s)
                    """, (
                        pharmacy_id, debtor['id'], debtor['phone'], message, str(e)
                    ))
                    
                    errors.append(CommunicationError(
                        debtor_id=debtor['id'],
                        error=str(e)
                    ))
            
            conn.commit()
            
        except ImportError:
            raise HTTPException(status_code=500, detail="requests library not installed")
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Error sending SMS: {str(e)}")
        
        return SendCommunicationResponse(sent=sent, errors=errors)


@router.post("/download-csv")
def download_csv(
    pharmacy_id: int,
    request: Optional[DownloadCSVRequest] = None,
    user_id: int = Depends(get_current_user_id)
):
    """Download debtors as CSV"""
    check_pharmacy_access(user_id, pharmacy_id)
    
    with get_conn() as conn, conn.cursor() as cur:
        query = """
            SELECT acc_no, name, current, d30, d60, d90, d120, d150, d180, balance, email, phone
            FROM pharma.debtors
            WHERE pharmacy_id = %s AND is_medical_aid_control = FALSE
        """
        params = [pharmacy_id]
        
        if request and request.debtor_ids:
            query += " AND id = ANY(%s)"
            params.append(request.debtor_ids)
        
        if request and request.min_balance is not None:
            query += " AND (d60 + d90 + d120 + d150 + d180) > %s"
            params.append(request.min_balance)
        
        query += " ORDER BY balance DESC"
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Account No', 'Name', 'Current', '30 Days', '60 Days', '90 Days', 
                        '120 Days', '150 Days', '180 Days', 'Balance', 'Email', 'Phone'])
        
        for row in rows:
            writer.writerow([
                row['acc_no'], row['name'],
                row['current'], row['d30'], row['d60'], row['d90'],
                row['d120'], row['d150'], row['d180'], row['balance'],
                row.get('email') or '', row.get('phone') or ''
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=debtors_{pharmacy_id}.csv"}
        )


@router.post("/download-pdf")
def download_pdf(
    pharmacy_id: int,
    request: Optional[DownloadPDFRequest] = None,
    user_id: int = Depends(get_current_user_id)
):
    """Download debtors as PDF"""
    check_pharmacy_access(user_id, pharmacy_id)
    
    try:
        from fpdf import FPDF
        
        with get_conn() as conn, conn.cursor() as cur:
            query = """
                SELECT acc_no, name, current, d30, d60, d90, d120, d150, d180, balance
                FROM pharma.debtors
                WHERE pharmacy_id = %s AND is_medical_aid_control = FALSE
            """
            params = [pharmacy_id]
            
            if request and request.debtor_ids:
                query += " AND id = ANY(%s)"
                params.append(request.debtor_ids)
            
            if request and request.ageing_buckets:
                buckets = request.ageing_buckets
                if buckets:
                    conditions = []
                    for bucket in buckets:
                        if bucket in ['d30', 'd60', 'd90', 'd120', 'd150', 'd180']:
                            conditions.append(f"{bucket} > 0")
                    if conditions:
                        query += " AND (" + " OR ".join(conditions) + ")"
            
            query += " ORDER BY balance DESC"
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            # Create PDF
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"Debtor Report - Pharmacy {pharmacy_id}", ln=1)
            pdf.ln(5)
            
            # Table header
            pdf.set_font("Arial", "B", 10)
            pdf.cell(25, 8, "Acc No", 1)
            pdf.cell(60, 8, "Name", 1)
            pdf.cell(20, 8, "Current", 1)
            pdf.cell(20, 8, "60 Days", 1)
            pdf.cell(20, 8, "90 Days", 1)
            pdf.cell(20, 8, "Balance", 1)
            pdf.ln()
            
            # Table rows
            pdf.set_font("Arial", "", 9)
            for row in rows:
                pdf.cell(25, 8, str(row['acc_no']), 1)
                pdf.cell(60, 8, row['name'][:30], 1)  # Truncate long names
                pdf.cell(20, 8, f"{row['current']:.2f}", 1)
                pdf.cell(20, 8, f"{row['d60']:.2f}", 1)
                pdf.cell(20, 8, f"{row['d90']:.2f}", 1)
                pdf.cell(20, 8, f"{row['balance']:.2f}", 1)
                pdf.ln()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                pdf_path = tmp_file.name
                pdf.output(pdf_path)
            
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=f"debtors_{pharmacy_id}.pdf"
            )
            
    except ImportError:
        raise HTTPException(status_code=500, detail="fpdf library not installed")


@router.get("/{debtor_id}/communications", response_model=List[CommunicationLog])
def get_debtor_communications(
    pharmacy_id: int,
    debtor_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """Get communication history for a debtor"""
    check_pharmacy_access(user_id, pharmacy_id)
    
    with get_conn() as conn, conn.cursor() as cur:
        # Verify debtor belongs to pharmacy
        cur.execute("""
            SELECT id FROM pharma.debtors
            WHERE id = %s AND pharmacy_id = %s
        """, (debtor_id, pharmacy_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Debtor not found")
        
        cur.execute("""
            SELECT * FROM pharma.communication_logs
            WHERE debtor_id = %s
            ORDER BY created_at DESC
        """, (debtor_id,))
        
        logs = cur.fetchall()
        return [
            CommunicationLog(
                id=log['id'],
                pharmacy_id=log['pharmacy_id'],
                debtor_id=log['debtor_id'],
                communication_type=log['communication_type'],
                recipient=log['recipient'],
                subject=log.get('subject'),
                message=log['message'],
                status=log['status'],
                external_id=log.get('external_id'),
                error_message=log.get('error_message'),
                sent_at=log.get('sent_at'),
                created_at=log['created_at']
            )
            for log in logs
        ]

