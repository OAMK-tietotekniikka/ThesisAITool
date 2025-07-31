# Streaming Debug Guide

## Issue Description
The client is receiving structured JSON data but displaying raw JSON objects instead of extracting the content.

## Debugging Steps

### 1. Test the Basic Streaming
Visit: `http://localhost:8000/test-streaming-page`

This will show a simple test page that demonstrates the streaming format.

### 2. Check Browser Console
Open the browser developer tools (F12) and look at the Console tab for:
- JSON parsing errors
- Data type logs
- Content extraction logs

### 3. Test the Enhanced Client
Visit: `http://localhost:8000/streaming_client_example.html`

Click the "🧪 Test Streaming" button to test the basic streaming format.

### 4. Check Server Logs
Look at the server console for:
- Connection attempts
- Data flow logs
- Error messages

## Expected Behavior

### Server Response Format
```json
{"type": "content", "content": "This is the actual text content"}
{"type": "progress", "content": "Step 1/3", "step": 1, "total": 3}
{"type": "status", "content": "Connected to OpenAI..."}
{"type": "complete"}
```

### Client Display
The client should display:
- "This is the actual text content" (not the JSON)
- Progress indicators
- Status messages
- Completion message

## Common Issues

### 1. JSON Parsing Errors
**Symptoms**: Raw JSON displayed instead of content
**Solution**: Check browser console for parsing errors

### 2. Content Not Extracted
**Symptoms**: JSON objects shown as text
**Solution**: Verify the client is calling `data.content` correctly

### 3. Network Issues
**Symptoms**: Connection errors or timeouts
**Solution**: Check server logs and network connectivity

## Debug Commands

### Server Side
```bash
# Start server with debug logging
python app.py

# Check logs for:
# - Connection attempts
# - Data flow
# - Error conditions
```

### Client Side
```javascript
// Add to browser console to debug
console.log('Received data:', data);
console.log('Content extracted:', data.content);
```

## Test Endpoints

1. **Basic Test**: `/test-streaming`
   - Simple streaming test
   - No authentication required
   - Structured data format

2. **Enhanced Test**: `/request-ai-feedback-enhanced`
   - Full AI analysis
   - Requires authentication
   - Complex data flow

3. **Test Page**: `/test-streaming-page`
   - Simple HTML test client
   - No authentication required

## Troubleshooting Checklist

- [ ] Server is running (`python app.py`)
- [ ] Browser console shows no errors
- [ ] Network tab shows successful requests
- [ ] JSON parsing works correctly
- [ ] Content extraction works
- [ ] Display formatting is correct

## Quick Fix

If the issue persists, try this simplified client:

```javascript
async function simpleTest() {
    const response = await fetch('/test-streaming');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.slice(6));
                    if (data.type === 'content') {
                        console.log('Content:', data.content);
                        // Display the content here
                    }
                } catch (e) {
                    console.error('Parse error:', e);
                }
            }
        }
    }
}
```

## Expected Output

When working correctly, you should see:
1. Status messages in blue
2. Progress indicators
3. Actual text content (not JSON)
4. Completion message in green

If you see raw JSON objects, the issue is in the client-side parsing or display logic. 