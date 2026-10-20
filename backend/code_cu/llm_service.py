from typing import Dict, Any, Optional
from llm_providers import LLMProvider, GeminiProvider, OpenAIProvider, DeepSeekProvider
from config import config

class LLMService:
    """Service class for managing LLM providers following SOLID principles"""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available LLM providers"""
        llm_config = config.llm
        
        # Initialize Gemini provider
        if llm_config.gemini_api_key:
            self.providers['gemini'] = GeminiProvider(llm_config.gemini_api_key)
        
        # Initialize OpenAI provider
        if llm_config.openai_api_key:
            self.providers['openai'] = OpenAIProvider(llm_config.openai_api_key)
        
        # Initialize DeepSeek provider
        if llm_config.deepseek_api_key:
            self.providers['deepseek'] = DeepSeekProvider(llm_config.deepseek_api_key)
    
    def get_available_providers(self) -> Dict[str, bool]:
        """Get list of available providers"""
        return {
            'gemini': 'gemini' in self.providers and self.providers['gemini'].is_available(),
            'openai': 'openai' in self.providers and self.providers['openai'].is_available(),
            'deepseek': 'deepseek' in self.providers and self.providers['deepseek'].is_available()
        }
    
    def get_default_provider(self) -> Optional[str]:
        """Get the default provider name"""
        default = config.llm.default_provider
        if default in self.providers and self.providers[default].is_available():
            return default
        
        # Fallback to first available provider
        for name, provider in self.providers.items():
            if provider.is_available():
                return name
        
        return None
    
    def analyze_text(self, text: str, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze text using specified provider or default provider
        
        Args:
            text: Text to analyze
            provider_name: Name of provider to use (gemini, openai, deepseek)
        
        Returns:
            Dict containing outline and questions
        """
        # Determine which provider to use
        if provider_name and provider_name in self.providers:
            provider = self.providers[provider_name]
        else:
            default_provider = self.get_default_provider()
            if not default_provider:
                # Return mock data if no providers available
                return self._get_mock_response()
            provider = self.providers[default_provider]
        
        # Analyze text
        return provider.analyze_text(text)
    
    def _get_mock_response(self) -> Dict[str, Any]:
        """Fallback mock response when no providers are available"""
        return {
            "outline": [
                {
                    "title": "Chương 1: Giới thiệu",
                    "subsections": [
                        {
                            "title": "1.1 Tổng quan",
                            "units": [
                                {"title": "1.1.1 Định nghĩa và khái niệm"},
                                {"title": "1.1.2 Lịch sử phát triển"}
                            ]
                        }
                    ]
                }
            ],
            "questions": [
                {
                    "question": "Đây là câu hỏi mẫu?",
                    "choices": ["Lựa chọn A", "Lựa chọn B", "Lựa chọn C", "Lựa chọn D"],
                    "answer": [1],
                    "type": "multiple_choice"
                }
            ]
        }

# Global service instance
llm_service = LLMService() 