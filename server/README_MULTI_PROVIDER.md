# ThesisAI Multi-Provider AI System

This application now supports multiple AI providers: OpenAI, DeepSeek, and OpenRouter. You can easily switch between providers or use different models for different tasks.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements_new.txt
```

### 2. Environment Variables
Create a `.env` file in the server directory with your API keys:

```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# DeepSeek API Key  
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# OpenRouter API Key
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 3. Run the Application
```bash
python app_DS_new.py
```

## Available AI Providers

### OpenAI
- **Default Model**: `gpt-4o`
- **API Endpoint**: `https://api.openai.com/v1/chat/completions`
- **Features**: High-quality responses, good for complex analysis

### DeepSeek
- **Default Model**: `deepseek-chat`
- **API Endpoint**: `https://api.deepseek.com/v1/chat/completions`
- **Features**: Cost-effective, good performance

### OpenRouter
- **Default Model**: `google/gemini-2.5-pro-exp-03-25:free`
- **API Endpoint**: `https://openrouter.ai/api/v1/chat/completions`
- **Features**: Access to multiple models, flexible pricing

## API Usage

### Request AI Feedback
```bash
curl -X POST "http://localhost:8000/request-ai-feedback" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "thesis_id=your_thesis_id" \
  -F "custom_instructions=Please review this thesis" \
  -F "predefined_questions[]=What are the strengths?" \
  -F "predefined_questions[]=What areas need improvement?" \
  -F "provider=openai" \
  -F "model=gpt-4o"
```

### Available Parameters
- `thesis_id`: ID of the thesis to analyze
- `custom_instructions`: Custom instructions for the AI
- `predefined_questions`: List of questions to answer
- `provider`: AI provider (`openai`, `deepseek`, `openrouter`)
- `model`: Specific model to use (optional, uses default if not specified)

### Get Available Providers
```bash
curl -X GET "http://localhost:8000/ai-providers" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Provider-Specific Models

### OpenAI Models
- `gpt-4o` (default)
- `gpt-4o-mini`
- `gpt-4-turbo`
- `gpt-3.5-turbo`

### DeepSeek Models
- `deepseek-chat` (default)
- `deepseek-coder`

### OpenRouter Models
- `google/gemini-2.5-pro-exp-03-25:free` (default)
- `deepseek/deepseek-chat-v3-0324:free`
- `anthropic/claude-3.5-sonnet:free`
- `meta-llama/llama-3.1-8b-instruct:free`

## Features

### 1. Unified Interface
All AI providers use the same interface, making it easy to switch between them.

### 2. Streaming Support
All providers support streaming responses for real-time feedback.

### 3. Fallback Mode
If no API key is configured for a provider, the system will use a fallback mode with simulated responses.

### 4. Multiple Analysis Types
- **Thesis Analysis**: General thesis review
- **Objective Grading**: Grade research objectives (1-5 scale)
- **Theoretical Foundation Grading**: Grade theoretical framework (1-5 scale)

### 5. Error Handling
Comprehensive error handling for API failures, timeouts, and invalid responses.

## Example Usage in Frontend

```javascript
// Request AI feedback with OpenAI
const response = await fetch('/request-ai-feedback', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: new FormData({
    thesis_id: 'thesis_123',
    custom_instructions: 'Please provide detailed feedback',
    predefined_questions: ['What are the strengths?', 'What needs improvement?'],
    provider: 'openai',
    model: 'gpt-4o'
  })
});

// Handle streaming response
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      console.log('AI Response:', data);
    }
  }
}
```

## Configuration

### Custom Models
You can specify custom models for each provider:

```python
# In the AIConfig class
self.default_models = {
    AIProvider.OPENAI: "gpt-4o",
    AIProvider.DEEPSEEK: "deepseek-chat", 
    AIProvider.OPENROUTER: "google/gemini-2.5-pro-exp-03-25:free"
}
```

### API Endpoints
```python
self.api_endpoints = {
    AIProvider.OPENAI: "https://api.openai.com/v1/chat/completions",
    AIProvider.DEEPSEEK: "https://api.deepseek.com/v1/chat/completions", 
    AIProvider.OPENROUTER: "https://openrouter.ai/api/v1/chat/completions"
}
```

## Troubleshooting

### No API Key Error
If you get an error about missing API keys, make sure your `.env` file is properly configured.

### Provider Not Working
Check that:
1. The API key is valid
2. The model name is correct for the provider
3. The API endpoint is accessible

### Streaming Issues
If streaming doesn't work:
1. Check network connectivity
2. Verify the provider supports streaming
3. Check browser compatibility for Server-Sent Events

## Migration from Old Version

The new version is backward compatible. The main changes are:

1. **New AI Provider System**: Unified interface for multiple providers
2. **Enhanced Configuration**: Environment-based API key management
3. **Better Error Handling**: More robust error handling and fallback modes
4. **Streaming Improvements**: Better streaming support across all providers

To migrate:
1. Update your `.env` file with the new API keys
2. Update your frontend to use the new `provider` parameter
3. Test with different providers to find the best fit for your needs 