"""Configuration settings for the Agriculture Schemes Chatbot"""

import os
from typing import Optional

# Gemini API Configuration (loaded from environment; do not hardcode)
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# Database Configuration
CHROMA_DB_PATH: str = "./chroma_db"
COLLECTION_NAME: str = "agriculture_schemes"

# Scraping Configuration
BASE_URL: str = "https://www.myscheme.gov.in"
AGRICULTURE_CATEGORY_URL: str = "https://www.myscheme.gov.in/search/category/Agriculture,Rural%20&%20Environment"

# Request Configuration
REQUEST_DELAY: float = 1.0  # Delay between requests in seconds
MAX_RETRIES: int = 3
REQUEST_TIMEOUT: int = 30

# Chatbot Configuration
MAX_SEARCH_RESULTS: int = 5
CONVERSATION_MEMORY_SIZE: int = 10

# LLM Configuration
LLM_MODEL: str = "gemini-2.5-flash"
LLM_TEMPERATURE: float = 0.3
CONVERT_SYSTEM_MESSAGE_TO_HUMAN: bool = True

# Logging Configuration
LOG_LEVEL: str = "INFO"
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
