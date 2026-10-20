"""
OpenAI LLM provider implementation
"""
import json
import requests
from typing import Dict, Any, Optional
from ..base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI GPT implementation"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "openai")
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.model_name = "gpt-4o"
    
    def is_available(self) -> bool:
        """Check if the provider is available (has API key)"""
        return bool(self.api_key and self.api_key.strip())
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        return {
            "name": self.model_name,
            "provider": "OpenAI",
            "max_tokens": 4096,
            "supports_streaming": True
        }
    
    def analyze_text(self, text: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Analyze text and return structured outline and questions"""
        if not self.is_available():
            self.logger.warning("OpenAI provider not available, returning mock response")
            return self.get_mock_response()
        
        # Use default prompt if none provided
        if not prompt:
            final_prompt = self._get_default_prompt().format(text=text)
        else:
            # If custom prompt is provided, use it directly (it already contains the text)
            final_prompt = prompt
        
        try:
            self.logger.info("Sending request to OpenAI API")
            
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Bạn là một chuyên gia phân tích tài liệu giáo dục. Hãy trả về đúng JSON format như yêu cầu."
                        },
                        {
                            "role": "user",
                            "content": final_prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4069
                },
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                self.logger.info("Successfully received response from OpenAI API")
                return self._parse_json_response(content)
            else:
                self.logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return self.get_mock_response()
                
        except Exception as e:
            self.logger.error(f"Error calling OpenAI API: {e}")
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
        - Tùy vào văn bản cần phân tích mà mỗi subsections sẽ chứa units phù hợp. 

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
            ]
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
                    self.logger.warning("Invalid response structure from OpenAI")
                    return self.get_mock_response()
            else:
                self.logger.warning("No JSON found in OpenAI response")
                return self.get_mock_response()
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from OpenAI response: {e}")
            return self.get_mock_response()
        except Exception as e:
            self.logger.error(f"Error parsing OpenAI response: {e}")
            return self.get_mock_response()
    
    def _parse_json_response_raw(self, text: str) -> Any:
        """Parse JSON response from LLM without validation"""
        try:
            # Try to extract JSON from response with better regex
            import re
            
            # First, try to find the start and end of JSON object
            # Look for the first { and find the matching closing }
            start_idx = text.find('{')
            if start_idx == -1:
                self.logger.warning("No JSON object found in OpenAI response")
                return text
            
            # Find the matching closing brace by counting braces
            brace_count = 0
            end_idx = start_idx
            
            for i, char in enumerate(text[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break
            
            if brace_count != 0:
                self.logger.warning("Unmatched braces in JSON response")
                return text
            
            json_str = text[start_idx:end_idx + 1]
            
            # Try to parse the JSON
            result = json.loads(json_str)
            return result
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from OpenAI response: {e}")
            # Try to fix common JSON issues
            try:
                # Remove any trailing text after the last }
                last_brace = text.rfind('}')
                if last_brace != -1:
                    json_str = text[:last_brace + 1]
                    result = json.loads(json_str)
                    return result
            except:
                pass
            return text  # Return raw text if JSON parsing fails
        except Exception as e:
            self.logger.error(f"Error parsing OpenAI response: {e}")
            return text  # Return raw text if any error occurs
    
    def analyze_text_raw(self, text: str, prompt: Optional[str] = None) -> Any:
        """Analyze text and return raw response without validation"""
        try:
            # Use custom prompt if provided, otherwise use default
            if prompt:
                # If custom prompt is provided, use it directly (it already contains the text)
                final_prompt = prompt
            else:
                # Use default prompt and format it with text
                final_prompt = self._get_default_prompt().format(text=text)
            
            self.logger.info("Sending request to OpenAI API")
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Bạn là một chuyên gia phân tích tài liệu giáo dục. Hãy trả về đúng JSON format như yêu cầu."
                        },
                        {
                            "role": "user",
                            "content": final_prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4069
                },
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                self.logger.info("Successfully received response from OpenAI API")
                return self._parse_json_response_raw(content)
            else:
                self.logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error calling OpenAI API: {e}")
            return None 