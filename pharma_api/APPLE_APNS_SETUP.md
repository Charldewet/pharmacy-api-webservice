# Apple Push Notification Service (APNs) Setup

## 🚀 **Your Backend Now Supports Both Expo AND Apple APNs!**

### **What This Fixes:**
- ✅ **Expo Go**: Still works with Expo Push Service
- ✅ **TestFlight**: Now works with Apple APNs
- ✅ **Production iOS**: Works with Apple APNs
- ✅ **Automatic Detection**: Backend detects device type and routes accordingly

## 🔧 **Setup Required:**

### **1. Get Apple Developer Credentials:**

1. **Go to [Apple Developer](https://developer.apple.com)**
2. **Navigate to Certificates, Identifiers & Profiles**
3. **Under Keys, create a new key with APNs enabled**
4. **Download the .p8 file**
5. **Note your Team ID and Key ID**

### **2. Set Environment Variables:**

Add these to your `.env` file or Render environment:

```bash
# Apple Push Notification Service
APPLE_TEAM_ID=ABC123DEF4
APPLE_KEY_ID=ABC123DEF4
APPLE_PRIVATE_KEY_PATH=/path/to/AuthKey_ABC123DEF4.p8
APPLE_BUNDLE_ID=com.yourcompany.yourapp
```

### **3. Upload .p8 Key File:**

**Option A: Render (Recommended)**
- Upload the .p8 file to your Render service
- Set `APPLE_PRIVATE_KEY_PATH` to the full path

**Option B: Local Development**
- Place .p8 file in your project
- Set path relative to project root

## 🎯 **How It Works Now:**

### **Device Detection:**
- **Expo tokens** (start with `ExponentPushToken[`) → **Expo Push Service**
- **Apple tokens** (64-character hex) → **Apple APNs**

### **Automatic Routing:**
- Backend detects device type automatically
- Sends to appropriate service
- Handles both success and error cases
- Marks invalid tokens as disabled

## 🧪 **Testing:**

### **1. TestFlight:**
- Log in on TestFlight app
- Device should stay active
- Notifications should arrive immediately

### **2. Expo Go:**
- Still works exactly as before
- No changes needed

### **3. Production iOS:**
- Will work with Apple APNs
- No Expo dependency

## 🚨 **Important Notes:**

- **TestFlight uses PRODUCTION APNs** (not sandbox)
- **.p8 key must have APNs enabled**
- **Bundle ID must match your app exactly**
- **Team ID is your Apple Developer Team ID**

## 🔍 **Troubleshooting:**

### **If TestFlight still doesn't work:**
1. Check environment variables are set
2. Verify .p8 file path is correct
3. Ensure Team ID and Key ID match
4. Check bundle ID matches exactly

### **If you get errors:**
- Check Render logs for Apple APNs errors
- Verify credentials are correct
- Ensure .p8 file is accessible

## 🎉 **Result:**

**Your TestFlight app will now receive push notifications directly from Apple's servers, not through Expo!** 