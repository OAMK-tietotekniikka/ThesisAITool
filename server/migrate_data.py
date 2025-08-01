#!/usr/bin/env python3
"""
Migration script to populate SQLite database with existing mock data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import user_repo, thesis_repo, feedback_repo
from passlib.context import CryptContext
import uuid

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def migrate_mock_data():
    """Migrate mock data from app.py to SQLite database"""
    print("🔄 Starting migration of mock data to SQLite database...")
    
    # Mock users data from app.py
    mock_users = {
        "admin": {
            "username": "admin",
            "email": "admin@gmail.com",
            "full_name": "Admin User",
            "hashed_password": pwd_context.hash("1234"),
            "role": "admin"
        },
        "gv": {
            "username": "gv",
            "email": "gv@gmail.com",
            "full_name": "Dr. Jane Smith",
            "hashed_password": pwd_context.hash("1234"),
            "role": "supervisor",
            "assigned_students": [],
        },
        "gv0": {
            "username": "gv0",
            "email": "gv0@gmail.com",
            "full_name": "Dr. Billy Andersson",
            "hashed_password": pwd_context.hash("1234"),
            "role": "supervisor",
            "assigned_students": ["sv"],
        },
        "sv": {
            "username": "sv",
            "email": "sv@gmail.com",
            "full_name": "John Doe",
            "hashed_password": pwd_context.hash("1234"),
            "role": "student",
            "supervisor_id": "gv0"
        },
        "sv2": {
            "username": "sv2",
            "email": "sv2@gmail.com",
            "full_name": "New Student",
            "hashed_password": pwd_context.hash("1234"),
            "role": "student",
        },
    }
    
    # Migrate users
    print("📝 Migrating users...")
    migrated_users = {}
    
    for username, user_data in mock_users.items():
        try:
            # Generate UUID for user ID
            user_data['id'] = str(uuid.uuid4())
            
            # Check if user already exists
            existing_user = user_repo.get_user_by_username(username)
            if existing_user:
                print(f"⚠️  User {username} already exists, skipping...")
                migrated_users[username] = existing_user
                continue
            
            # Create user
            created_user = user_repo.create_user(user_data)
            migrated_users[username] = created_user
            print(f"✅ Created user: {username} ({created_user['full_name']})")
            
        except Exception as e:
            print(f"❌ Error creating user {username}: {str(e)}")
    
    # Update supervisor assignments
    print("🔗 Updating supervisor assignments...")
    for username, user_data in mock_users.items():
        if user_data.get('supervisor_id'):
            try:
                user_repo.assign_supervisor(username, user_data['supervisor_id'])
                print(f"✅ Assigned {username} to supervisor {user_data['supervisor_id']}")
            except Exception as e:
                print(f"❌ Error assigning supervisor for {username}: {str(e)}")
    
    print("✅ Migration completed successfully!")
    print(f"📊 Migrated {len(migrated_users)} users")
    
    return migrated_users

def check_database_status():
    """Check database status and show statistics"""
    print("\n📊 Database Status:")
    
    # Count users by role
    users = user_repo.get_all_users()
    role_counts = {}
    for user in users:
        role = user['role']
        role_counts[role] = role_counts.get(role, 0) + 1
    
    print(f"👥 Total users: {len(users)}")
    for role, count in role_counts.items():
        print(f"   - {role.capitalize()}s: {count}")
    
    # Count theses
    theses = thesis_repo.get_all_theses()
    print(f"📄 Total theses: {len(theses)}")
    
    # Count feedback
    feedback_count = 0
    for thesis in theses:
        feedback = feedback_repo.get_feedback_by_thesis_id(thesis['id'])
        feedback_count += len(feedback)
    print(f"💬 Total feedback entries: {feedback_count}")
    
    print("\n✅ Database is ready for production use!")

if __name__ == "__main__":
    try:
        migrated_users = migrate_mock_data()
        check_database_status()
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1) 