/**
 * Example: How to create an account in the chart of accounts
 * 
 * This example shows the correct way to call the /admin/chart-of-accounts endpoint
 * with proper authentication headers.
 */

// ============================================
// Method 1: Using fetch with proper headers
// ============================================

async function createAccount(accountData) {
  // Step 1: Get the authentication token
  // This should come from your authentication system (localStorage, context, store, etc.)
  const token = localStorage.getItem('admin_token'); // or getAuthToken() from your auth system
  
  if (!token) {
    throw new Error('No authentication token available. Please log in first.');
  }
  
  // Step 2: Make the API call with proper headers
  try {
    const response = await fetch('/admin/chart-of-accounts', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,  // REQUIRED: Must include this header
        'Content-Type': 'application/json'   // REQUIRED: For JSON body
      },
      body: JSON.stringify({
        code: accountData.code,
        name: accountData.name,
        type: accountData.type,
        category: accountData.category,
        parent_account_id: accountData.parent_account_id || null,
        is_active: accountData.is_active !== undefined ? accountData.is_active : true,
        display_order: accountData.display_order || 0,
        notes: accountData.notes || null
      })
    });
    
    // Step 3: Handle the response
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `Failed to create account: ${response.status}`);
    }
    
    const newAccount = await response.json();
    return newAccount;
  } catch (error) {
    console.error('Error creating account:', error);
    throw error;
  }
}

// ============================================
// Method 2: Using a helper function
// ============================================

/**
 * Helper function to make authenticated API calls
 */
async function authenticatedFetch(url, options = {}) {
  const token = localStorage.getItem('admin_token');
  
  if (!token) {
    throw new Error('No authentication token available. Please log in first.');
  }
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    ...options.headers
  };
  
  const response = await fetch(url, {
    ...options,
    headers
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }
  
  return await response.json();
}

// Usage with helper function
async function createAccountWithHelper(accountData) {
  return await authenticatedFetch('/admin/chart-of-accounts', {
    method: 'POST',
    body: JSON.stringify(accountData)
  });
}

// ============================================
// Usage Examples
// ============================================

// Example 1: Basic account creation
async function example1() {
  try {
    const account = await createAccount({
      code: '2101',
      name: 'Operating Expenses',
      type: 'EXPENSE',
      category: 'OPERATING_EXPENSE'
    });
    console.log('Account created:', account);
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Example 2: Account with all fields
async function example2() {
  try {
    const account = await createAccount({
      code: '2102',
      name: 'Sub Account',
      type: 'EXPENSE',
      category: 'OPERATING_EXPENSE',
      parent_account_id: 123,  // ID of parent account
      is_active: true,
      display_order: 10,
      notes: 'This is a sub-account'
    });
    console.log('Account created:', account);
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Example 3: Using helper function
async function example3() {
  try {
    const account = await createAccountWithHelper({
      code: '2103',
      name: 'Another Account',
      type: 'INCOME',
      category: 'SALES'
    });
    console.log('Account created:', account);
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// ============================================
// Common Mistakes to Avoid
// ============================================

// ❌ WRONG: Missing Authorization header
async function wrongExample1() {
  const response = await fetch('/admin/chart-of-accounts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
      // Missing: 'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ code: '2101', name: 'Test', type: 'EXPENSE', category: 'TEST' })
  });
  // This will fail with "Missing Authorization header"
}

// ❌ WRONG: Wrong header format
async function wrongExample2() {
  const token = localStorage.getItem('admin_token');
  const response = await fetch('/admin/chart-of-accounts', {
    method: 'POST',
    headers: {
      'Authorization': token,  // Wrong: Should be `Bearer ${token}`
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ code: '2101', name: 'Test', type: 'EXPENSE', category: 'TEST' })
  });
  // This will fail because the format is wrong
}

// ❌ WRONG: Missing Content-Type
async function wrongExample3() {
  const token = localStorage.getItem('admin_token');
  const response = await fetch('/admin/chart-of-accounts', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
      // Missing: 'Content-Type': 'application/json'
    },
    body: JSON.stringify({ code: '2101', name: 'Test', type: 'EXPENSE', category: 'TEST' })
  });
  // This might work but is not recommended
}

// ✅ CORRECT: Proper headers
async function correctExample() {
  const token = localStorage.getItem('admin_token');
  const response = await fetch('/admin/chart-of-accounts', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,  // ✅ Correct format
      'Content-Type': 'application/json'   // ✅ Include Content-Type
    },
    body: JSON.stringify({
      code: '2101',
      name: 'Test Account',
      type: 'EXPENSE',
      category: 'OPERATING_EXPENSE'
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { createAccount, authenticatedFetch, createAccountWithHelper };
}
