#!/usr/bin/env python3
"""
Test script to verify the edit user functionality works
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login_admin():
    """Login as an existing admin user for testing"""
    print("=== Testing Admin Login ===")
    
    # Login as existing admin
    login_data = {
        'username': 'admin_test2',
        'password': 'adminpass',
        'grant_type': 'password'
    }
    
    try:
        response = requests.post(f'{BASE_URL}/auth/token', data=login_data)
        print(f"Admin Login Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Admin login successful!")
            return response.json()['access_token']
        else:
            print(f"❌ Admin login failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Admin login error: {e}")
        return None

def test_use_existing_user():
    """Use an existing test user for editing"""
    print("\n=== Using Existing Test User ===")
    
    # Use an existing test user
    test_username = 'testuser_edit3'
    print(f"Using existing user: {test_username}")
    return True

def test_get_all_users(token):
    """Test getting all users to verify the test user exists"""
    print("\n=== Testing Get All Users ===")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(f'{BASE_URL}/users/users', headers=headers)
        print(f"Get All Users Status: {response.status_code}")
        
        if response.status_code == 200:
            users = response.json()
            print(f"Found {len(users)} users")
            for user in users:
                print(f"  - {user['username']}: {user['full_name']} ({user['role']})")
            return users
        else:
            print(f"❌ Get all users failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Get all users error: {e}")
        return None

def test_get_user(token):
    """Test getting user details"""
    print("\n=== Testing Get User ===")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(f'{BASE_URL}/users/testuser_edit3', headers=headers)
        print(f"Get User Status: {response.status_code}")
        print(f"Get User Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Get user successful!")
            return response.json()
        else:
            print("❌ Get user failed!")
            return None
    except Exception as e:
        print(f"❌ Get user error: {e}")
        return None

def test_update_user(token):
    """Test updating user details"""
    print("\n=== Testing Update User ===")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Update user data
    update_data = {
        'email': 'updated@example.com',
        'full_name': 'Updated Test User',
        'role': 'supervisor'
    }
    
    try:
        response = requests.put(f'{BASE_URL}/users/testuser_edit3', data=update_data, headers=headers)
        print(f"Update User Status: {response.status_code}")
        print(f"Update User Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Update user successful!")
            return True
        else:
            print("❌ Update user failed!")
            return False
    except Exception as e:
        print(f"❌ Update user error: {e}")
        return False

def test_verify_update(token):
    """Test verifying the user was updated"""
    print("\n=== Testing Verify Update ===")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(f'{BASE_URL}/users/testuser_edit3', headers=headers)
        print(f"Verify Update Status: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"Updated User Data: {json.dumps(user_data, indent=2)}")
            
            # Check if the update was successful
            if (user_data['email'] == 'updated@example.com' and 
                user_data['full_name'] == 'Updated Test User' and 
                user_data['role'] == 'supervisor'):
                print("✅ User update verification successful!")
                return True
            else:
                print("❌ User update verification failed - data doesn't match expected values!")
                return False
        else:
            print("❌ Verify update failed!")
            return False
    except Exception as e:
        print(f"❌ Verify update error: {e}")
        return False

if __name__ == "__main__":
    print("Testing the edit user functionality...")
    
    # Test admin login
    admin_token = test_login_admin()
    
    if admin_token:
        # Use an existing test user
        if test_use_existing_user():
            # Test getting all users to verify the test user exists
            all_users = test_get_all_users(admin_token)
            
            if all_users:
                # Test getting user details
                user_data = test_get_user(admin_token)
                
                if user_data:
                    # Test updating user
                    if test_update_user(admin_token):
                        # Test verifying the update
                        test_verify_update(admin_token)
                    else:
                        print("❌ Cannot proceed with verification without successful update")
                else:
                    print("❌ Cannot proceed with update without successful get user")
            else:
                print("❌ Cannot proceed with tests without successful get all users")
        else:
            print("❌ Cannot proceed with tests without test user")
    else:
        print("❌ Cannot proceed with tests without admin authentication") 