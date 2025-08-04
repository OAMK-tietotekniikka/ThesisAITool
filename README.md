# ThesisAI Tool

A FastAPI-based server for thesis analysis and feedback with AI integration and Graphical User Interface client.

## ⚙️ Installation

1. Clone the repository and install dependencies:
```bash
git clone <repository-url>
cd ThesisAITool/server
pip install -r requirements.txt
```

2. Set up environment variables:

Navigate to the `server` directory (if you were not) and configure the environment settings:

- Copy the `env_example.txt` file to `.env`
- Edit the `.env` file with your API credentials and other preferred settings

This tool has been tested with the three major AI providers listed below. However, it should work with any AI providers that implement the OpenAI-compatible API
- **OpenAI**
- **DeepSeek**
- **OpenRouter**

You only need to configure one provider. The essential configuration parameters are:

```env
ACTIVE_AI_PROVIDER=your_preferred_provider
your_preferred_provider_API_KEY=your_api_key_here
```

Replace `your_preferred_provider` with one of the supported provider names (openai, deepseek, or openrouter) and substitute `your_api_key_here` with your actual API key.

## ▶️ Running the Server

Assumed that you are in the root project directory.

### Option 1: Using the startup script (recommended)
```bash
python run_server.py
```

### Option 2: Direct execution
```bash
cd server
python main.py
```

### Option 3: Using uvicorn directly
```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🖥️ Start Using the Tool with GUI

Simply navigate to the `client` directory and open `index.html` in your web browser, or deploy the entire `client` directory to your preferred hosting environment to access the graphical user interface. Remember to change `API_BASE_URL` in `main.js` to your own URL if you do so.


## 🧪 Testing

### **Server Testing**

```bash
cd server
python test_server.py
```

### **Unit Testing**
```bash
# Test individual modules
python -m pytest tests/unit/

# Test specific module
python -m pytest tests/unit/test_auth.py
```

### **Integration Testing**
```bash
# Test API endpoints
python -m pytest tests/integration/

# Test database operations
python -m pytest tests/integration/test_database.py
```

## 📚 API Documentation

The API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📋 Key Features

### **Authentication System**
- JWT-based authentication
- Role-based access control (Student, Supervisor, Admin)
- Secure password hashing with bcrypt

### **Thesis Management**
- Upload and store thesis documents
- Support for PDF, DOCX, and TXT formats
- Document preview and text extraction
- Version control and status tracking

### **AI Analysis**
- Multi-provider AI support (OpenAI, DeepSeek, OpenRouter)
- Streaming AI responses for real-time feedback
- Comprehensive thesis evaluation with grading
- Customizable analysis parameters

### **User Management**
- User registration and authentication
- Supervisor-student assignment system
- Role-based permissions and access control

## 👤 Default Users

The server comes with pre-configured test users.:

- **Admin**: username: `admin`, password: `1234`
- **Supervisor**: username: `gv`, password: `1234`
- **Student**: username: `sv`, password: `1234`

Delete `thesis_ai.db` for a clean database.

## 📁 Project Structure

```
ThesisAITool/
├── client/                          # Frontend client files
│   ├── css/                         # CSS stylesheets
│   ├── js/                          # JavaScript files
│   ├── components/                  # Reusable UI components
│   ├── pages/                       # Page-specific components
│   ├── utils/                       # Client-side utilities
│   ├── index.html                   # Main HTML file
│   ├── register.html                # Registration page
│   ├── style.css                    # Main stylesheet
│   ├── main.js                      # Main JavaScript file
│   └── favicon.ico                  # Favicon
│
├── server/                          # Backend server code
│   ├── main.py                      # Main application entry point
│   ├── app.py                       # Legacy app file (to be removed)
│   │
│   ├── core/                        # Core application modules
│   │   ├── models/                  # Data models
│   │   │   ├── __init__.py
│   │   │   ├── user.py             # User model
│   │   │   ├── thesis.py           # Thesis model
│   │   │   ├── feedback.py         # Feedback model
│   │   │   └── ai_request.py       # AI request model
│   │   ├── services/               # Business logic services
│   │   ├── repositories/           # Data access layer
│   │   └── utils/                  # Core utilities
│   │
│   ├── config/                     # Configuration management
│   │   ├── __init__.py
│   │   └── config.py               # Configuration settings
│   │
│   ├── database/                   # Database layer
│   │   ├── __init__.py
│   │   └── database.py             # Database models and repositories
│   │
│   ├── auth/                       # Authentication module
│   │   ├── __init__.py
│   │   └── auth_service.py         # Authentication services
│   │
│   ├── file_processing/            # File processing utilities
│   │   ├── __init__.py
│   │   ├── text_extractor.py       # Text extraction from files
│   │   └── image_converter.py      # Document to image conversion
│   │
│   ├── ai/                         # AI services and providers
│   │   ├── __init__.py
│   │   ├── providers/              # AI provider implementations
│   │   │   ├── __init__.py
│   │   │   └── ai_provider.py      # AI provider enum
│   │   ├── services/               # AI service implementations
│   │   │   ├── __init__.py
│   │   │   └── unified_ai_model.py # Unified AI model service
│   │   └── models/                 # AI-specific models
│   │
│   ├── api/                        # API layer
│   │   ├── __init__.py
│   │   ├── routes/                 # API route definitions
│   │   │   ├── __init__.py
│   │   │   ├── auth_routes.py      # Authentication routes
│   │   │   ├── thesis_routes.py    # Thesis management routes
│   │   │   ├── ai_routes.py        # AI analysis routes
│   │   │   └── user_routes.py      # User management routes
│   │   └── middleware/             # API middleware
│   │
│   ├── static/                     # Static files
│   ├── templates/                  # HTML templates
│   │
│   ├── thesis_uploads/             # Uploaded thesis files
│   ├── feedback_files/             # Feedback files
│   ├── ai_responses/               # AI response files
│   └── references/                 # Reference materials
│
├── requirements.txt                 # Python dependencies
├── requirements_new.txt             # Updated dependencies
├── run_server.py                   # Server runner script
└── README.md                       # Original README
```

## ❓ Troubleshooting

1. **Import errors**: Make sure all dependencies are installed
2. **API key errors**: Set the API key environment variable
3. **File permission errors**: Ensure the server has write permissions to the directories
4. **Port already in use**: Change the port in the startup script or kill the existing process 

## 📄 License

You can use this project freely. Attribution is appreciated but not required.
