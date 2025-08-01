#!/usr/bin/env python3
"""
Simple server startup script
"""
import os
import sys
import subprocess

def main():
    """Start the server with proper environment setup."""
    print("🚀 Starting ThesisAI Server...")
    
    # Check if we're in the right directory
    if not os.path.exists("server/app.py"):
        print("❌ Error: server/app.py not found. Please run this script from the project root.")
        return
    
    # Check if client directory exists
    if not os.path.exists("client"):
        print("❌ Error: client directory not found.")
        return
    
    print("✅ Found server and client directories")
    
    # Try to start the server
    try:
        # Change to server directory and start the app
        os.chdir("server")
        subprocess.run([sys.executable, "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main() 