#!/usr/bin/env python
"""
Script to promote a user to admin status in the TicketRush application.
Usage: python promote_admin.py <email>
"""

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the User model
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import User, db, app

def promote_to_admin(email):
    """Promote a user to admin by email address."""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"Error: User with email '{email}' not found.")
            return False
        
        if user.is_admin:
            print(f"User '{email}' is already an admin.")
            return True
        
        # Promote user to admin
        user.is_admin = True
        db.session.commit()
        
        print(f"Successfully promoted '{email}' to admin.")
        print(f"User details:")
        print(f"  - Name: {user.first_name} {user.last_name}")
        print(f"  - Business: {user.business_name}")
        print(f"  - Admin Status: {user.is_admin}")
        return True

def list_admins():
    """List all admin users in the system."""
    with app.app_context():
        admins = User.query.filter_by(is_admin=True).all()
        
        if not admins:
            print("No admin users found.")
            return
        
        print("\nCurrent Admin Users:")
        print("-" * 50)
        for admin in admins:
            print(f"  - {admin.email} ({admin.first_name} {admin.last_name})")

def remove_admin(email):
    """Remove admin privileges from a user."""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"Error: User with email '{email}' not found.")
            return False
        
        if not user.is_admin:
            print(f"User '{email}' is not an admin.")
            return True
        
        # Remove admin privileges
        user.is_admin = False
        db.session.commit()
        
        print(f"Successfully removed admin privileges from '{email}'.")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python promote_admin.py <email>           - Promote user to admin")
        print("  python promote_admin.py --list            - List all admin users")
        print("  python promote_admin.py --remove <email>  - Remove admin privileges")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_admins()
    elif sys.argv[1] == "--remove" and len(sys.argv) == 3:
        remove_admin(sys.argv[2])
    elif len(sys.argv) == 2:
        promote_to_admin(sys.argv[1])
    else:
        print("Invalid arguments. Use --help for usage information.")
        sys.exit(1)