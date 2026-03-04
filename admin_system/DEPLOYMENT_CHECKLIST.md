# Pre-Deployment Checklist

Complete this checklist before deploying to Render.

## ✅ Code Preparation

- [ ] All code pushed to GitHub
- [ ] `.gitignore` properly configured
- [ ] No sensitive data in repo (check with `git log --all --full-history -- firebase-credentials.json`)
- [ ] `requirements.txt` includes `gunicorn`
- [ ] `render.yaml` configured

## ✅ Firebase Setup

- [ ] Firebase project created
- [ ] Firestore database enabled
- [ ] Firebase credentials JSON downloaded
- [ ] Test Firebase connection locally
- [ ] Collections created: `events`, `admin_users`, `registrations`, `venues`, `volunteers`

## ✅ Gmail Setup

- [ ] Gmail account created/prepared
- [ ] 2-Step Verification enabled
- [ ] App Password generated (not regular password!)
- [ ] Test email sending locally

## ✅ Gemini API

- [ ] Google AI Studio account created
- [ ] Gemini API key obtained
- [ ] API key tested locally

## ✅ Environment Variables Ready

Copy these values (you'll need them in Render):

```bash
PYTHON_VERSION=3.11.0
FLASK_ENV=production
SECRET_KEY=<generate-random-32-char-string>
GEMINI_API_KEY=<your-gemini-key>
GMAIL_USER=<your-email@gmail.com>
GMAIL_APP_PASSWORD=<16-char-app-password>
FIREBASE_CREDENTIALS=<paste-entire-json-as-one-line>
CORS_ORIGINS=https://your-frontend-domain.com,https://gdta-2026-website.onrender.com
```

**Generate SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## ✅ Super Admin Account

- [ ] Created super admin locally: `python3 create_super_admin.py`
- [ ] Credentials saved securely:
  - Username: `super_admin`
  - Password: (saved in password manager)
  - Email: (verified)

## ✅ Local Testing

Test everything locally before deploying:

```bash
cd admin_system
python3 app.py
```

- [ ] Server starts without errors
- [ ] Admin dashboard loads: http://localhost:5000/static/admin-dashboard.html
- [ ] Super admin can login
- [ ] Can create new event
- [ ] Can create new admin
- [ ] Can view registrations (if any)
- [ ] Email system works (test registration)
- [ ] ID card generation works
- [ ] Chatbot responds

## ✅ Render Deployment

### Step 1: Create Web Service
- [ ] New Web Service created
- [ ] GitHub repo connected
- [ ] Root directory set to `admin_system`
- [ ] Build command: `pip install -r requirements.txt`
- [ ] Start command: `gunicorn app:app`

### Step 2: Environment Variables
- [ ] All environment variables added
- [ ] FIREBASE_CREDENTIALS properly formatted (one line JSON)
- [ ] SECRET_KEY generated uniquely for production

### Step 3: Deploy
- [ ] Initial deployment successful
- [ ] No errors in logs
- [ ] Service URL accessible

### Step 4: Post-Deployment Testing
- [ ] Admin dashboard accessible: `https://your-app.onrender.com/static/admin-dashboard.html`
- [ ] Super admin can login
- [ ] Create test event
- [ ] Create test admin
- [ ] Test registration flow
- [ ] Verify email delivery
- [ ] Check ID card generation
- [ ] Test chatbot

## ✅ Frontend Deployment (Static Site)

### Option A: Netlify/Vercel
- [ ] Static site deployed
- [ ] Custom domain configured (optional)
- [ ] SSL certificate active

### Option B: Render Static Site
- [ ] Static site service created
- [ ] Root directory set correctly
- [ ] Site accessible

### Frontend Updates
- [ ] Updated API endpoint in `register.html`:
  ```javascript
  const API_BASE_URL = 'https://your-admin-system.onrender.com';
  ```
- [ ] Updated CORS_ORIGINS in Render to include frontend domain
- [ ] Tested registration from frontend to backend

## ✅ Custom Domain (Optional)

### Admin System
- [ ] Domain purchased (e.g., `admin.gdta.org`)
- [ ] DNS CNAME record added:
  - Name: `admin`
  - Value: `your-app.onrender.com`
- [ ] SSL certificate issued (Render does automatically)
- [ ] Domain verified and working

### Public Website
- [ ] Domain configured (e.g., `gdta.org`)
- [ ] DNS records updated
- [ ] SSL active
- [ ] Registration form points to admin API

## ✅ Monitoring Setup

- [ ] Render email notifications enabled
- [ ] Uptime monitor configured (UptimeRobot, Pingdom, etc.)
- [ ] Health check endpoint working: `/`
- [ ] Logs reviewed for any warnings

## ✅ Documentation

- [ ] README updated with production URLs
- [ ] Admin credentials shared securely with team
- [ ] API documentation available
- [ ] Deployment notes recorded

## ✅ Security

- [ ] No secrets in git history
- [ ] Environment variables secure
- [ ] HTTPS only (enforced by Render)
- [ ] Session cookies secure
- [ ] CORS origins restricted to known domains
- [ ] Admin accounts use strong passwords
- [ ] 2FA enabled on critical accounts (GitHub, Firebase, Gmail)

## ✅ Backup Plan

- [ ] Firebase data export tested
- [ ] Local backup of registration data
- [ ] Recovery procedure documented
- [ ] Rollback plan prepared

---

## 🚨 Common Issues & Solutions

### Issue: Build fails with module not found
**Solution**: Ensure `requirements.txt` includes all dependencies

### Issue: App crashes on start
**Solution**: Check environment variables, especially FIREBASE_CREDENTIALS format

### Issue: CORS errors from frontend
**Solution**: Add frontend domain to CORS_ORIGINS environment variable

### Issue: Email not sending
**Solution**: Verify Gmail App Password (not regular password)

### Issue: Firebase connection fails
**Solution**: Check FIREBASE_CREDENTIALS is valid JSON, Firestore is enabled

---

## 📞 Emergency Contacts

- **Super Admin**: (save securely)
- **Firebase Admin**: (save securely)
- **Domain Registrar**: (save credentials)
- **Render Support**: https://render.com/support

---

**Checklist Version**: 1.0  
**Last Updated**: March 2026  
**Project**: GDTA Admin System
