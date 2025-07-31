#!/usr/bin/env python3
"""
Generate a secure JWT secret key for ThesisAI server
"""

import secrets
import string

def generate_jwt_secret(length=64):
    """Generate a secure random JWT secret key"""
    # Use a combination of letters, digits, and special characters
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Generate a secure random string
    secret = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    return secret

def main():
    print("🔐 ThesisAI JWT Secret Key Generator")
    print("=" * 50)
    
    # Generate a secure secret key
    jwt_secret = generate_jwt_secret()
    
    print(f"\n✅ Generated JWT Secret Key:")
    print(f"JWT_SECRET_KEY={jwt_secret}")
    
    print(f"\n📝 Add this to your .env file:")
    print(f"JWT_SECRET_KEY={jwt_secret}")
    
    print(f"\n⚠️  Security Notes:")
    print(f"- Keep this secret key secure and private")
    print(f"- Never commit it to version control")
    print(f"- Use different keys for development and production")
    print(f"- The key is {len(jwt_secret)} characters long")
    
    print(f"\n🚀 Next steps:")
    print(f"1. Copy the JWT_SECRET_KEY line above")
    print(f"2. Paste it into your .env file")
    print(f"3. Restart your server")

if __name__ == "__main__":
    main() 