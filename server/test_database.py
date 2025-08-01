#!/usr/bin/env python3
"""
Test script to verify database integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import user_repo, thesis_repo, feedback_repo
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_database_integration():
    """Test database integration"""
    print("🧪 Testing database integration...")
    
    # Test 1: Get all users
    print("\n1. Testing user retrieval...")
    users = user_repo.get_all_users()
    print(f"   Found {len(users)} users")
    for user in users:
        print(f"   - {user['username']} ({user['role']})")
    
    # Test 2: Get user by username
    print("\n2. Testing user lookup...")
    admin_user = user_repo.get_user_by_username("admin")
    if admin_user:
        print(f"   ✅ Found admin user: {admin_user['full_name']}")
    else:
        print("   ❌ Admin user not found")
    
    # Test 3: Get supervisors
    print("\n3. Testing supervisor retrieval...")
    supervisors = user_repo.get_users_by_role("supervisor")
    print(f"   Found {len(supervisors)} supervisors")
    for supervisor in supervisors:
        print(f"   - {supervisor['full_name']} (assigned students: {len(supervisor['assigned_students'])})")
    
    # Test 4: Get students
    print("\n4. Testing student retrieval...")
    students = user_repo.get_users_by_role("student")
    print(f"   Found {len(students)} students")
    for student in students:
        supervisor_name = "None"
        if student['supervisor_id']:
            supervisor = user_repo.get_user_by_username(student['supervisor_id'])
            if supervisor:
                supervisor_name = supervisor['full_name']
        print(f"   - {student['full_name']} (supervisor: {supervisor_name})")
    
    # Test 5: Test thesis operations
    print("\n5. Testing thesis operations...")
    theses = thesis_repo.get_all_theses()
    print(f"   Found {len(theses)} theses")
    
    # Test 6: Test feedback operations
    print("\n6. Testing feedback operations...")
    feedback_count = 0
    for thesis in theses:
        feedback = feedback_repo.get_feedback_by_thesis_id(thesis['id'])
        feedback_count += len(feedback)
    print(f"   Found {feedback_count} feedback entries")
    
    print("\n✅ Database integration test completed successfully!")

def test_authentication():
    """Test authentication with database"""
    print("\n🔐 Testing authentication...")
    
    # Test admin login
    admin_user = user_repo.get_user_by_username("admin")
    if admin_user:
        password_correct = pwd_context.verify("1234", admin_user['hashed_password'])
        if password_correct:
            print("   ✅ Admin authentication works")
        else:
            print("   ❌ Admin authentication failed")
    else:
        print("   ❌ Admin user not found")
    
    # Test student login
    student_user = user_repo.get_user_by_username("sv")
    if student_user:
        password_correct = pwd_context.verify("1234", student_user['hashed_password'])
        if password_correct:
            print("   ✅ Student authentication works")
        else:
            print("   ❌ Student authentication failed")
    else:
        print("   ❌ Student user not found")

if __name__ == "__main__":
    try:
        test_database_integration()
        test_authentication()
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 