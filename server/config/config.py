import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class to handle all environment variables and settings"""
    
    def __init__(self):
        # JWT Configuration
        self.SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-here')
        self.ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
        
        # AI Provider API Keys
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
        self.OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
        
        # Active AI Provider (default to openrouter if not specified)
        self.ACTIVE_AI_PROVIDER = os.getenv('ACTIVE_AI_PROVIDER', 'openrouter')
        
        # AI Provider Default Models
        self.OPENAI_DEFAULT_MODEL = os.getenv('OPENAI_DEFAULT_MODEL', 'gpt-4o')
        self.DEEPSEEK_DEFAULT_MODEL = os.getenv('DEEPSEEK_DEFAULT_MODEL', 'deepseek-chat')
        self.OPENROUTER_DEFAULT_MODEL = os.getenv('OPENROUTER_DEFAULT_MODEL', 'deepseek/deepseek-r1:free')
        
        # Server Configuration
        self.HOST = os.getenv('HOST', '0.0.0.0')
        self.PORT = int(os.getenv('PORT', '8000'))
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # File Storage Configuration
        self.UPLOAD_DIR = os.getenv('UPLOAD_DIR', 'thesis_uploads')
        self.FEEDBACK_DIR = os.getenv('FEEDBACK_DIR', 'feedback_files')
        self.AI_RESPONSES_DIR = os.getenv('AI_RESPONSES_DIR', 'ai_responses')
        
        # AI Configuration
        self.AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', '18000'))
        self.AI_SEED = int(os.getenv('AI_SEED', '1'))
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [self.UPLOAD_DIR, self.FEEDBACK_DIR, self.AI_RESPONSES_DIR]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def get_ai_provider_config(self) -> dict:
        """Get AI provider configuration"""
        return {
            'openai': {
                'api_key': self.OPENAI_API_KEY,
                'default_model': self.OPENAI_DEFAULT_MODEL,
                'api_url': 'https://api.openai.com/v1/chat/completions'
            },
            'deepseek': {
                'api_key': self.DEEPSEEK_API_KEY,
                'default_model': self.DEEPSEEK_DEFAULT_MODEL,
                'api_url': 'https://api.deepseek.com/v1/chat/completions'
            },
            'openrouter': {
                'api_key': self.OPENROUTER_API_KEY,
                'default_model': self.OPENROUTER_DEFAULT_MODEL,
                'api_url': 'https://openrouter.ai/api/v1/chat/completions'
            }
        }
    
    def get_active_provider(self) -> str:
        """Get the active AI provider"""
        return self.ACTIVE_AI_PROVIDER
    
    def get_available_providers(self) -> list:
        """Get list of available AI providers with their status"""
        providers = []
        config = self.get_ai_provider_config()
        
        for provider_name, provider_config in config.items():
            providers.append({
                'provider': provider_name,
                'name': provider_name.upper(),
                'has_api_key': provider_config['api_key'] is not None,
                'default_model': provider_config['default_model'],
                'api_url': provider_config['api_url'],
                'is_active': provider_name == self.ACTIVE_AI_PROVIDER
            })
        
        return providers
    
    def validate_jwt_config(self) -> bool:
        """Validate JWT configuration"""
        if self.SECRET_KEY == 'your-secret-key-here':
            print("⚠️  WARNING: Using default JWT secret key. Set JWT_SECRET_KEY in .env for production.")
            return False
        return True
    
    def validate_ai_config(self) -> dict:
        """Validate AI configuration and return status"""
        config = self.get_ai_provider_config()
        status = {
            'openai': config['openai']['api_key'] is not None,
            'deepseek': config['deepseek']['api_key'] is not None,
            'openrouter': config['openrouter']['api_key'] is not None
        }
        
        available_providers = [k for k, v in status.items() if v]
        if not available_providers:
            print("⚠️  WARNING: No AI provider API keys configured. Using fallback mode.")
        
        # Check if active provider has API key
        active_provider = self.ACTIVE_AI_PROVIDER
        if active_provider in status and not status[active_provider]:
            print(f"⚠️  WARNING: Active provider '{active_provider}' has no API key configured.")
        
        return status

# Global config instance
config = Config() 