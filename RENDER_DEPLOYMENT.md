# 🚀 Render Deployment Guide for Pharmacy API

Complete step-by-step guide to deploy your Pharmacy API on Render.com

## 📋 Prerequisites

- ✅ GitHub repository: `pharmacy-api-webservice`
- ✅ Render.com account (free tier available)
- ✅ PostgreSQL database (Render provides this too)

## 🎯 Step-by-Step Deployment

### **Step 1: Sign Up for Render**

1. Go to [render.com](https://render.com)
2. Click **"Get Started"** or **"Sign Up"**
3. Choose **"Continue with GitHub"** (recommended)
4. Authorize Render to access your GitHub repositories

### **Step 2: Create a New Web Service**

1. In your Render dashboard, click **"New +"**
2. Select **"Web Service"**
3. Click **"Connect"** next to your `pharmacy-api-webservice` repository
4. Render will automatically detect it's a Python application

### **Step 3: Configure Your Web Service**

Fill in these settings:

```
Name: pharmacy-api-webservice
Environment: Python 3
Region: Choose closest to your users
Branch: main
Build Command: pip install -r pharma_api/requirements.txt
Start Command: cd pharma_api && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### **Step 4: Set Environment Variables**

Click **"Environment"** and add these variables:

#### **Required Variables:**
```
DATABASE_URL=postgresql://username:password@host:port/database
API_KEY=your-super-secret-api-key-here
```

#### **Optional Variables:**
```
CORS_ALLOW_ORIGINS=*
CORS_ALLOW_CREDENTIALS=false
STATEMENT_TIMEOUT_MS=30000
```

### **Step 5: Create PostgreSQL Database**

1. In Render dashboard, click **"New +"**
2. Select **"PostgreSQL"**
3. Choose **"Starter"** plan (free tier)
4. Name it: `pharmacy-database`
5. Choose the same region as your web service
6. Click **"Create Database"**

### **Step 6: Connect Database to Web Service**

1. Go back to your web service settings
2. Click **"Environment"**
3. Add the database connection:
   - **Key**: `DATABASE_URL`
   - **Value**: Copy from your PostgreSQL service dashboard
   - Format: `postgresql://username:password@host:port/database`

### **Step 7: Deploy Your Service**

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Build your application
   - Start the service

### **Step 8: Wait for Deployment**

- **Build time**: 2-5 minutes
- **Deploy time**: 1-2 minutes
- **Total**: Usually under 10 minutes

## 🔧 Configuration Details

### **Build Command**
```bash
pip install -r pharma_api/requirements.txt
```

### **Start Command**
```bash
cd pharma_api && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### **Health Check**
- **Path**: `/health`
- **Expected Response**: `{"ok": true}`

## 🌐 Access Your Deployed API

Once deployed, your API will be available at:
```
https://pharmacy-api-webservice.onrender.com
```

### **Test Your Deployment:**
```bash
# Health check
curl https://pharmacy-api-webservice.onrender.com/health

# Test with API key
curl -H "Authorization: Bearer your-api-key" \
     https://pharmacy-api-webservice.onrender.com/pharmacies
```

## 📊 Monitoring & Logs

### **View Logs:**
1. Go to your web service dashboard
2. Click **"Logs"** tab
3. Monitor real-time application logs

### **Health Status:**
- **Green**: Service is healthy
- **Yellow**: Service is starting/restarting
- **Red**: Service has failed

## 🚨 Troubleshooting

### **Common Issues:**

#### **1. Build Failures**
- Check `requirements.txt` for missing dependencies
- Verify Python version compatibility
- Check build logs for specific errors

#### **2. Database Connection Issues**
- Verify `DATABASE_URL` is correct
- Ensure database is in the same region
- Check database credentials

#### **3. Service Won't Start**
- Verify `startCommand` is correct
- Check if port `$PORT` is being used
- Review application logs

#### **4. 500 Internal Server Errors**
- Check database connectivity
- Verify environment variables
- Review application logs for Python errors

### **Debug Commands:**
```bash
# Check if service is running
curl -I https://your-service.onrender.com/health

# Test database connection
curl -H "Authorization: Bearer your-api-key" \
     https://your-service.onrender.com/pharmacies
```

## 🔄 Auto-Deployment

### **Enable Auto-Deploy:**
1. In your web service settings
2. Go to **"Settings"** tab
3. Enable **"Auto-Deploy"**
4. Every push to `main` branch will trigger deployment

### **Manual Deploy:**
1. Go to **"Manual Deploy"** section
2. Click **"Deploy latest commit"**

## 💰 Cost Management

### **Free Tier Limits:**
- **Web Service**: 750 hours/month
- **PostgreSQL**: 90 days free trial
- **Bandwidth**: 100GB/month

### **Upgrade When Needed:**
- **Starter Plan**: $7/month (always on)
- **Standard Plan**: $25/month (better performance)

## 🎉 Success Checklist

- ✅ Service is deployed and running
- ✅ Health check returns `{"ok": true}`
- ✅ Database connection is working
- ✅ API endpoints are responding
- ✅ CORS is configured correctly
- ✅ Environment variables are set
- ✅ Auto-deploy is enabled

## 🔗 Useful Links

- **Your API**: `https://pharmacy-api-webservice.onrender.com`
- **API Docs**: `https://pharmacy-api-webservice.onrender.com/docs`
- **Health Check**: `https://pharmacy-api-webservice.onrender.com/health`
- **Render Dashboard**: [dashboard.render.com](https://dashboard.render.com)

## 🆘 Need Help?

- **Render Documentation**: [docs.render.com](https://docs.render.com)
- **FastAPI Documentation**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **Community Support**: Render Discord/Forums

---

**🎯 Your Pharmacy API will be live and accessible from anywhere in the world!** 