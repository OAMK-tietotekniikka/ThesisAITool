#!/usr/bin/env python3
"""
Simple test script for ThesisAI API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

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
        response = requests.post(f"{BASE_URL}/auth/register", data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_login():
    """Test user login"""
    print("\nTesting user login...")
    
    data = {
        'username': 'testuser',
        'password': 'testpass'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/token", data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_config_status():
    """Test config status endpoint"""
    print("\nTesting config status...")
    
    try:
        response = requests.get(f"{BASE_URL}/config/status")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=== ThesisAI API Test ===")
    
    # Test config status first (no auth required)
    config_ok = test_config_status()
    
    # Test registration
    register_ok = test_register()
    
    # Test login
    login_ok = test_login()
    
    print("\n=== Test Results ===")
    print(f"Config Status: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"Registration: {'✅ PASS' if register_ok else '❌ FAIL'}")
    print(f"Login: {'✅ PASS' if login_ok else '❌ FAIL'}")
    
    if config_ok and register_ok and login_ok:
        print("\n🎉 All tests passed! The API is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the server logs for details.") 