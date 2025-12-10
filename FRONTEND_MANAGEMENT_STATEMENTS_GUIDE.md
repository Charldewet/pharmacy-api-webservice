# Frontend Implementation Guide: Management Financial Statements

Complete guide for implementing the Management Financial Statements feature in the frontend, including statement display, account drill-down, and ledger entry viewing.

---

## Table of Contents

1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [Data Structures](#data-structures)
4. [Implementation Guide](#implementation-guide)
5. [UI/UX Recommendations](#uiux-recommendations)
6. [Code Examples](#code-examples)
7. [Navigation Flow](#navigation-flow)
8. [Error Handling](#error-handling)

---

## Overview

The Management Financial Statements feature provides:

1. **Monthly P&L Statement** - Complete profit & loss statement for a pharmacy and month
2. **Account Drill-Down** - View individual accounts and their balances
3. **Ledger Entry Listing** - View all transactions (ledger entries) for an account
4. **Historical Trends** - View trends over multiple months

### Key Features

- Filter by pharmacy, year, and month
- View summary totals (revenue, COGS, gross profit, expenses, net profit)
- Drill down into individual accounts
- View all ledger entries for an account
- Historical trend charts

---

## API Endpoints

### Base URL
All endpoints use the base API URL (e.g., `https://pharmacy-api-webservice.onrender.com`)

### Authentication
All endpoints require Bearer token authentication:
```http
Authorization: Bearer YOUR_API_KEY
```

---

### 1. Monthly Management Statement

**Endpoint:**
```http
GET /pharmacies/{pharmacy_id}/management-statement?year=YYYY&month=MM
```

**Parameters:**
- `pharmacy_id` (path): ID of the pharmacy
- `year` (query, required): Year (e.g., 2025)
- `month` (query, required): Month number (1-12)

**Example:**
```javascript
GET /pharmacies/1/management-statement?year=2025&month=11
```

**Response Structure:**
```typescript
interface ManagementStatement {
  pharmacy_id: number;
  year: number;
  month: number;
  from_date: string;  // YYYY-MM-DD
  to_date: string;    // YYYY-MM-DD
  summary: {
    total_revenue: number;
    total_cogs: number;
    gross_profit: number;
    gross_profit_percent: number;
    total_expenses: number;
    operating_profit: number;
    total_other_income: number;
    total_other_expenses: number;
    net_profit: number;
  };
  revenue: AccountLineItem[];
  cogs: AccountLineItem[];
  expenses: AccountLineItem[];
  other_income: AccountLineItem[];
  other_expenses: AccountLineItem[];
}

interface AccountLineItem {
  account_id: number;
  code: string;
  name: string;
  amount: number;  // Negative for COGS/expenses, positive for revenue/income
}
```

---

### 2. Historical Trend

**Endpoint:**
```http
GET /pharmacies/{pharmacy_id}/management-statement/trend?from=YYYY-MM&to=YYYY-MM
```

**Parameters:**
- `pharmacy_id` (path): ID of the pharmacy
- `from` (query, required): Start month in YYYY-MM format
- `to` (query, required): End month in YYYY-MM format

**Example:**
```javascript
GET /pharmacies/1/management-statement/trend?from=2025-01&to=2025-12
```

**Response Structure:**
```typescript
interface ManagementTrendPoint {
  month: string;  // YYYY-MM format
  revenue: number;
  gross_profit: number;
  net_profit: number;
}
```

---

### 3. List Accounts

**Endpoint:**
```http
GET /accounts?type={type}&report_category={category}&is_active=true
```

**Parameters:**
- `type` (query, optional): Filter by account type (INCOME, COGS, EXPENSE, etc.)
- `category` (query, optional): Filter by category
- `is_active` (query, optional): Filter by active status
- `include_inactive` (query, optional, default: false): Include inactive accounts

**Example:**
```javascript
// Get all revenue accounts
GET /accounts?type=INCOME&is_active=true

// Get all accounts with report_category
GET /accounts?is_active=true
```

**Response Structure:**
```typescript
interface Account {
  id: number;
  code: string;
  name: string;
  type: string;
  category: string;
  parent_account_id: number | null;
  is_active: boolean;
  display_order: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
  report_category?: string;  // revenue, cogs, expenses, other_income, other_expenses
}
```

---

### 4. List Ledger Entries (for Account Drill-Down)

**Endpoint:**
```http
GET /ledger-entries/pharmacies/{pharmacy_id}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&limit=100&offset=0
```

**Parameters:**
- `pharmacy_id` (path): ID of the pharmacy
- `start_date` (query, optional): Start date (inclusive)
- `end_date` (query, optional): End date (inclusive)
- `source` (query, optional): Filter by source (PHARMASIGHT, BANK, MANUAL)
- `limit` (query, optional, default: 100): Maximum entries (max: 1000)
- `offset` (query, optional, default: 0): Pagination offset

**Example:**
```javascript
// Get all ledger entries for November 2025
GET /ledger-entries/pharmacies/1?start_date=2025-11-01&end_date=2025-11-30&limit=1000

// Get entries for a specific account (filter client-side by debit_account_id or credit_account_id)
GET /ledger-entries/pharmacies/1?start_date=2025-11-01&end_date=2025-11-30&limit=1000
```

**Response Structure:**
```typescript
interface LedgerEntry {
  id: number;
  pharmacy_id: number;
  date: string;  // YYYY-MM-DD
  description: string;
  amount: number;  // Always positive
  debit_account_id: number;
  credit_account_id: number;
  source: string;  // PHARMASIGHT, BANK, MANUAL
  source_reference_type: string | null;
  source_reference_id: string | null;
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}
```

**Note:** To get entries for a specific account, fetch all entries and filter client-side where `debit_account_id === accountId` OR `credit_account_id === accountId`.

---

### 5. Get Single Ledger Entry

**Endpoint:**
```http
GET /ledger-entries/{ledger_entry_id}
```

**Response:** Single `LedgerEntry` object

---

## Data Structures

### Complete TypeScript Interfaces

```typescript
// Management Statement Types
interface ManagementStatement {
  pharmacy_id: number;
  year: number;
  month: number;
  from_date: string;
  to_date: string;
  summary: ManagementStatementSummary;
  revenue: AccountLineItem[];
  cogs: AccountLineItem[];
  expenses: AccountLineItem[];
  other_income: AccountLineItem[];
  other_expenses: AccountLineItem[];
}

interface ManagementStatementSummary {
  total_revenue: number;
  total_cogs: number;
  gross_profit: number;
  gross_profit_percent: number;
  total_expenses: number;
  operating_profit: number;
  total_other_income: number;
  total_other_expenses: number;
  net_profit: number;
}

interface AccountLineItem {
  account_id: number;
  code: string;
  name: string;
  amount: number;
}

interface ManagementTrendPoint {
  month: string;
  revenue: number;
  gross_profit: number;
  net_profit: number;
}

// Account Types
interface Account {
  id: number;
  code: string;
  name: string;
  type: string;
  category: string;
  parent_account_id: number | null;
  is_active: boolean;
  display_order: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
  report_category?: string;
}

// Ledger Entry Types
interface LedgerEntry {
  id: number;
  pharmacy_id: number;
  date: string;
  description: string;
  amount: number;
  debit_account_id: number;
  credit_account_id: number;
  source: string;
  source_reference_type: string | null;
  source_reference_id: string | null;
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

// Helper: Account Transaction (derived from LedgerEntry)
interface AccountTransaction {
  ledger_entry_id: number;
  date: string;
  description: string;
  amount: number;
  side: 'debit' | 'credit';
  counterpart_account_id: number;
  counterpart_account_code: string;
  counterpart_account_name: string;
  source: string;
}
```

---

## Implementation Guide

### Step 1: Create API Service Functions

```typescript
// services/managementStatementApi.ts

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://pharmacy-api-webservice.onrender.com';
const API_KEY = process.env.REACT_APP_API_KEY || '';

async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function getManagementStatement(
  pharmacyId: number,
  year: number,
  month: number
): Promise<ManagementStatement> {
  return apiRequest<ManagementStatement>(
    `/pharmacies/${pharmacyId}/management-statement?year=${year}&month=${month}`
  );
}

export async function getManagementTrend(
  pharmacyId: number,
  fromMonth: string,
  toMonth: string
): Promise<ManagementTrendPoint[]> {
  return apiRequest<ManagementTrendPoint[]>(
    `/pharmacies/${pharmacyId}/management-statement/trend?from=${fromMonth}&to=${toMonth}`
  );
}

export async function getAccounts(filters?: {
  type?: string;
  report_category?: string;
  is_active?: boolean;
}): Promise<Account[]> {
  const params = new URLSearchParams();
  if (filters?.type) params.append('type', filters.type);
  if (filters?.report_category) params.append('report_category', filters.report_category);
  if (filters?.is_active !== undefined) params.append('is_active', String(filters.is_active));
  
  return apiRequest<Account[]>(`/accounts?${params.toString()}`);
}

export async function getLedgerEntries(
  pharmacyId: number,
  filters?: {
    start_date?: string;
    end_date?: string;
    source?: string;
    limit?: number;
    offset?: number;
  }
): Promise<LedgerEntry[]> {
  const params = new URLSearchParams();
  if (filters?.start_date) params.append('start_date', filters.start_date);
  if (filters?.end_date) params.append('end_date', filters.end_date);
  if (filters?.source) params.append('source', filters.source);
  if (filters?.limit) params.append('limit', String(filters.limit));
  if (filters?.offset) params.append('offset', String(filters.offset));
  
  return apiRequest<LedgerEntry[]>(
    `/ledger-entries/pharmacies/${pharmacyId}?${params.toString()}`
  );
}

export async function getAccountTransactions(
  pharmacyId: number,
  accountId: number,
  startDate: string,
  endDate: string
): Promise<AccountTransaction[]> {
  // Fetch all ledger entries for the period
  const entries = await getLedgerEntries(pharmacyId, {
    start_date: startDate,
    end_date: endDate,
    limit: 1000,
  });

  // Fetch account details for counterpart accounts
  const accounts = await getAccounts({ is_active: true });
  const accountMap = new Map(accounts.map(acc => [acc.id, acc]));

  // Filter and transform entries for this account
  const transactions: AccountTransaction[] = [];
  
  for (const entry of entries) {
    if (entry.debit_account_id === accountId) {
      // This account is debited (expense/asset increase, income decrease)
      const counterpart = accountMap.get(entry.credit_account_id);
      transactions.push({
        ledger_entry_id: entry.id,
        date: entry.date,
        description: entry.description,
        amount: entry.amount,
        side: 'debit',
        counterpart_account_id: entry.credit_account_id,
        counterpart_account_code: counterpart?.code || 'N/A',
        counterpart_account_name: counterpart?.name || 'Unknown',
        source: entry.source,
      });
    } else if (entry.credit_account_id === accountId) {
      // This account is credited (income increase, expense/asset decrease)
      const counterpart = accountMap.get(entry.debit_account_id);
      transactions.push({
        ledger_entry_id: entry.id,
        date: entry.date,
        description: entry.description,
        amount: entry.amount,
        side: 'credit',
        counterpart_account_id: entry.debit_account_id,
        counterpart_account_code: counterpart?.code || 'N/A',
        counterpart_account_name: counterpart?.name || 'Unknown',
        source: entry.source,
      });
    }
  }

  // Sort by date descending
  transactions.sort((a, b) => b.date.localeCompare(a.date));

  return transactions;
}
```

---

### Step 2: Create React Components

#### 2.1 Management Statement Page Component

```typescript
// components/ManagementStatementPage.tsx

import React, { useState, useEffect } from 'react';
import { getManagementStatement, getManagementTrend } from '../services/managementStatementApi';
import { ManagementStatement, ManagementTrendPoint } from '../types';
import StatementSummary from './StatementSummary';
import StatementTable from './StatementTable';
import TrendChart from './TrendChart';

interface Props {
  pharmacyId: number;
}

export default function ManagementStatementPage({ pharmacyId }: Props) {
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [statement, setStatement] = useState<ManagementStatement | null>(null);
  const [trend, setTrend] = useState<ManagementTrendPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStatement();
    loadTrend();
  }, [pharmacyId, year, month]);

  async function loadStatement() {
    setLoading(true);
    setError(null);
    try {
      const data = await getManagementStatement(pharmacyId, year, month);
      setStatement(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load statement');
    } finally {
      setLoading(false);
    }
  }

  async function loadTrend() {
    try {
      // Load last 12 months
      const fromMonth = `${year}-${String(Math.max(1, month - 11)).padStart(2, '0')}`;
      const toMonth = `${year}-${String(month).padStart(2, '0')}`;
      const data = await getManagementTrend(pharmacyId, fromMonth, toMonth);
      setTrend(data);
    } catch (err) {
      console.error('Failed to load trend:', err);
    }
  }

  if (loading && !statement) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  if (!statement) {
    return null;
  }

  return (
    <div className="management-statement-page">
      {/* Filters */}
      <div className="filters">
        <select value={year} onChange={(e) => setYear(Number(e.target.value))}>
          {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i).map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        <select value={month} onChange={(e) => setMonth(Number(e.target.value))}>
          {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
            <option key={m} value={m}>
              {new Date(2000, m - 1).toLocaleString('default', { month: 'long' })}
            </option>
          ))}
        </select>
        <button onClick={loadStatement}>Refresh</button>
      </div>

      {/* Summary Cards */}
      <StatementSummary summary={statement.summary} />

      {/* P&L Table */}
      <StatementTable statement={statement} pharmacyId={pharmacyId} />

      {/* Trend Chart */}
      {trend.length > 0 && <TrendChart data={trend} />}
    </div>
  );
}
```

#### 2.2 Statement Summary Component

```typescript
// components/StatementSummary.tsx

import React from 'react';
import { ManagementStatementSummary } from '../types';

interface Props {
  summary: ManagementStatementSummary;
}

export default function StatementSummary({ summary }: Props) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-ZA', {
      style: 'currency',
      currency: 'ZAR',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  return (
    <div className="statement-summary">
      <div className="summary-card">
        <div className="label">Turnover</div>
        <div className="value">{formatCurrency(summary.total_revenue)}</div>
      </div>
      <div className="summary-card">
        <div className="label">Gross Profit</div>
        <div className="value">{formatCurrency(summary.gross_profit)}</div>
        <div className="subtext">{summary.gross_profit_percent.toFixed(1)}%</div>
      </div>
      <div className="summary-card">
        <div className="label">Operating Expenses</div>
        <div className="value">{formatCurrency(summary.total_expenses)}</div>
      </div>
      <div className="summary-card highlight">
        <div className="label">Net Profit</div>
        <div className="value">{formatCurrency(summary.net_profit)}</div>
      </div>
    </div>
  );
}
```

#### 2.3 Statement Table Component

```typescript
// components/StatementTable.tsx

import React from 'react';
import { ManagementStatement, AccountLineItem } from '../types';
import { useNavigate } from 'react-router-dom';

interface Props {
  statement: ManagementStatement;
  pharmacyId: number;
}

export default function StatementTable({ statement, pharmacyId }: Props) {
  const navigate = useNavigate();

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-ZA', {
      style: 'currency',
      currency: 'ZAR',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const handleAccountClick = (accountId: number, accountCode: string) => {
    navigate(`/pharmacies/${pharmacyId}/accounts/${accountId}`, {
      state: {
        year: statement.year,
        month: statement.month,
        fromDate: statement.from_date,
        toDate: statement.to_date,
      },
    });
  };

  const renderSection = (
    title: string,
    items: AccountLineItem[],
    total: number,
    isNegative: boolean = false
  ) => {
    if (items.length === 0) return null;

    return (
      <div className="statement-section">
        <h3>{title}</h3>
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Account Name</th>
              <th className="text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.account_id}
                className="clickable-row"
                onClick={() => handleAccountClick(item.account_id, item.code)}
              >
                <td>{item.code}</td>
                <td>{item.name}</td>
                <td className={`text-right ${isNegative ? 'negative' : ''}`}>
                  {formatCurrency(item.amount)}
                </td>
              </tr>
            ))}
            <tr className="subtotal">
              <td colSpan={2}><strong>Total {title}</strong></td>
              <td className={`text-right ${isNegative ? 'negative' : ''}`}>
                <strong>{formatCurrency(total)}</strong>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="statement-table">
      {renderSection('Revenue', statement.revenue, statement.summary.total_revenue)}
      
      {renderSection('Cost of Sales', statement.cogs, statement.summary.total_cogs, true)}
      
      {statement.summary.total_revenue !== 0 && (
        <div className="statement-section">
          <div className="gross-profit-row">
            <strong>Gross Profit</strong>
            <strong>{formatCurrency(statement.summary.gross_profit)}</strong>
          </div>
        </div>
      )}

      {renderSection('Operating Expenses', statement.expenses, statement.summary.total_expenses, true)}
      
      {statement.summary.total_revenue !== 0 && (
        <div className="statement-section">
          <div className="operating-profit-row">
            <strong>Operating Profit</strong>
            <strong>{formatCurrency(statement.summary.operating_profit)}</strong>
          </div>
        </div>
      )}

      {statement.other_income.length > 0 && (
        renderSection('Other Income', statement.other_income, statement.summary.total_other_income)
      )}

      {statement.other_expenses.length > 0 && (
        renderSection('Other Expenses', statement.other_expenses, statement.summary.total_other_expenses, true)
      )}

      <div className="statement-section">
        <div className="net-profit-row">
          <strong>Net Profit</strong>
          <strong className={statement.summary.net_profit >= 0 ? 'positive' : 'negative'}>
            {formatCurrency(statement.summary.net_profit)}
          </strong>
        </div>
      </div>
    </div>
  );
}
```

#### 2.4 Account Detail Page Component

```typescript
// components/AccountDetailPage.tsx

import React, { useState, useEffect } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { getAccountTransactions, getAccounts } from '../services/managementStatementApi';
import { AccountTransaction, Account } from '../types';
import AccountTransactionsTable from './AccountTransactionsTable';

export default function AccountDetailPage() {
  const { pharmacyId, accountId } = useParams<{ pharmacyId: string; accountId: string }>();
  const location = useLocation();
  const state = location.state as { year?: number; month?: number; fromDate?: string; toDate?: string } | null;

  const [account, setAccount] = useState<Account | null>(null);
  const [transactions, setTransactions] = useState<AccountTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use date range from navigation state, or default to current month
  const fromDate = state?.fromDate || new Date().toISOString().split('T')[0];
  const toDate = state?.toDate || new Date().toISOString().split('T')[0];

  useEffect(() => {
    if (pharmacyId && accountId) {
      loadAccount();
      loadTransactions();
    }
  }, [pharmacyId, accountId, fromDate, toDate]);

  async function loadAccount() {
    try {
      const accounts = await getAccounts({ is_active: true });
      const found = accounts.find(acc => acc.id === Number(accountId));
      setAccount(found || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load account');
    }
  }

  async function loadTransactions() {
    if (!pharmacyId || !accountId) return;

    setLoading(true);
    setError(null);
    try {
      const data = await getAccountTransactions(
        Number(pharmacyId),
        Number(accountId),
        fromDate,
        toDate
      );
      setTransactions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transactions');
    } finally {
      setLoading(false);
    }
  }

  if (!account) {
    return <div>Loading account...</div>;
  }

  // Calculate account balance
  const balance = transactions.reduce((sum, txn) => {
    if (account.type === 'INCOME' || account.type === 'OTHER_INCOME') {
      // Income: credits increase, debits decrease
      return sum + (txn.side === 'credit' ? txn.amount : -txn.amount);
    } else if (account.type === 'EXPENSE' || account.type === 'COGS' || account.type === 'FINANCE_COST') {
      // Expenses: debits increase, credits decrease
      return sum + (txn.side === 'debit' ? txn.amount : -txn.amount);
    } else {
      // Assets/Liabilities: debits increase assets, credits increase liabilities
      return sum + (txn.side === 'debit' ? txn.amount : -txn.amount);
    }
  }, 0);

  return (
    <div className="account-detail-page">
      <div className="account-header">
        <h1>{account.code} - {account.name}</h1>
        <div className="account-info">
          <span>Type: {account.type}</span>
          <span>Category: {account.category}</span>
          {account.report_category && <span>Report Category: {account.report_category}</span>}
        </div>
        <div className="account-balance">
          <strong>Balance for period:</strong>{' '}
          {new Intl.NumberFormat('en-ZA', {
            style: 'currency',
            currency: 'ZAR',
          }).format(balance)}
        </div>
        <div className="period-info">
          Period: {fromDate} to {toDate}
        </div>
      </div>

      {error && <div className="error">Error: {error}</div>}

      {loading ? (
        <div>Loading transactions...</div>
      ) : (
        <AccountTransactionsTable transactions={transactions} account={account} />
      )}
    </div>
  );
}
```

#### 2.5 Account Transactions Table Component

```typescript
// components/AccountTransactionsTable.tsx

import React from 'react';
import { AccountTransaction, Account } from '../types';

interface Props {
  transactions: AccountTransaction[];
  account: Account;
}

export default function AccountTransactionsTable({ transactions, account }: Props) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-ZA', {
      style: 'currency',
      currency: 'ZAR',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-ZA');
  };

  const getSourceBadge = (source: string) => {
    const colors: Record<string, string> = {
      PHARMASIGHT: 'blue',
      BANK: 'green',
      MANUAL: 'orange',
    };
    return (
      <span className={`badge badge-${colors[source] || 'gray'}`}>
        {source}
      </span>
    );
  };

  if (transactions.length === 0) {
    return (
      <div className="no-transactions">
        <p>No transactions found for this account in the selected period.</p>
      </div>
    );
  }

  return (
    <div className="account-transactions">
      <h2>Transactions ({transactions.length})</h2>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Side</th>
            <th>Amount</th>
            <th>Counterpart Account</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((txn) => (
            <tr key={txn.ledger_entry_id}>
              <td>{formatDate(txn.date)}</td>
              <td>{txn.description}</td>
              <td>
                <span className={`side side-${txn.side}`}>
                  {txn.side.toUpperCase()}
                </span>
              </td>
              <td className="text-right">{formatCurrency(txn.amount)}</td>
              <td>
                {txn.counterpart_account_code} - {txn.counterpart_account_name}
              </td>
              <td>{getSourceBadge(txn.source)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## UI/UX Recommendations

### 1. Layout Structure

```
┌─────────────────────────────────────────────────┐
│  Management Financial Statements                │
├─────────────────────────────────────────────────┤
│  [Pharmacy Selector] [Year ▼] [Month ▼] [🔄] │
├─────────────────────────────────────────────────┤
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│  │Turnover│ │Gross │ │Expenses│ │Net Profit│ │
│  │ R450k │ │ R150k│ │ R105k │ │  R45k │     │
│  └──────┘ └──────┘ └──────┘ └──────┘          │
├─────────────────────────────────────────────────┤
│  Revenue                                        │
│  ┌───────────────────────────────────────────┐ │
│  │ Code │ Account Name      │ Amount       │ │
│  ├───────────────────────────────────────────┤ │
│  │ 4000 │ OTC Sales         │ R 250,000.00 │ │
│  │ 4010 │ Dispensary Sales  │ R 200,000.00 │ │
│  └───────────────────────────────────────────┘ │
│  Total Revenue: R 450,000.00                    │
│                                                  │
│  Cost of Sales                                  │
│  ...                                            │
└─────────────────────────────────────────────────┘
```

### 2. Color Coding

- **Revenue/Income**: Green (positive)
- **COGS/Expenses**: Red (negative amounts)
- **Net Profit**: 
  - Green if positive
  - Red if negative
- **Source Badges**:
  - PHARMASIGHT: Blue
  - BANK: Green
  - MANUAL: Orange

### 3. Interactive Elements

- **Clickable Account Rows**: Click to drill down into account details
- **Hover Effects**: Highlight rows on hover
- **Loading States**: Show skeleton loaders while fetching
- **Error States**: Display user-friendly error messages
- **Empty States**: Show helpful messages when no data

### 4. Responsive Design

- **Desktop**: Full table layout
- **Tablet**: Scrollable table with sticky header
- **Mobile**: Card-based layout for summary, stacked table

---

## Navigation Flow

### Flow 1: View Statement → Account Detail

```
Management Statement Page
  ↓ (click account row)
Account Detail Page
  ↓ (shows all transactions for that account)
Transaction List
```

### Flow 2: Filter by Period

```
Select Year/Month → Load Statement → Display Data
```

### Flow 3: View Trends

```
Management Statement Page → Trend Chart Tab
  ↓ (shows line chart of revenue/gross profit/net profit)
Historical Trend View
```

---

## Error Handling

### API Error Handling

```typescript
try {
  const statement = await getManagementStatement(pharmacyId, year, month);
  // Handle success
} catch (error) {
  if (error instanceof Error) {
    if (error.message.includes('404')) {
      // Pharmacy not found
      showError('Pharmacy not found');
    } else if (error.message.includes('400')) {
      // Invalid parameters
      showError('Invalid date range or parameters');
    } else {
      // Generic error
      showError('Failed to load statement. Please try again.');
    }
  }
}
```

### Loading States

```typescript
const [loading, setLoading] = useState(false);

// Show skeleton loader
{loading && <StatementSkeleton />}

// Show error
{error && <ErrorMessage message={error} />}

// Show data
{!loading && !error && statement && <StatementTable statement={statement} />}
```

---

## Example CSS Styles

```css
/* Statement Summary Cards */
.statement-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.summary-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
}

.summary-card .label {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.summary-card .value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
}

.summary-card .subtext {
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.25rem;
}

.summary-card.highlight {
  border-color: #4CAF50;
  background: #f1f8f4;
}

/* Statement Table */
.statement-table {
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.statement-section {
  margin-bottom: 2rem;
}

.statement-section h3 {
  background: #f5f5f5;
  padding: 0.75rem 1rem;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.statement-section table {
  width: 100%;
  border-collapse: collapse;
}

.statement-section th {
  background: #f9f9f9;
  padding: 0.75rem 1rem;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid #e0e0e0;
}

.statement-section td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f0f0f0;
}

.statement-section .clickable-row {
  cursor: pointer;
  transition: background-color 0.2s;
}

.statement-section .clickable-row:hover {
  background-color: #f5f5f5;
}

.statement-section .text-right {
  text-align: right;
}

.statement-section .negative {
  color: #d32f2f;
}

.statement-section .subtotal {
  background: #f9f9f9;
  font-weight: 600;
}

.gross-profit-row,
.operating-profit-row,
.net-profit-row {
  display: flex;
  justify-content: space-between;
  padding: 1rem;
  background: #f9f9f9;
  border-top: 2px solid #e0e0e0;
  font-size: 1.1rem;
}

.net-profit-row {
  background: #f1f8f4;
  border-top: 3px solid #4CAF50;
}

.net-profit-row .positive {
  color: #2e7d32;
}

.net-profit-row .negative {
  color: #d32f2f;
}

/* Account Transactions */
.account-transactions table {
  width: 100%;
  border-collapse: collapse;
}

.account-transactions th {
  background: #f5f5f5;
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
}

.account-transactions td {
  padding: 0.75rem;
  border-bottom: 1px solid #f0f0f0;
}

.side {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.side-debit {
  background: #fff3e0;
  color: #e65100;
}

.side-credit {
  background: #e3f2fd;
  color: #1565c0;
}

.badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-blue {
  background: #e3f2fd;
  color: #1565c0;
}

.badge-green {
  background: #e8f5e9;
  color: #2e7d32;
}

.badge-orange {
  background: #fff3e0;
  color: #e65100;
}
```

---

## Complete Example: Full Page Implementation

See the code examples above for complete component implementations. The key files you'll need:

1. **API Service** (`services/managementStatementApi.ts`) - All API calls
2. **Main Page** (`components/ManagementStatementPage.tsx`) - Main statement view
3. **Summary Cards** (`components/StatementSummary.tsx`) - Key metrics
4. **Statement Table** (`components/StatementTable.tsx`) - P&L table with drill-down
5. **Account Detail** (`components/AccountDetailPage.tsx`) - Account detail view
6. **Transactions Table** (`components/AccountTransactionsTable.tsx`) - Ledger entries list

---

## Testing Checklist

- [ ] Load management statement for current month
- [ ] Change year/month filters and reload
- [ ] Click on account row to view account details
- [ ] View ledger entries for an account
- [ ] Display correct amounts (negative for expenses/COGS)
- [ ] Show loading states
- [ ] Handle API errors gracefully
- [ ] Display empty states when no data
- [ ] Test responsive design on mobile/tablet
- [ ] Verify trend chart displays correctly

---

## Additional Notes

### Amount Sign Convention

- **Revenue/Income**: Positive amounts
- **COGS/Expenses**: Negative amounts (for readability)
- **Net Profit**: Can be positive or negative

### Account Balance Calculation

For each account type:
- **INCOME**: Credits increase balance, debits decrease
- **EXPENSE/COGS**: Debits increase balance, credits decrease
- **ASSET**: Debits increase balance, credits decrease
- **LIABILITY**: Credits increase balance, debits decrease

### Performance Considerations

- Use pagination for ledger entries (limit: 1000 max)
- Cache account list to avoid repeated API calls
- Consider debouncing filter changes
- Use React Query or SWR for data fetching and caching

---

## Support

For questions or issues, refer to:
- Backend documentation: `MANAGEMENT_STATEMENTS_IMPLEMENTATION.md`
- API endpoints: See API documentation
- Example responses: Use browser DevTools Network tab
