#!/usr/bin/env python3
"""
Simple test for the register endpoint
"""

import requests

def test_register():
    """Test user registration"""
    print("Testing user registration...")
    
    data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'full_name': 'Test User',
        'password': 'testpass',
        'role': 'student'
    }
    
    try:
        response = requests.post('http://localhost:8000/auth/register', data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=== Simple Register Test ===")
    success = test_register()
    if success:
        print("✅ Registration successful!")
    else:
        print("❌ Registration failed!") 