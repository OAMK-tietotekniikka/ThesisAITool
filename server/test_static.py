#!/usr/bin/env python3
"""
Simple test script to verify static files mounting
"""
import os
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Create a simple test app
app = FastAPI()

# Test the static files mount
client_path = "../client"
print(f"Testing static files mount:")
print(f"Client path: {client_path}")
print(f"Client exists: {os.path.exists(client_path)}")
print(f"Current directory: {os.getcwd()}")

# List contents of client directory
if os.path.exists(client_path):
    print(f"Client directory contents:")
    for item in os.listdir(client_path):
        print(f"  - {item}")

# Mount static files
app.mount("/web", StaticFiles(directory=client_path), name="web")

# Add a test route
@app.get("/")
async def root():
    return HTMLResponse(content="<h1>Static files test server</h1><p>Visit <a href='/web/'>/web/</a> to test static files</p>")

if __name__ == "__main__":
    import uvicorn
    print("Starting test server on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001) 