# User Management Admin Interface

A simple web-based admin interface for managing users and their pharmacy access. **Only authorized admin users (Charl and Amin) can access this interface.**

## Features

- ✅ View all users in the system
- ✅ Create new users
- ✅ Update user information (email, password, active status)
- ✅ Grant pharmacy access to users
- ✅ Revoke pharmacy access from users
- ✅ View detailed user information including pharmacy access

## Access

**URL:** `http://your-server/admin/`

**Access Control:** Only authorized admin users can log in to this interface (Charl - user_id: 2, Amin - user_id: 9).

## How to Use

### 1. Login

1. Navigate to `/admin/` in your browser
2. Enter admin user credentials:
   - Username: `Charl` or `Amin`
   - Password: (Current password for the admin user)
3. Click "Login"

### 2. View Users

The main page displays a table of all users with:
- User ID
- Username
- Email
- Status (Active/Inactive)
- Number of pharmacies they have access to
- Created date
- Action buttons

### 3. Create New User

1. Click the "+ Add New User" button
2. Fill in the form:
   - **Username**: Unique username for the user
   - **Email**: User's email address
   - **Password**: Initial password (user can change later)
   - **Grant Pharmacy Access**: Check the pharmacies you want to grant access to
   - **Grant Write Access**: Check this if the user should have write permissions
3. Click "Create User"

### 4. Edit User

1. Click "Edit" next to any user
2. Update:
   - Email address
   - Password (leave blank to keep current password)
   - Active status (check/uncheck to activate/deactivate)
3. Click "Update User"

### 5. View User Details

1. Click "View" next to any user
2. See detailed information including:
   - User information
   - All pharmacy access with permissions (READ/WRITE)
   - Option to revoke individual pharmacy access

### 6. Grant Pharmacy Access

1. Click "Grant Access" next to any user
2. Select a pharmacy from the dropdown
3. Choose permissions:
   - **Read Access**: User can view data
   - **Write Access**: User can modify data (requires Read Access)
4. Click "Grant Access"

### 7. Revoke Pharmacy Access

1. Click "View" on a user
2. Click "Revoke" next to any pharmacy access you want to remove
3. Confirm the action

## API Endpoints

The admin interface uses the following API endpoints (all require Charl authentication):

- `GET /admin/users` - List all users
- `GET /admin/users/{user_id}` - Get user details
- `POST /admin/users` - Create new user
- `PUT /admin/users/{user_id}` - Update user
- `POST /admin/users/{user_id}/pharmacies` - Grant pharmacy access
- `DELETE /admin/users/{user_id}/pharmacies/{pharmacy_id}` - Revoke pharmacy access
- `GET /admin/pharmacies` - List all pharmacies

## Security

- **Authentication**: Uses JWT tokens from `/auth/login`
- **Authorization**: Only authorized admin users (user_id 2 for Charl, user_id 9 for Amin) can access admin endpoints
- **Token Storage**: Tokens are stored in browser localStorage
- **Session**: Tokens expire after 12 hours (as configured in auth system)

## Technical Details

- **Frontend**: Pure HTML/CSS/JavaScript (no framework)
- **Backend**: FastAPI with Jinja2 templates
- **Database**: Direct PostgreSQL queries
- **Authentication**: JWT-based via existing auth system

## Files

- `pharma_api/app/routers/admin.py` - Admin API endpoints
- `pharma_api/templates/admin.html` - Admin interface HTML
- `pharma_api/app/main.py` - Router registration

## Troubleshooting

### "Access denied" error
- Make sure you're logged in as an authorized admin user (Charl - user_id: 2, or Amin - user_id: 9)
- Check that your token hasn't expired (try logging out and back in)

### Can't see users
- Check browser console for errors
- Verify database connection
- Check that you're logged in (token in localStorage)

### Login not working
- Verify the admin user's username and password are correct
- Check that the `/auth/login` endpoint is working
- Check browser console for API errors

## Notes

- Passwords are hashed using SHA-256 (same as the main app)
- User creation automatically sets `is_active = true`
- Pharmacy access can be granted/revoked independently
- Write access requires read access (enforced by UI)

