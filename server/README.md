# ThesisAI Server

A FastAPI-based server for thesis analysis and feedback with AI integration.

## Recent Fixes

The following issues have been fixed in the server:

1. **String concatenation errors**: Fixed `ai_feedback += '' * 80` to use proper string formatting
2. **Async method calls**: Made `fetch_reference_text_from_url` and `check_ref_validity` async and properly await async calls
3. **Method call error**: Fixed `grade_objective` being called instead of `grade_theoretical_foundation`
4. **File encoding issues**: Improved text file reading to handle different encodings
5. **Missing file handling**: Added error handling for missing JSON files and HTML files
6. **Dependencies**: Created comprehensive requirements.txt with all necessary packages

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
Navigate to the `server` directory and configure the environment settings:

- Copy the `env_example.txt` file to `.env`
- Edit the `.env` file with your API credentials and other preferred settings

This tool supports three major AI providers:
- **OpenAI**
- **DeepSeek**
- **OpenRouter**

You only need to configure one provider. The essential configuration parameters are:

```env
ACTIVE_AI_PROVIDER=your_preferred_provider
your_preferred_provider_API_KEY=your_api_key_here
```

Replace `your_preferred_provider` with one of the supported provider names (openai, deepseek, or openrouter) and substitute `your_api_key_here` with your actual API key.

## Running the Server

### Option 1: Using the startup script (recommended)
```bash
python start_server.py
```

### Option 2: Direct execution
```bash
python app.py
```

### Option 3: Using uvicorn directly
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Start Using the Tool with GUI

The client interface is available through the `index.html` file located in the `client` directory. This directory contains all static files required for the web interface and can be hosted on any web server or static hosting platform of your choice.

Simply navigate to the `client` directory and open `index.html` in your web browser, or deploy the entire `client` directory to your preferred hosting environment to access the graphical user interface.


## Testing

Run the test script to verify everything is working:
```bash
python test_server.py
```

## API Endpoints

- **API Documentation**: http://localhost:8000/docs
- **Web Interface**: http://localhost:8000
- **Health Check**: http://localhost:8000/me (requires authentication)

## Features

- User authentication with JWT tokens
- File upload and processing (PDF, DOCX, TXT)
- AI-powered thesis analysis and grading
- Supervisor feedback system
- Role-based access control (student, supervisor, admin)

## Default Users

The server comes with pre-configured test users:

- **Admin**: username: `admin`, password: `1234`
- **Supervisor**: username: `gv`, password: `1234`
- **Student**: username: `sv`, password: `1234`

## File Structure

```
server/
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── start_server.py       # Startup script with error handling
├── test_server.py        # Test script
├── README.md            # This file
├── thesis_uploads/      # Uploaded thesis files
├── feedback_files/      # Supervisor feedback files
└── ai_responses/        # AI analysis responses
```

## Troubleshooting

1. **Import errors**: Make sure all dependencies are installed
2. **API key errors**: Set the OPENROUTER_API_KEY environment variable
3. **File permission errors**: Ensure the server has write permissions to the directories
4. **Port already in use**: Change the port in the startup script or kill the existing process 