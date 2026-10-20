import os
import requests
from llm_service import llm_service

def analyze_text_with_llm(text: str, provider_name: str = None):
    """
    Gửi văn bản lên LLM API để phân tích outline và câu hỏi.
    Trả về JSON với hai khóa: outline, questions.
    
    Args:
        text: Văn bản cần phân tích
        provider_name: Tên provider (gemini, openai, deepseek) hoặc None để dùng default
    
    Returns:
        Dict chứa outline và questions
    """
    return llm_service.analyze_text(text, provider_name)

def get_available_providers():
    """
    Lấy danh sách các provider có sẵn
    
    Returns:
        Dict chứa trạng thái của từng provider
    """
    return llm_service.get_available_providers()

def get_default_provider():
    """
    Lấy tên provider mặc định
    
    Returns:
        Tên provider mặc định hoặc None nếu không có provider nào
    """
    return llm_service.get_default_provider() 