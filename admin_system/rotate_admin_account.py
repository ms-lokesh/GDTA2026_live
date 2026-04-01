"""
Rotate admin account in Firestore + Firebase Auth.

Usage:
  python rotate_admin_account.py \
    --old-username admin \
    --new-username <username> \
    --new-email <email> \
    --new-name <display_name> \
    --new-password <password>
"""

import argparse
from db.firebase_config import initialize_firebase, get_firestore_db
from db.firebase_models import AdminUser
from firebase_admin import auth as firebase_auth


def rotate_admin(old_username: str, new_username: str, new_email: str, new_name: str, new_password: str):
    initialize_firebase()
    db = get_firestore_db()

    old_username = old_username.strip()
    new_username = new_username.strip()
    new_email = new_email.strip()
    new_name = new_name.strip()

    # 1) Remove old Firestore admin doc if exists
    old_doc = db.collection('admin_users').document(old_username).get()
    if old_doc.exists:
        db.collection('admin_users').document(old_username).delete()
        print('OLD_FIRESTORE_ADMIN_DELETED=YES')
    else:
        print('OLD_FIRESTORE_ADMIN_DELETED=NO')

    # 2) Remove old Firebase Auth user if exists
    old_uid = f'admin:{old_username}'
    try:
        firebase_auth.delete_user(old_uid)
        print('OLD_FIREBASE_ADMIN_DELETED=YES')
    except firebase_auth.UserNotFoundError:
        print('OLD_FIREBASE_ADMIN_DELETED=NO')

    # 3) Create/update new Firestore admin doc
    existing = AdminUser.get_by_username(new_username)
    if existing:
        admin = existing
        print('NEW_FIRESTORE_ADMIN_EXISTED=YES')
    else:
        admin = AdminUser(
            username=new_username,
            email=new_email,
            name=new_name,
            role='admin',
            assigned_events=[],
            is_active=True
        )
        print('NEW_FIRESTORE_ADMIN_EXISTED=NO')

    admin.email = new_email
    admin.name = new_name
    admin.role = 'admin'
    admin.is_active = True
    admin.set_password(new_password)
    admin.save()
    print('NEW_FIRESTORE_ADMIN_SAVED=YES')

    # 4) Create/update new Firebase Auth user
    new_uid = f'admin:{new_username}'
    try:
        firebase_auth.get_user(new_uid)
        firebase_auth.update_user(
            new_uid,
            email=new_email,
            password=new_password,
            display_name=new_name,
            disabled=False,
        )
        print('NEW_FIREBASE_ADMIN_UPDATED=YES')
    except firebase_auth.UserNotFoundError:
        firebase_auth.create_user(
            uid=new_uid,
            email=new_email,
            password=new_password,
            display_name=new_name,
            disabled=False,
        )
        print('NEW_FIREBASE_ADMIN_CREATED=YES')

    print('ROTATION_STATUS=SUCCESS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Rotate admin account')
    parser.add_argument('--old-username', default='admin')
    parser.add_argument('--new-username', required=True)
    parser.add_argument('--new-email', required=True)
    parser.add_argument('--new-name', required=True)
    parser.add_argument('--new-password', required=True)

    args = parser.parse_args()
    rotate_admin(
        old_username=args.old_username,
        new_username=args.new_username,
        new_email=args.new_email,
        new_name=args.new_name,
        new_password=args.new_password,
    )
