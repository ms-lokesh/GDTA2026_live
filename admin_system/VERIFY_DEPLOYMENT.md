# Verify Render Deployment

This guide helps you verify that your Render deployment is working correctly with all the latest fixes.

## 📌 What Was Fixed

Recent fixes pushed to `render-deployment` branch:
1. ✅ Added `event_id` field to all registration submissions
2. ✅ Fixed Event.save() method for custom IDs
3. ✅ Migrated all existing registrations to `event_id='gdta-2026'`
4. ✅ Updated admin user assigned_events to `['gdta-2026']`

## 🔍 Step 1: Check Deployment Status

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Find your service: **gdta-admin-system**
3. Check the **Events** tab to see if the latest commit deployed:
   - Latest commit: `4a6e85e - Fix: Migrate all existing registrations to event_id='gdta-2026'`
4. Wait for deployment to complete (usually 2-5 minutes)

## 🧪 Step 2: Test the Deployment

### A. Health Check

Visit your Render URL (replace with your actual URL):
```
https://gdta-admin-system.onrender.com/
```

You should see:
```json
{
  "service": "GDTA 2026 Chatbot Backend",
  "status": "running",
  "version": "2.0.0"
}
```

### B. Test Admin Login

1. Go to: `https://gdta-admin-system.onrender.com/static/admin-dashboard.html`
2. Login with:
   - Username: `admin`
   - Password: `admin123`
3. ✅ Should successfully log in

### C. Check Registrations Display

After logging in:
1. Click **"Registration Management"** in the sidebar
2. **IMPORTANT**: Check if you see an event selector dropdown
   - If you're a regular admin: registrations should load automatically
   - If you're a super admin: select "GDTA 2026 (2026)" from the dropdown
3. ✅ You should see all 9 registrations displayed

**If registrations don't show:**
- Check browser console for errors (F12 → Console tab)
- Verify the event selector shows "GDTA 2026 (2026)"
- Try refreshing the page

## 🔧 Step 3: Run Post-Deployment Setup (If Needed)

If registrations still don't show, you need to run the migration script on Render:

### Option A: Using Render Shell (Recommended)

1. Go to your service in Render Dashboard
2. Click **"Shell"** tab
3. Run:
```bash
python3 setup_render.py
```

Expected output:
```
============================================================
GDTA 2026 - Post-Deployment Setup
============================================================

1. Initializing Firebase...
✓ Firebase initialized

2. Checking GDTA 2026 event...
✓ Event exists: GDTA 2026

3. Migrating registrations...
  Found 9 registrations
✓ All registrations already have correct event_id

4. Updating admin user...
✓ Admin already assigned to gdta-2026

============================================================
Setup Complete!
============================================================
✓ Total registrations with event_id='gdta-2026': 9
✓ Event 'GDTA 2026' is active
✓ Admin dashboard ready
============================================================
```

### Option B: Trigger Automatic Re-deployment

If you can't access the shell:
1. Make a small change to any file (add a comment)
2. Commit and push to `render-deployment` branch
3. Render will auto-deploy and migrations will run on startup

## 📊 Step 4: Verify Data Integrity

### Test Registration Submission

1. Go to the main website registration page
2. Complete a test registration
3. Go to Admin Dashboard → Registration Management
4. ✅ New registration should appear immediately

### Check Existing Data

In Admin Dashboard:
- Click on any registration to view details
- ✅ Each registration should have:
  - `event_id`: gdta-2026
  - `unique_id`: 6-character code (e.g., "8AD54K")
  - Valid email, name, institution, etc.

## 🚨 Troubleshooting

### Issue: "No registrations found"

**Solution:**
1. Check browser Network tab (F12 → Network)
2. Look for `/api/admin/registrations` request
3. Check the response - if it returns empty array:
   - Run `setup_render.py` script on Render Shell
   - Verify Firebase credentials are set correctly

### Issue: "403 Forbidden" or "401 Unauthorized"

**Solution:**
1. Clear browser cookies
2. Log out and log back in
3. Check if admin user exists in Firebase

### Issue: Event selector shows "KYXOGU3AWNXirarWCW4N"

**Solution:**
1. Run `setup_render.py` on Render Shell
2. This will update admin assigned_events to `['gdta-2026']`
3. Log out and log back in

## ✅ Success Checklist

- [ ] Render deployment shows "Live" status
- [ ] Health check endpoint returns JSON response
- [ ] Admin login works
- [ ] Event selector shows "GDTA 2026 (2026)"
- [ ] All 9 registrations display in the table
- [ ] Can view individual registration details
- [ ] New registrations appear in dashboard
- [ ] Registration count matches Firebase data

## 📞 Need Help?

If issues persist:
1. Check Render logs: Dashboard → Logs tab
2. Look for error messages mentioning Firebase or authentication
3. Verify all environment variables are set:
   - `FIREBASE_CREDENTIALS`
   - `GEMINI_API_KEY`
   - `GMAIL_USER`
   - `GMAIL_APP_PASSWORD`
   - `SECRET_KEY`

## 🔗 Quick Links

- **Admin Dashboard**: `https://YOUR-SERVICE.onrender.com/static/admin-dashboard.html`
- **API Health**: `https://YOUR-SERVICE.onrender.com/`
- **Render Dashboard**: https://dashboard.render.com
- **Firebase Console**: https://console.firebase.google.com

---

**Last Updated**: March 5, 2026  
**Branch**: render-deployment  
**Latest Commit**: 4a6e85e
