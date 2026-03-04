# Render Deployment Guide

Complete guide to deploy GDTA Admin System on Render.

## 📋 Prerequisites

1. **GitHub account** with your code pushed
2. **Render account** (free tier available): https://render.com
3. **Firebase project** with credentials
4. **Gmail account** with App Password
5. **Gemini API key** from Google AI Studio

---

## 🚀 Part 1: Deploy Admin System (Flask App)

### Step 1: Prepare Repository

Push your code to GitHub:
```bash
cd /Users/user/gdta/GDTA2026
git init
git add .
git commit -m "Initial commit - GDTA admin system"
git branch -M main
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### Step 2: Create Web Service on Render

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `gdta-admin-system`
   - **Region**: Oregon (US West)
   - **Branch**: `main`
   - **Root Directory**: `admin_system`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free

### Step 3: Set Environment Variables

In Render dashboard → Environment tab, add:

| Key | Value | Notes |
|-----|-------|-------|
| `PYTHON_VERSION` | `3.11.0` | Python version |
| `FLASK_ENV` | `production` | Environment |
| `SECRET_KEY` | (generate random) | Use Render's "Generate" button |
| `GEMINI_API_KEY` | `your-gemini-key` | From Google AI Studio |
| `GMAIL_USER` | `your-email@gmail.com` | Gmail for sending emails |
| `GMAIL_APP_PASSWORD` | `your-app-password` | Gmail App Password (not regular password) |
| `FIREBASE_CREDENTIALS` | (see below) | Firebase credentials JSON |

#### Setting FIREBASE_CREDENTIALS

**Option A: Environment Variable (Simple)**
1. Open `db/firebase-credentials.json`
2. Copy entire JSON content (minified, one line)
3. Paste as value for `FIREBASE_CREDENTIALS` in Render

**Option B: File Upload (Recommended)**
1. In `db/firebase_config.py`, update to read from file path
2. Use Render's "Persistent Disk" feature
3. Upload `firebase-credentials.json` to disk

### Step 4: Update Firebase Config

If using Option B, update `db/firebase_config.py`:

```python
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    if not firebase_admin._apps:
        # Try environment variable first
        cred_json = os.getenv('FIREBASE_CREDENTIALS')
        
        if cred_json:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        else:
            # Fallback to file
            cred_path = os.path.join(os.path.dirname(__file__), 'firebase-credentials.json')
            cred = credentials.Certificate(cred_path)
        
        firebase_admin.initialize_app(cred)
    
    return firestore.client()
```

### Step 5: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repo
   - Install dependencies
   - Start the app
3. Wait 3-5 minutes for deployment
4. You'll get a URL: `https://gdta-admin-system.onrender.com`

### Step 6: Test Deployment

Visit:
- Admin Dashboard: `https://gdta-admin-system.onrender.com/static/admin-dashboard.html`
- Health Check: `https://gdta-admin-system.onrender.com/`

Login with your super admin credentials.

---

## 🌐 Part 2: Deploy Public Website (Static Site)

### Option A: Separate Static Site on Render

1. In Render dashboard, click **"New +"** → **"Static Site"**
2. Connect same GitHub repo
3. Configure:
   - **Name**: `gdta-2026-website`
   - **Branch**: `main`
   - **Root Directory**: Leave empty (uses root)
   - **Build Command**: Leave empty (no build needed)
   - **Publish Directory**: `.` (current directory)

4. Deploy → Get URL: `https://gdta-2026-website.onrender.com`

### Option B: Netlify or Vercel (Recommended)

For static sites, Netlify/Vercel offer better performance:

**Netlify:**
1. Go to https://app.netlify.com
2. Drag & drop the root folder
3. Or connect GitHub repo

**Vercel:**
1. Go to https://vercel.com
2. Import GitHub repository
3. Set root directory to `./`

---

## 🔧 Configuration Updates

### Update Registration Form

In root `register.html`, update API endpoint:

```html
<script>
const API_BASE_URL = 'https://gdta-admin-system.onrender.com';

// Registration form submit
$('#registrationForm').submit(function(e) {
    e.preventDefault();
    
    $.ajax({
        url: API_BASE_URL + '/api/register',
        method: 'POST',
        // ... rest of code
    });
});
</script>
```

### Enable CORS

Ensure admin system allows frontend domain. In `app.py`:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=[
    'https://gdta-2026-website.onrender.com',
    'https://gdta.org',
    'http://localhost:*'
])
```

---

## 📊 Monitoring & Maintenance

### Check Logs

In Render dashboard:
- Click your service
- Go to "Logs" tab
- Monitor for errors

### Auto-Deploy

Render auto-deploys on git push:
```bash
git add .
git commit -m "Update feature"
git push
# Render automatically deploys
```

### Custom Domain

1. Render dashboard → Settings
2. Add custom domain: `admin.gdta.org`
3. Update DNS:
   - Type: CNAME
   - Name: admin
   - Value: `gdta-admin-system.onrender.com`

---

## 🆓 Free Tier Limitations

**Render Free Tier:**
- ⏰ Spins down after 15 min inactivity
- ⚡ First request after spin-down: 30-60s delay
- 💾 750 hours/month (enough for one service)
- 🌐 Free SSL certificate included

**Workaround:** Use a cron job to ping every 14 minutes:
```bash
# External service (cron-job.org)
GET https://gdta-admin-system.onrender.com/health
Every 14 minutes
```

---

## 🐛 Troubleshooting

### Build Fails
```
Error: No module named 'firebase_admin'
```
**Fix**: Ensure `requirements.txt` is in root of `admin_system/`

### App Won't Start
```
Error: Failed to bind to port
```
**Fix**: Ensure `app.py` has:
```python
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
```

### Firebase Error
```
Error: Could not load credentials
```
**Fix**: 
1. Verify `FIREBASE_CREDENTIALS` environment variable is set
2. Check JSON is valid (use jsonlint.com)
3. Ensure Firebase project has Firestore enabled

### CORS Error
```
Access to fetch blocked by CORS policy
```
**Fix**: Add frontend domain to CORS origins in `app.py`

---

## 📝 Production Checklist

Before going live:

- [ ] All environment variables set
- [ ] Firebase credentials working
- [ ] Gmail credentials working
- [ ] Gemini API key working
- [ ] Super admin account created
- [ ] Test registration flow end-to-end
- [ ] Test email delivery
- [ ] Test ID card generation
- [ ] Custom domain configured
- [ ] SSL certificate active (Render does this automatically)
- [ ] Backup database regularly

---

## 🔐 Security Best Practices

1. **Never commit secrets** to git
2. Use `.gitignore`:
   ```
   .env
   db/firebase-credentials.json
   static/generated_ids/*.png
   ```
3. **Rotate secrets** regularly:
   - SECRET_KEY
   - Gmail App Password
   - Firebase credentials
4. **Monitor access logs** in admin dashboard
5. **Enable 2FA** on admin accounts

---

## 📚 Additional Resources

- Render Docs: https://render.com/docs
- Flask Deployment: https://flask.palletsprojects.com/en/3.0.x/deploying/
- Firebase Admin SDK: https://firebase.google.com/docs/admin/setup

---

## 🆘 Support

**Admin System Issues:**
- Check Render logs for errors
- Verify environment variables
- Test locally first: `python3 app.py`

**Deployment Issues:**
- Render community: https://community.render.com
- GitHub Issues: Create issue in your repo

---

**Deployment Date**: March 2026  
**Version**: 1.0  
**Platform**: Render.com
