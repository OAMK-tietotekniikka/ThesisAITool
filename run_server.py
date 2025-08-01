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
    if not os.path.exists("server"):
        print("❌ Error: server directory not found. Please run this script from the project root.")
        return
    
    # Check if client directory exists
    if not os.path.exists("client"):
        print("❌ Error: client directory not found.")
        return
    
    print("✅ Found server and client directories")
    
    # Check which server file to use
    use_new_structure = False
    if os.path.exists("server/main.py"):
        print("📁 Found new refactored structure (server/main.py)")
        use_new_structure = True
    elif os.path.exists("server/app.py"):
        print("📁 Found legacy structure (server/app.py)")
        use_new_structure = False
    else:
        print("❌ Error: No server file found. Neither server/main.py nor server/app.py exists.")
        return
    
    # Try to start the server
    try:
        # Change to server directory and start the app
        os.chdir("server")
        
        if use_new_structure:
            print("🔄 Starting with new refactored structure...")
            subprocess.run([sys.executable, "main.py"], check=True)
        else:
            print("🔄 Starting with legacy structure...")
            subprocess.run([sys.executable, "app.py"], check=True)
            
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        if use_new_structure:
            print("💡 Tip: The new structure may need route files to be implemented.")
            print("   Try running the legacy app.py instead: python server/app.py")

if __name__ == "__main__":
    main() 