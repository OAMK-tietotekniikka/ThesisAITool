#!/usr/bin/env python3
"""
Test script to verify the fixes work
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_register_and_login():
    """Test user registration and login"""
    print("=== Testing Registration and Login ===")
    
    # Register a test user
    register_data = {
        'username': 'testuser2',
        'email': 'test2@example.com',
        'full_name': 'Test User 2',
        'password': 'testpass',
        'role': 'student'
    }
    
    try:
        response = requests.post(f'{BASE_URL}/auth/register', data=register_data)
        print(f"Registration Status: {response.status_code}")
        print(f"Registration Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Registration successful!")
        else:
            print("❌ Registration failed!")
            return None
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None
    
    # Login
    login_data = {
        'username': 'testuser2',
        'password': 'testpass',
        'grant_type': 'password'
    }
    
    try:
        response = requests.post(f'{BASE_URL}/auth/token', data=login_data)
        print(f"Login Status: {response.status_code}")
        print(f"Login Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
            return response.json()['access_token']
        else:
            print("❌ Login failed!")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_delete_user(token):
    """Test delete user functionality"""
    print("\n=== Testing Delete User ===")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        # First get all users
        response = requests.get(f'{BASE_URL}/users/users', headers=headers)
        print(f"Get Users Status: {response.status_code}")
        
        if response.status_code == 200:
            users = response.json()
            print(f"Found {len(users)} users")
            
            # Try to delete a test user (if it exists)
            test_username = 'testuser2'
            response = requests.delete(f'{BASE_URL}/users/users/{test_username}', headers=headers)
            print(f"Delete User Status: {response.status_code}")
            print(f"Delete User Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ Delete user successful!")
            else:
                print("❌ Delete user failed!")
        else:
            print("❌ Get users failed!")
    except Exception as e:
        print(f"❌ Delete user error: {e}")

def test_ai_feedback_options(token):
    """Test AI feedback options endpoint"""
    print("\n=== Testing AI Feedback Options ===")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(f'{BASE_URL}/ai/feedback-options', headers=headers)
        print(f"AI Feedback Options Status: {response.status_code}")
        print(f"AI Feedback Options Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ AI feedback options successful!")
        else:
            print("❌ AI feedback options failed!")
    except Exception as e:
        print(f"❌ AI feedback options error: {e}")

if __name__ == "__main__":
    print("Testing the fixes...")
    
    # Test registration and login
    token = test_register_and_login()
    
    if token:
        # Test delete user
        test_delete_user(token)
        
        # Test AI feedback options
        test_ai_feedback_options(token)
    else:
        print("❌ Cannot proceed with tests without authentication token") 