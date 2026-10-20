from abc import ABC, abstractmethod
from typing import Dict, Any, List
import requests
import json
from config import LLMConfig

class LLMProvider(ABC):
    """Abstract base class for LLM providers following SOLID principles"""
    
    @abstractmethod
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text and return structured outline and questions"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (has API key)"""
        pass

class GeminiProvider(LLMProvider):
    """Gemini API implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            return self._get_mock_response()
        
        try:
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json={
                    "contents": [{
                        "parts": [{"text": text}]
                    }]
                },
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("candidates", [{}])[0].get("content", {})
                parts = content.get("parts", [{}])
                text_response = parts[0].get("text", "")
                return self._parse_json_response(text_response)
            else:
                print(f"Gemini API error: {response.status_code} - {response.text}")
                return self._get_mock_response()
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return self._get_mock_response()
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = text[start:end]
                return json.loads(json_str)
        except:
            pass
        return self._get_mock_response()
    
    def _get_mock_response(self) -> Dict[str, Any]:
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
                        },
                        {
                            "title": "1.2 Cơ sở lý thuyết",
                            "units": [
                                {"title": "1.2.1 Nguyên lý cơ bản"},
                                {"title": "1.2.2 Ứng dụng thực tế"}
                            ]
                        }
                    ]
                },
                {
                    "title": "Chương 2: Nội dung chính",
                    "subsections": [
                        {
                            "title": "2.1 Phương pháp luận",
                            "units": [
                                {"title": "2.1.1 Các bước thực hiện"},
                                {"title": "2.1.2 Công cụ và kỹ thuật"}
                            ]
                        }
                    ]
                }
            ],
            "questions": [
                {
                    "question": "Đâu là đặc điểm chính của phương pháp này?",
                    "choices": ["Tính đơn giản", "Tính phức tạp", "Tính linh hoạt", "Tính cứng nhắc"],
                    "answer": [2],
                    "type": "multiple_choice"
                },
                {
                    "question": "2 + 2 = ?",
                    "choices": ["3", "4", "5", "6"],
                    "answer": [1],
                    "type": "multiple_choice"
                }
            ]
        }

class OpenAIProvider(LLMProvider):
    """OpenAI GPT implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            return self._get_mock_response()
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Bạn là một chuyên gia phân tích tài liệu giáo dục. Hãy trả về đúng JSON format như yêu cầu."
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    "temperature": 0.7
                },
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return self._parse_json_response(content)
            else:
                print(f"OpenAI API error: {response.status_code} - {response.text}")
                return self._get_mock_response()
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return self._get_mock_response()
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = text[start:end]
                return json.loads(json_str)
        except:
            pass
        return self._get_mock_response()
    
    def _get_mock_response(self) -> Dict[str, Any]:
        return {
            "outline": [
                {
                    "title": "Chương 1: Giới thiệu",
                    "subsections": [
                        {
                            "title": "1.1 Tổng quan",
                            "units": [
                                {"title": "1.1.1 Định nghĩa và khái niệm"}
                            ]
                        }
                    ]
                }
            ],
            "questions": [
                {
                    "question": "GPT là viết tắt của gì?",
                    "choices": ["General Purpose Technology", "Generative Pre-trained Transformer", "Global Processing Tool", "General Processing Technology"],
                    "answer": [1],
                    "type": "multiple_choice"
                }
            ]
        }

class DeepSeekProvider(LLMProvider):
    """DeepSeek API implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            return self._get_mock_response()
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Bạn là một chuyên gia phân tích tài liệu giáo dục. Hãy trả về đúng JSON format như yêu cầu."
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    "temperature": 0.7
                },
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return self._parse_json_response(content)
            else:
                print(f"DeepSeek API error: {response.status_code} - {response.text}")
                return self._get_mock_response()
        except Exception as e:
            print(f"Error calling DeepSeek API: {e}")
            return self._get_mock_response()
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = text[start:end]
                return json.loads(json_str)
        except:
            pass
        return self._get_mock_response()
    
    def _get_mock_response(self) -> Dict[str, Any]:
        return {
            "outline": [
                {
                    "title": "Chương 1: Giới thiệu",
                    "subsections": [
                        {
                            "title": "1.1 Tổng quan",
                            "units": [
                                {"title": "1.1.1 Định nghĩa và khái niệm"}
                            ]
                        }
                    ]
                }
            ],
            "questions": [
                {
                    "question": "DeepSeek là gì?",
                    "choices": ["Một công ty AI", "Một mô hình ngôn ngữ", "Một nền tảng học tập", "Tất cả đều đúng"],
                    "answer": [3],
                    "type": "multiple_choice"
                }
            ]
        } 