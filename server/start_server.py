#!/usr/bin/env python3
"""
Startup script for the ThesisAI server with better error handling.
"""

import sys
import os
import uvicorn
from dotenv import load_dotenv

def main():
    """Start the server with proper error handling."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Check if API key is set
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            print("⚠️  Warning: OPENROUTER_API_KEY not set in environment variables")
            print("   AI features may not work properly.")
            print("   Please set your OpenRouter API key in a .env file or environment variable.")
        
        # Import the app
        from app import app
        
        print("🚀 Starting ThesisAI Server...")
        print("📖 API Documentation: http://localhost:8000/docs")
        print("🌐 Web Interface: http://localhost:8000")
        print("🔧 Press Ctrl+C to stop the server")
        
        # Start the server
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000, 
            reload=True,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("Please check the error message above and fix any issues.")
        sys.exit(1)

if __name__ == "__main__":
    main() 