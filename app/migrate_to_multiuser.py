#!/usr/bin/env python3
"""
Migration Script: Single-User to Multi-User Database

This script migrates the existing single-user vocabulary database
to the new multi-user schema while preserving all existing data.

Usage:
    python migrate_to_multiuser.py [--backup-old] [--admin-email EMAIL]

Author: Migration Script
Date: August 2025
"""

import sys
import os
import argparse
from multi_user_database_manager import migrate_single_user_to_multiuser, MultiUserDatabaseManager


def main():
    parser = argparse.ArgumentParser(description='Migrate single-user database to multi-user schema')
    parser.add_argument('--backup-old', action='store_true', 
                       help='Create backup of old database (default: True)')
    parser.add_argument('--admin-email', default='admin@vocabulary.app',
                       help='Email for the default admin user (default: admin@vocabulary.app)')
    parser.add_argument('--old-db', default='data/vocabulary.db',
                       help='Path to existing single-user database')
    parser.add_argument('--new-db', default='data/vocabulary_multiuser.db',
                       help='Path for new multi-user database')
    
    args = parser.parse_args()
    
    print("🔄 Starting migration from single-user to multi-user database...")
    print(f"📂 Old database: {args.old_db}")
    print(f"📂 New database: {args.new_db}")
    print(f"👤 Admin email: {args.admin_email}")
    print()
    
    # Check if old database exists
    if not os.path.exists(args.old_db):
        print(f"❌ Old database not found: {args.old_db}")
        print("ℹ️  Creating new multi-user database instead...")
        
        # Create new database with default admin user
        db_manager = MultiUserDatabaseManager(args.new_db)
        success, message, user_id = db_manager.create_user(
            email=args.admin_email,
            username="admin",
            password="admin123"
        )
        
        if success:
            print(f"✅ Created new multi-user database with admin user")
            print(f"🔑 Login credentials:")
            print(f"   Email: {args.admin_email}")
            print(f"   Password: admin123")
            print(f"   ⚠️  Please change the password immediately!")
        else:
            print(f"❌ Failed to create admin user: {message}")
            return 1
        
        return 0
    
    # Check if new database already exists
    if os.path.exists(args.new_db):
        response = input(f"⚠️  New database already exists: {args.new_db}\nOverwrite? (y/N): ")
        if response.lower() != 'y':
            print("❌ Migration cancelled")
            return 1
        
        # Remove existing new database
        os.remove(args.new_db)
        print(f"🗑️  Removed existing database: {args.new_db}")
    
    # Perform migration
    success = migrate_single_user_to_multiuser(
        old_db_path=args.old_db,
        new_db_path=args.new_db,
        default_user_email=args.admin_email
    )
    
    if success:
        print()
        print("🎉 Migration completed successfully!")
        print()
        print("📋 Next steps:")
        print("1. Update your application to use the new database")
        print("2. Update web_flashcards.py to use MultiUserDatabaseManager")
        print("3. Add authentication to your Flask routes")
        print("4. Test the application with the new multi-user system")
        print()
        print("🔧 To switch to the new database:")
        print(f"   mv {args.old_db} {args.old_db}.old")
        print(f"   mv {args.new_db} {args.old_db}")
        print()
        return 0
    else:
        print("❌ Migration failed!")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
