#!/usr/bin/env python3
"""
Simple server startup script with static files
"""
import os
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Create the app
app = FastAPI()

# Get the absolute path to the client directory
current_dir = os.path.dirname(os.path.abspath(__file__))
client_dir = os.path.join(os.path.dirname(current_dir), "client")

print(f"Server directory: {current_dir}")
print(f"Client directory: {client_dir}")
print(f"Client exists: {os.path.exists(client_dir)}")

if os.path.exists(client_dir):
    print(f"Client directory contents:")
    for item in os.listdir(client_dir):
        print(f"  - {item}")
    
    # Mount static files
    app.mount("/web", StaticFiles(directory=client_dir), name="web")
    print("✅ Static files mounted at /web")
else:
    print("❌ Client directory not found!")

@app.get("/")
async def root():
    return HTMLResponse(content="""
    <h1>ThesisAI Server</h1>
    <p>Static files are mounted at <a href="/web/">/web/</a></p>
    <p>Try visiting:</p>
    <ul>
        <li><a href="/web/index.html">/web/index.html</a></li>
        <li><a href="/web/main.js">/web/main.js</a></li>
        <li><a href="/web/style.css">/web/style.css</a></li>
    </ul>
    """)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000) 