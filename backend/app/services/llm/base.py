"""
Base LLM service and interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from app.core.logging import get_logger
from app.core.exceptions import LLMServiceError
from app.config.settings import get_llm_settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers following SOLID principles"""
    
    def __init__(self, api_key: str, provider_name: str):
        self.api_key = api_key
        self.provider_name = provider_name
        self.logger = get_logger(f"llm.{provider_name}")
    
    @abstractmethod
    def analyze_text(self, text: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Analyze text and return structured response"""
        pass
    
    def analyze_text_raw(self, text: str, prompt: Optional[str] = None) -> Any:
        """Analyze text and return raw response without validation"""
        # Default implementation calls analyze_text, but subclasses can override
        return self.analyze_text(text, prompt)
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (has API key)"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        pass
    
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate LLM response structure"""
        required_keys = ["outline", "questions"]
        return all(key in response for key in required_keys)
    
    def get_mock_response(self) -> Dict[str, Any]:
        """Get mock response when provider is unavailable"""
        return {
            "outline": [
                {
                    "title": "Chương 1: Giới thiệu",
                    "subsections": [
                        {
                            "title": "1.1 Tổng quan",
                            "units": [
                                {"title": "1.1.1 Định nghĩa và khái niệm", "type": "pdf"},
                                {"title": "1.1.2 Video giới thiệu", "type": "video"}
                            ]
                        }
                    ]
                }
            ],
            "questions": []
        }


class LLMService:
    """Service class for managing LLM providers following SOLID principles"""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.logger = get_logger("llm.service")
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize available LLM providers"""
        # Clear existing providers
        self.providers.clear()
        
        # Get fresh settings
        settings = get_llm_settings()
        
        # Import providers here to avoid circular imports
        from .providers.gemini import GeminiProvider
        from .providers.openai import OpenAIProvider
        from .providers.deepseek import DeepSeekProvider
        
        # Initialize Gemini provider
        if settings.gemini_api_key:
            try:
                self.providers['gemini'] = GeminiProvider(settings.gemini_api_key)
                self.logger.info("Gemini provider initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Gemini provider: {e}")
        
        # Initialize OpenAI provider
        if settings.openai_api_key:
            try:
                self.providers['openai'] = OpenAIProvider(settings.openai_api_key)
                self.logger.info("OpenAI provider initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI provider: {e}")
        
        # Initialize DeepSeek provider
        if settings.deepseek_api_key:
            try:
                self.providers['deepseek'] = DeepSeekProvider(settings.deepseek_api_key)
                self.logger.info("DeepSeek provider initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize DeepSeek provider: {e}")
        
        self.logger.info(f"Initialized {len(self.providers)} LLM providers")
    
    def reload_settings(self) -> None:
        """Reload settings and reinitialize providers"""
        from app.config.settings import clear_settings_cache
        self.logger.info("Reloading LLM settings and reinitializing providers")
        clear_settings_cache()
        
        # Debug: Check settings before reload
        old_settings = get_llm_settings()
        self.logger.info(f"Old settings - default_provider: {old_settings.default_provider}")
        
        self._initialize_providers()
        
        # Debug: Check settings after reload
        new_settings = get_llm_settings()
        self.logger.info(f"New settings - default_provider: {new_settings.default_provider}")
    
    def get_available_providers(self) -> Dict[str, bool]:
        """Get list of available providers"""
        return {
            name: provider.is_available() 
            for name, provider in self.providers.items()
        }
    
    def get_default_provider(self) -> Optional[str]:
        """Get the default provider name"""
        settings = get_llm_settings()
        default = settings.default_provider
        
        # Debug logging
        self.logger.info(f"LLM Settings - default_provider: {default}")
        self.logger.info(f"LLM Settings - all fields: {settings.dict()}")
        
        if default in self.providers and self.providers[default].is_available():
            return default
        
        # Fallback to first available provider
        for name, provider in self.providers.items():
            if provider.is_available():
                return name
        
        return None
    
    def analyze_text(
        self, 
        text: str, 
        provider_name: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze text using specified provider or default provider
        
        Args:
            text: Text to analyze
            provider_name: Name of provider to use
            prompt: Custom prompt (optional)
        
        Returns:
            Dict containing outline and questions
        
        Raises:
            LLMServiceError: If no providers are available or analysis fails
        """
        # Determine which provider to use
        if provider_name and provider_name in self.providers:
            provider = self.providers[provider_name]
            self.logger.info(f"Using specified provider: {provider_name}")
        else:
            default_provider = self.get_default_provider()
            if not default_provider:
                self.logger.error("No LLM providers available")
                raise LLMServiceError("No LLM providers available")
            
            provider = self.providers[default_provider]
            self.logger.info(f"Using default provider: {default_provider}")
        
        # Analyze text
        try:
            self.logger.info(f"Starting text analysis with {provider.provider_name}")
            result = provider.analyze_text(text, prompt)
            
            # Validate response
            if not provider.validate_response(result):
                self.logger.warning("Invalid response structure, using mock response")
                result = provider.get_mock_response()
            
            self.logger.info("Text analysis completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Text analysis failed: {e}")
            raise LLMServiceError(f"Text analysis failed: {str(e)}", provider.provider_name)
    
    def analyze_questions(
        self, 
        text: str, 
        provider_name: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Any:
        """
        Analyze questions text using specified provider or default provider
        This method doesn't validate response structure like analyze_text does
        
        Args:
            text: Text to analyze
            provider_name: Name of provider to use
            prompt: Custom prompt (optional)
        
        Returns:
            Raw response from provider (could be dict, list, or string)
        
        Raises:
            LLMServiceError: If no providers are available or analysis fails
        """
        # Determine which provider to use
        if provider_name and provider_name in self.providers:
            provider = self.providers[provider_name]
            self.logger.info(f"Using specified provider: {provider_name}")
        else:
            default_provider = self.get_default_provider()
            if not default_provider:
                self.logger.error("No LLM providers available")
                raise LLMServiceError("No LLM providers available")
            
            provider = self.providers[default_provider]
            self.logger.info(f"Using default provider: {default_provider}")
        
        # Analyze text without validation
        try:
            self.logger.info(f"Starting question analysis with {provider.provider_name}")
            result = provider.analyze_text_raw(text, prompt)
            
            self.logger.info("Question analysis completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Question analysis failed: {e}")
            raise LLMServiceError(f"Question analysis failed: {str(e)}", provider.provider_name)
    
    def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific provider"""
        if provider_name in self.providers:
            provider = self.providers[provider_name]
            return {
                "name": provider.provider_name,
                "available": provider.is_available(),
                "model_info": provider.get_model_info()
            }
        return None
    
    def get_all_provider_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all providers"""
        return {
            name: self.get_provider_info(name)
            for name in self.providers.keys()
        }


# Global service instance
# llm_service = LLMService()  # Remove this line

def get_llm_service() -> LLMService:
    """Get a fresh LLM service instance"""
    return LLMService() 