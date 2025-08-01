# ThesisAI Tool - Refactored Codebase

This document describes the refactored structure of the ThesisAI Tool codebase, which has been reorganized into a more modular and maintainable architecture.

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

## 🏗️ Architecture Overview

### 1. **Core Layer** (`server/core/`)
Contains the fundamental building blocks of the application:
- **Models**: Data structures and Pydantic models
- **Services**: Business logic and domain services
- **Repositories**: Data access patterns
- **Utils**: Shared utilities and helpers

### 2. **Configuration Layer** (`server/config/`)
Centralized configuration management:
- Environment variable handling
- AI provider configuration
- Database settings
- Server configuration

### 3. **Database Layer** (`server/database/`)
Database management and data access:
- SQLite database setup
- Repository pattern implementation
- User, Thesis, and Feedback repositories

### 4. **Authentication Layer** (`server/auth/`)
Security and authentication:
- JWT token management
- Password hashing
- User authentication
- Role-based access control

### 5. **File Processing Layer** (`server/file_processing/`)
Document and file handling:
- Text extraction from various formats (PDF, DOCX, TXT)
- Document to image conversion
- File preview generation

### 6. **AI Layer** (`server/ai/`)
Artificial Intelligence services:
- **Providers**: Different AI service providers (OpenAI, DeepSeek, OpenRouter)
- **Services**: Unified AI model interface
- **Models**: AI-specific data structures

### 7. **API Layer** (`server/api/`)
REST API implementation:
- **Routes**: Organized by domain (auth, thesis, ai, users)
- **Middleware**: Request/response processing
- **Validation**: Input validation and error handling

## 🔄 Migration Benefits

### **Before Refactoring:**
- Single monolithic `app.py` file (2,283 lines)
- Mixed concerns (models, routes, business logic, AI services)
- Difficult to maintain and test
- Hard to extend with new features
- No clear separation of responsibilities

### **After Refactoring:**
- **Modular Structure**: Clear separation of concerns
- **Maintainability**: Each module has a single responsibility
- **Testability**: Individual components can be tested in isolation
- **Scalability**: Easy to add new features and providers
- **Reusability**: Components can be reused across the application

## 🚀 Getting Started

### 1. **Installation**
```bash
# Clone the repository
git clone <repository-url>
cd ThesisAITool

# Install dependencies
pip install -r requirements.txt
```

### 2. **Configuration**
Create a `.env` file in the root directory:
```env
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Provider API Keys
OPENAI_API_KEY=your-openai-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
OPENROUTER_API_KEY=your-openrouter-api-key

# Active AI Provider
ACTIVE_AI_PROVIDER=openrouter

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False
```

### 3. **Running the Application**
```bash
# Run the main application
python server/main.py

# Or use the legacy app (during transition)
python server/app.py
```

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

## 🔧 Development Guidelines

### **Adding New Features**
1. **Models**: Add to `server/core/models/`
2. **Services**: Add to `server/core/services/`
3. **Routes**: Add to `server/api/routes/`
4. **Configuration**: Update `server/config/config.py`

### **Adding New AI Providers**
1. Add provider enum to `server/ai/providers/ai_provider.py`
2. Update configuration in `server/config/config.py`
3. Implement provider-specific logic in `server/ai/services/`

### **Database Changes**
1. Update models in `server/core/models/`
2. Update repositories in `server/database/database.py`
3. Run database migrations if needed

## 🧪 Testing

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

## 🔄 Migration Notes

### **Legacy Support**
- The original `app.py` is still available for backward compatibility
- New features should use the refactored structure
- Gradual migration of existing endpoints to new structure

### **Breaking Changes**
- Import paths have changed for refactored modules
- Some function signatures may have been updated
- Database schema remains the same

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Follow** the new modular structure
4. **Add** tests for new functionality
5. **Submit** a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the API documentation
- Review the configuration guide

---

**Note**: This refactored structure provides a solid foundation for future development while maintaining backward compatibility with existing functionality. 