"""
Core utilities and configurations for Krishi Dhan Sahayak
"""

import os
import logging
from dotenv import load_dotenv
from typing import Optional, Tuple

# Load environment variables
load_dotenv()

# Configuration
class Config:
    """Application configuration"""
    
    # API Keys
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
    VISUAL_CROSSING_API_KEY = os.getenv("VISUAL_CROSSING_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    # Geoapify maps key
    GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY") or os.getenv("GEOAPIFY_MAPS_API")
    
    # API URLs
    OPENWEATHER_GEOCODE_URL = "http://api.openweathermap.org/geo/1.0/direct"
    OPENWEATHER_WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"
    VISUAL_CROSSING_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    
    # Application settings
    DEFAULT_TIMEOUT = 15
    MAX_FPO_RESULTS = 5
    CHAT_HISTORY_LIMIT = 50

# Logging setup
def setup_logging(level: str = "WARNING"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

# Common utilities
def validate_api_keys() -> dict:
    """Validate which API keys are available"""
    keys_status = {
        'openweather': bool(Config.OPENWEATHER_API_KEY),
        'visual_crossing': bool(Config.VISUAL_CROSSING_API_KEY),
    'gemini': bool(Config.GEMINI_API_KEY),
    'maps': bool(Config.GEOAPIFY_API_KEY)
    }
    return keys_status

def get_available_services() -> list:
    """Get list of available services based on API keys"""
    keys = validate_api_keys()
    services = []
    
    if keys['openweather'] or keys['visual_crossing']:
        services.append('weather')
    
    services.append('fpo')  # FPO doesn't need API key
    
    if keys['gemini']:
        services.append('chatbot')
    if keys['maps']:
        services.append('maps')
    
    return services

# Indian states list (centralized)
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", 
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", 
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", 
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", 
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", 
    "Delhi", "Chandigarh", "Puducherry", "Jammu and Kashmir", "Ladakh"
]

# Common exceptions
class KrishiError(Exception):
    """Base exception for Krishi Dhan Sahayak"""
    pass

class APIKeyMissingError(KrishiError):
    """Raised when required API key is missing"""
    pass

class ServiceUnavailableError(KrishiError):
    """Raised when a service is unavailable"""
    pass
