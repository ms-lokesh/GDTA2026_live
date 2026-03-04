#!/usr/bin/env python3
"""
Script to create a super admin user directly in Firebase.
"""

from db.firebase_models import AdminUser
import sys

def create_super_admin():
    """Create a super admin user"""
    print("=== Create Super Admin ===\n")
    
    # Get user input
    username = input("Enter username: ").strip()
    if not username or len(username) < 3:
        print("❌ Username must be at least 3 characters")
        return False
    
    name = input("Enter full name: ").strip()
    if not name:
        print("❌ Name is required")
        return False
    
    email = input("Enter email (optional, press Enter to skip): ").strip()
    email = email if email else None
    
    password = input("Enter password (min 8 characters): ").strip()
    if not password or len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return False
    
    # Check if username already exists
    existing = AdminUser.get_by_username(username)
    if existing:
        print(f"❌ Username '{username}' already exists")
        return False
    
    # Create super admin
    print("\nCreating super admin...")
    admin = AdminUser(
        username=username,
        name=name,
        email=email,
        role='super_admin',
        is_active=True
    )
    
    # Set password
    admin.set_password(password)
    
    # Save to Firestore
    admin.save()
    
    print(f"\n✅ Super admin created successfully!")
    print(f"\nUsername: {admin.username}")
    print(f"Name: {admin.name}")
    print(f"Email: {admin.email or 'Not set'}")
    print(f"Role: {admin.role}")
    print(f"\nYou can now login at: http://localhost:5000/static/admin-dashboard.html")
    return True

if __name__ == "__main__":
    try:
        success = create_super_admin()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
