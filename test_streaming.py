#!/usr/bin/env python3
"""
Test script to verify streaming functionality
"""

import asyncio
import aiohttp
import json

async def test_streaming():
    """Test the streaming endpoint"""
    async with aiohttp.ClientSession() as session:
        # Test data
        data = {
            'custom_instructions': 'Please review this thesis and provide feedback',
            'predefined_questions[0]': 'What are the strengths?',
            'predefined_questions[1]': 'What areas need improvement?'
        }
        
        # Convert to form data
        form_data = aiohttp.FormData()
        for key, value in data.items():
            form_data.add_field(key, value)
        
        # Make request to streaming endpoint
        url = "http://localhost:8000/request-ai-feedback?thesis_id=test123"
        
        try:
            async with session.post(url, data=form_data) as response:
                print(f"Status: {response.status}")
                print(f"Headers: {response.headers}")
                
                if response.status == 200:
                    print("Streaming response received:")
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            content = line_str[6:]  # Remove 'data: ' prefix
                            print(f"Received: {content}")
                else:
                    print(f"Error: {response.status}")
                    text = await response.text()
                    print(f"Response: {text}")
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_streaming()) 