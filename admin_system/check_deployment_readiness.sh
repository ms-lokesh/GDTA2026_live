#!/bin/bash
# Quick deployment helper script for Render

echo "=================================================="
echo "GDTA Admin System - Render Deployment Helper"
echo "=================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: Run this script from admin_system/ directory"
    exit 1
fi

echo "✅ Found app.py - in correct directory"
echo ""

# Check for required files
echo "Checking required files..."
required_files=("requirements.txt" "render.yaml" ".env.example" "app.py" "db/firebase_models.py")
missing_files=()

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ Missing: $file"
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo ""
    echo "❌ Missing required files. Cannot proceed."
    exit 1
fi

echo ""
echo "Checking dependencies..."

# Check for Python
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version)
    echo "  ✅ Python: $python_version"
else
    echo "  ❌ Python 3 not found"
    exit 1
fi

# Check for git
if command -v git &> /dev/null; then
    echo "  ✅ Git installed"
else
    echo "  ❌ Git not found"
    exit 1
fi

echo ""
echo "Checking environment setup..."

# Check for .env file
if [ -f ".env" ]; then
    echo "  ✅ .env file exists"
    
    # Check for critical environment variables
    if grep -q "GEMINI_API_KEY=" .env && ! grep -q "GEMINI_API_KEY=your-" .env; then
        echo "  ✅ GEMINI_API_KEY configured"
    else
        echo "  ⚠️  GEMINI_API_KEY not configured in .env"
    fi
    
    if grep -q "GMAIL_USER=" .env && ! grep -q "GMAIL_USER=your-" .env; then
        echo "  ✅ GMAIL_USER configured"
    else
        echo "  ⚠️  GMAIL_USER not configured in .env"
    fi
else
    echo "  ⚠️  .env file not found (okay if deploying to Render)"
fi

# Check for Firebase credentials
if [ -f "db/firebase-credentials.json" ]; then
    echo "  ✅ Firebase credentials found"
else
    echo "  ⚠️  db/firebase-credentials.json not found"
fi

echo ""
echo "Checking git repository..."

# Check if git repo initialized
if [ -d "../.git" ]; then
    echo "  ✅ Git repository initialized"
    
    # Check for remote
    if git remote -v | grep -q "origin"; then
        remote_url=$(git remote get-url origin)
        echo "  ✅ Git remote configured: $remote_url"
    else
        echo "  ⚠️  No git remote configured"
        echo "      Run: git remote add origin YOUR_GITHUB_REPO_URL"
    fi
    
    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo "  ⚠️  Uncommitted changes found"
        echo "      Run: git add . && git commit -m 'Update'"
    else
        echo "  ✅ No uncommitted changes"
    fi
else
    echo "  ❌ Not a git repository"
    echo "      Initialize with: git init"
    exit 1
fi

echo ""
echo "Generating SECRET_KEY for production..."
secret_key=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "  SECRET_KEY=$secret_key"
echo "  (Save this for Render environment variables)"

echo ""
echo "=================================================="
echo "Pre-Deployment Summary"
echo "=================================================="
echo ""
echo "✅ All required files present"
echo "✅ Dependencies available"
echo ""
echo "Next steps:"
echo ""
echo "1. Push to GitHub:"
echo "   cd .."
echo "   git add ."
echo "   git commit -m 'Prepare for deployment'"
echo "   git push origin main"
echo ""
echo "2. Go to Render: https://dashboard.render.com"
echo ""
echo "3. Create New Web Service:"
echo "   - Connect GitHub repository"
echo "   - Name: gdta-admin-system"
echo "   - Root Directory: admin_system"
echo "   - Build Command: pip install -r requirements.txt"
echo "   - Start Command: gunicorn app:app"
echo ""
echo "4. Add Environment Variables (see DEPLOYMENT_CHECKLIST.md)"
echo ""
echo "5. Deploy and test!"
echo ""
echo "📚 Full documentation:"
echo "   - RENDER_DEPLOYMENT.md (step-by-step guide)"
echo "   - DEPLOYMENT_CHECKLIST.md (pre-flight checklist)"
echo ""
echo "=================================================="
