# Stock On Hand (SOH) API Implementation Issues - Analysis & Solution

## 🔍 Issues Found

### Issue #1: 422 Unprocessable Entity Error

**Problem:** The frontend team is requesting `limit=1000` but the endpoint has a maximum limit of `200`.

**Root Cause:**
- Endpoint: `GET /pharmacies/{pharmacyId}/stock-activity`
- Current limit constraint: `limit: int = Query(50, ge=1, le=200)`
- Frontend request: `limit=1000` ❌

**Error:** FastAPI validation rejects the request with `422 Unprocessable Entity` because `1000 > 200`.

**Fix:** Change `limit=1000` to `limit=200` in the frontend proxy code.

---

### Issue #2: Product Not Found (Even When It Exists)

**Problem:** Product `LP9037679` exists on Nov 12, 2025 with SOH = 58.668, but it's not returned in the first 200 results.

**Root Cause:**
- The `/stock-activity` endpoint returns products sorted by `sales_val DESC`
- Product `LP9037679` has sales of R25.17 on Nov 12
- It's at position **347 out of 416** products
- With `limit=200`, only the top 200 products by sales value are returned
- Product `LP9037679` is NOT in the top 200 ❌

**Why This Happens:**
- The endpoint only returns products that had **activity (sales)** on that specific date
- Products are sorted by sales value (highest first)
- Low-selling products won't appear in the first 200 results

**Fix:** Use pagination with `cursor` parameter, OR use the new dedicated endpoint (see Solution below).

---

## ✅ Solution: New Dedicated Endpoint

I've created a new endpoint specifically for getting SOH by product code:

### New Endpoint: `GET /products/{product_code}/stock`

**URL:** `https://pharmacy-api-webservice.onrender.com/products/{product_code}/stock`

**Query Parameters:**
- `date` (required): Business date in YYYY-MM-DD format
- `pharmacy_id` (optional): Pharmacy ID (default: 1)

**Example Request:**
```bash
GET /products/LP9037679/stock?date=2025-11-12&pharmacy_id=1
```

**Response:**
```json
{
  "product_code": "LP9037679",
  "description": "ALLERGEX TABS 30",
  "on_hand": 58.668,
  "business_date": "2025-11-12"
}
```

**If product not found:**
```json
{
  "product_code": "LP9037679",
  "description": null,
  "on_hand": 0.0,
  "business_date": "2025-11-12"
}
```

---

## 📝 Updated Frontend Proxy Code

**Replace your current endpoint call with:**

```python
@app.get("/api/products/{product_code}/stock")
async def api_product_stock(
    request: Request, 
    product_code: str, 
    pharmacy_id: int = Query(..., description="Pharmacy ID"),
    date: str = Query(..., description="Date in YYYY-MM-DD format")
) -> JSONResponse:
    """Get stock on hand for a specific product using the dedicated /products/{code}/stock endpoint"""
    headers = _auth_headers(request)
    
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            # Use the new dedicated endpoint
            url = f"{API_BASE_URL}/products/{product_code}/stock?date={date}&pharmacy_id={pharmacy_id}"
            print(f"[DEBUG] Calling product stock API: {url}")
            resp = await client.get(url, headers=headers)
            
            if resp.status_code == 401 and API_KEY:
                resp = await client.get(url, headers={"X-API-Key": API_KEY})
            
            if resp.status_code == 200:
                data = resp.json()
                on_hand = data.get("on_hand", 0)
                print(f"[DEBUG] Found SOH for {product_code}: {on_hand}")
                return JSONResponse({"on_hand": on_hand})
            else:
                print(f"[ERROR] API returned {resp.status_code}: {resp.text}")
                return JSONResponse({"on_hand": 0}, status_code=resp.status_code)
        except Exception as e:
            print(f"[ERROR] Failed to fetch product stock: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)
```

---

## ❓ Answers to Frontend Team's Questions

### 1. Does `/pharmacies/{pharmacyId}/stock-activity?date={date}&limit={limit}` return ALL products with stock on hand, or only products that were sold on that date?

**Answer:** Only products that had **activity (sales)** on that specific date. If a product wasn't sold on Nov 12, it won't appear in the response, even if it has stock on hand.

### 2. If a product wasn't sold on a specific date, will it still appear in the `/stock-activity` response with its `on_hand` value?

**Answer:** No. The endpoint only returns products that had sales activity on that date. Use the new `/products/{code}/stock` endpoint instead.

### 3. What is the maximum `limit` value we can use?

**Answer:** Maximum is **200**. Requesting `limit=1000` causes a 422 error.

### 4. Is there a different endpoint we should use to get SOH for a specific product by product_code?

**Answer:** Yes! Use the new endpoint: `GET /products/{product_code}/stock?date={date}&pharmacy_id={id}`

### 5. Can you verify that the endpoint `/pharmacies/1/stock-activity?date=2025-11-12&limit=1000` returns product "LP9037679" with an `on_hand` value?

**Answer:** 
- ❌ The request fails with 422 because `limit=1000` exceeds the max of 200
- ✅ Product `LP9037679` exists on Nov 12 with `on_hand = 58.668`
- ❌ But it's at position 347, so it won't appear with `limit=200` either

### 6. Are there any authentication or permission issues that might prevent certain products from appearing in the response?

**Answer:** No authentication issues. The problem is purely due to:
1. Limit constraint (max 200)
2. Product sorting (by sales value DESC)
3. Product position (347 out of 416)

---

## 🧪 Test the New Endpoint

```bash
curl -X GET "https://pharmacy-api-webservice.onrender.com/products/LP9037679/stock?date=2025-11-12&pharmacy_id=1" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "product_code": "LP9037679",
  "description": "ALLERGEX TABS 30",
  "on_hand": 58.668,
  "business_date": "2025-11-12"
}
```

---

## 📊 Summary

| Issue | Root Cause | Solution |
|-------|------------|----------|
| 422 Error | `limit=1000` exceeds max of 200 | Use `limit=200` or new endpoint |
| Product Not Found | Product at position 347, only top 200 returned | Use new `/products/{code}/stock` endpoint |
| Missing SOH Data | Product not in first page of results | New endpoint queries directly by product code |

---

## 🚀 Recommendation

**Use the new dedicated endpoint** `/products/{product_code}/stock` instead of searching through `/stock-activity` results. It's:
- ✅ More efficient (direct query by product code)
- ✅ No limit constraints
- ✅ Guaranteed to return the product if it exists
- ✅ Simpler code (no need to search through arrays)



