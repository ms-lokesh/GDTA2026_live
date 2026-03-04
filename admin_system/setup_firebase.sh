#!/bin/bash
# Quick Start Script for Firebase Setup

echo "========================================="
echo "  GDTA 2026 - Firebase Setup"
echo "========================================="
echo ""

# Check if in correct directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: Please run this script from the chatbot directory"
    echo "   cd /Users/user/gdta/GDTA2026/chatbot"
    exit 1
fi

# Step 1: Install Firebase SDK
echo "📦 Step 1: Installing Firebase Admin SDK..."
pip3 install -q firebase-admin==6.4.0
echo "✅ Firebase SDK installed"
echo ""

# Step 2: Check for credentials file
echo "🔐 Step 2: Checking for Firebase credentials..."
if [ ! -f "firebase-credentials.json" ]; then
    echo "⚠️  Firebase credentials file not found!"
    echo ""
    echo "Please follow these steps:"
    echo "1. Go to https://console.firebase.google.com/"
    echo "2. Select your project (or create one)"
    echo "3. Go to Project Settings > Service Accounts"
    echo "4. Click 'Generate New Private Key'"
    echo "5. Save the downloaded JSON file as:"
    echo "   /Users/user/gdta/GDTA2026/chatbot/firebase-credentials.json"
    echo ""
    echo "📖 Full guide: chatbot/FIREBASE_SETUP.md"
    echo ""
    read -p "Press Enter after you've added the credentials file..."
    
    if [ ! -f "firebase-credentials.json" ]; then
        echo "❌ Still can't find credentials file. Exiting."
        exit 1
    fi
fi

echo "✅ Firebase credentials found"
echo ""

# Step 3: Initialize Firebase database
echo "🔥 Step 3: Initializing Firebase Firestore..."
python3 << 'EOF'
try:
    from db.firebase_models import init_firebase, create_default_admin
    print("Connecting to Firebase...")
    init_firebase()
    print("Creating default admin...")
    create_default_admin()
    print("✅ Firebase initialization complete!")
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPlease check:")
    print("1. Firebase credentials file is valid JSON")
    print("2. Firebase project exists and Firestore is enabled")
    print("3. Internet connection is working")
    exit(1)
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Firebase initialization failed"
    echo "📖 See FIREBASE_SETUP.md for troubleshooting"
    exit 1
fi

echo ""
echo "========================================="
echo "  ✅ Firebase Setup Complete!"
echo "========================================="
echo ""
echo "🎯 Next steps:"
echo "1. Start the server: python3 app.py"
echo "2. Admin dashboard: http://localhost:5000/admin"
echo "3. Login: admin / admin123"
echo ""
echo "📊 Your data is stored in:"
echo "   Firebase Firestore (free up to 1GB)"
echo "   Project: Check Firebase Console"
echo ""
echo "📖 Full documentation: chatbot/FIREBASE_SETUP.md"
echo ""
