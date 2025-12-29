# Deployment Checklist for User Roles Feature

## ✅ What Needs to Be Deployed

### 1. **Code Changes** (Requires API Redeploy)
The following files were modified and need to be deployed:

- ✅ `pharma_api/app/auth.py` - New role checking functions
- ✅ `pharma_api/app/routers/admin.py` - Role management endpoints
- ✅ `pharma_api/app/routers/authn.py` - Login response includes roles
- ✅ `schema.sql` - Updated schema documentation

**Action Required:** Redeploy your API service (Render will auto-deploy if you push to main, or manually trigger deployment)

### 2. **Database Migration** (Run After Deployment)
The database schema needs to be updated:

- ✅ Add `is_admin` column to `pharma.users` table
- ✅ Add `is_accounting` column to `pharma.users` table
- ✅ Set existing admin users (user_id 2 and 9) to `is_admin=true`

**Action Required:** Run the migration script on your production database

## 🚀 Deployment Steps

### Step 1: Commit and Push Code Changes

```bash
# Commit the changes
git add pharma_api/app/auth.py
git add pharma_api/app/routers/admin.py
git add pharma_api/app/routers/authn.py
git add schema.sql
git add scripts/migrate_user_roles.py
git add scripts/show_user_roles.py
git add scripts/grant_accounting_role.py

git commit -m "Add user roles system (admin and accounting)"
git push origin main
```

### Step 2: Wait for Render Auto-Deploy (or Manual Deploy)

If auto-deploy is enabled on Render:
- Render will automatically detect the push to `main`
- It will rebuild and redeploy your service
- Wait for deployment to complete (usually 5-10 minutes)

If auto-deploy is disabled:
- Go to Render dashboard
- Click "Manual Deploy" → "Deploy latest commit"

### Step 3: Verify API is Running

```bash
# Check health endpoint
curl https://pharmacy-api-webservice.onrender.com/health

# Should return: {"status": "healthy"}
```

### Step 4: Run Database Migration

**Option A: Run Migration Script Locally (Recommended)**

```bash
# Make sure you're connected to production database
# Set DATABASE_URL environment variable to production database
export DATABASE_URL="postgresql://user:pass@host:port/dbname"

# Run migration
python scripts/migrate_user_roles.py
```

**Option B: Run Migration via Render Shell**

1. Go to Render dashboard
2. Click on your PostgreSQL database service
3. Click "Connect" → "Shell"
4. Run SQL commands:

```sql
-- Add columns if they don't exist
ALTER TABLE pharma.users 
  ADD COLUMN IF NOT EXISTS is_admin boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS is_accounting boolean NOT NULL DEFAULT false;

-- Set existing admin users
UPDATE pharma.users SET is_admin = true WHERE user_id IN (2, 9);

-- Verify
SELECT user_id, username, is_admin, is_accounting 
FROM pharma.users 
ORDER BY user_id;
```

**Option C: Use psql Directly**

```bash
# Connect to production database
psql $DATABASE_URL

# Run migration SQL
ALTER TABLE pharma.users 
  ADD COLUMN IF NOT EXISTS is_admin boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS is_accounting boolean NOT NULL DEFAULT false;

UPDATE pharma.users SET is_admin = true WHERE user_id IN (2, 9);
```

### Step 5: Verify Migration

```bash
# Run the show roles script
python scripts/show_user_roles.py

# Or test via API
curl -H "Authorization: Bearer <admin_token>" \
     https://pharmacy-api-webservice.onrender.com/admin/users
```

## ⚠️ Important Notes

### Order Matters
1. **Deploy code first** - The API needs the new code to handle role checks
2. **Then run migration** - Database needs the new columns

### Backward Compatibility
- ✅ Existing functionality continues to work
- ✅ Admin users (user_id 2 and 9) will automatically get `is_admin=true` from migration
- ✅ API keys still work as before (treated as admin/accounting access)
- ✅ No breaking changes to existing endpoints

### Testing After Deployment

1. **Test Login** - Verify login response includes roles:
```bash
curl -X POST https://pharmacy-api-webservice.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "Charl", "password": "your_password"}'

# Should return user object with is_admin and is_accounting fields
```

2. **Test Admin Endpoints** - Verify admin endpoints work:
```bash
curl -H "Authorization: Bearer <admin_token>" \
     https://pharmacy-api-webservice.onrender.com/admin/users

# Should return list of users with role information
```

3. **Test Role Updates** - Verify you can update roles:
```bash
curl -X PUT https://pharmacy-api-webservice.onrender.com/admin/users/3 \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"is_accounting": true}'
```

## 🔍 Troubleshooting

### Issue: Migration Fails
**Error:** `column "is_admin" already exists`

**Solution:** Columns already exist, migration is safe to run multiple times (uses `IF NOT EXISTS`)

### Issue: API Returns 500 Error
**Possible Causes:**
- Database columns don't exist yet (run migration)
- Code not deployed yet (check Render deployment status)

### Issue: Admin Endpoints Return 403
**Possible Causes:**
- User doesn't have `is_admin=true` in database
- Migration didn't run successfully
- Token is expired or invalid

### Issue: Login Response Missing Roles
**Possible Causes:**
- Code not deployed yet
- Old cached response (try logging out and back in)

## ✅ Post-Deployment Checklist

- [ ] Code deployed to Render
- [ ] API health check passes
- [ ] Database migration completed
- [ ] Login response includes `is_admin` and `is_accounting`
- [ ] Admin endpoints return role information
- [ ] Can create users with roles
- [ ] Can update user roles
- [ ] Existing admin users have `is_admin=true`

## 📝 Quick Reference

**Deploy Code:**
```bash
git push origin main  # Auto-deploys on Render
```

**Run Migration:**
```bash
export DATABASE_URL="your_production_db_url"
python scripts/migrate_user_roles.py
```

**Verify:**
```bash
python scripts/show_user_roles.py
```

