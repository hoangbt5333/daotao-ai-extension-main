"""
Gemini LLM provider implementation
"""
import json
import requests
from typing import Dict, Any, Optional
from ..base import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini API implementation"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "gemini")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        self.model_name = "gemini-pro"
    
    def is_available(self) -> bool:
        """Check if the provider is available (has API key)"""
        return bool(self.api_key and self.api_key.strip())
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        return {
            "name": self.model_name,
            "provider": "Google",
            "max_tokens": 8192,
            "supports_streaming": True
        }
    
    def analyze_text(self, text: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Analyze text and return structured outline and questions"""
        if not self.is_available():
            self.logger.warning("Gemini provider not available, returning mock response")
            return self.get_mock_response()
        
        # Use default prompt if none provided
        if not prompt:
            final_prompt = self._get_default_prompt().format(text=text)
        else:
            # If custom prompt is provided, use it directly (it already contains the text)
            final_prompt = prompt
        
        try:
            self.logger.info("Sending request to Gemini API")
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json={
                    "contents": [{
                        "parts": [{"text": final_prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 16384,
                    }
                },
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("candidates", [{}])[0].get("content", {})
                parts = content.get("parts", [{}])
                text_response = parts[0].get("text", "")
                
                self.logger.info("Successfully received response from Gemini API")
                return self._parse_json_response(text_response)
            else:
                self.logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return self.get_mock_response()
                
        except Exception as e:
            self.logger.error(f"Error calling Gemini API: {e}")
            return self.get_mock_response()
    
    def _get_default_prompt(self) -> str:
        """Get default prompt for text analysis"""
        return """
        Bạn là một chuyên gia phân tích tài liệu giáo dục. Hãy phân tích văn bản sau và tạo ra một outline khóa học có cấu trúc rõ ràng với các chương, bài học.

        YÊU CẦU:
        - Trả về đúng JSON format như yêu cầu
        - Outline phải có cấu trúc: chapters > subsections > units
        - Mỗi unit phải có type: "pdf", "video", "docx", "text", hoặc "video_pdf"
        - Unit type "pdf": cho tài liệu PDF
        - Unit type "video": cho video bài giảng
        - Unit type "docx": cho tài liệu Word
        - Unit type "text": cho nội dung text
        - Unit type "video_pdf": cho video kết hợp PDF
        - Không tạo câu hỏi, chỉ tập trung vào outline

        VĂN BẢN CẦN PHÂN TÍCH:
        {text}

        TRẢ VỀ JSON format như sau (KHÔNG giải thích gì thêm, chỉ trả về JSON):
        {{
            "outline": [
                {{
                    "title": "Tên chương",
                    "subsections": [
                        {{
                            "title": "Tên bài học",
                            "units": [
                                {{
                                    "title": "Tên unit",
                                    "type": "pdf"
                                }},
                                {{
                                    "title": "Tên unit",
                                    "type": "video"
                                }}
                            ]
                        }}
                    ]
                }}
            ],
            "questions": []
        }}
        """
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON response from LLM"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # Validate structure
                if self.validate_response(result):
                    return result
                else:
                    self.logger.warning("Invalid response structure from Gemini")
                    return self.get_mock_response()
            else:
                self.logger.warning("No JSON found in Gemini response")
                return self.get_mock_response()
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from Gemini response: {e}")
            return self.get_mock_response()
        except Exception as e:
            self.logger.error(f"Error parsing Gemini response: {e}")
            return self.get_mock_response() 