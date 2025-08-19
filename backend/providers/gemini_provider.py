import google.genai as genai
from config import settings

def get_gemini_client():
    """Get configured Gemini client"""
    return genai.Client(api_key=settings.GEMINI_API_KEY)
