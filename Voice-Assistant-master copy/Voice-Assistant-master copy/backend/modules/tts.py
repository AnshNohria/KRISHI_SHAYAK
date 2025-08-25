from sarvamai import SarvamAI
import os
from dotenv import load_dotenv

API_KEY = os.getenv("SARVAM_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set the API_KEY environment variable")

client = SarvamAI(api_subscription_key=API_KEY)

response = client.text_to_speech.convert(
    text="Hello, how are you?",
    target_language_code="en-IN",
)

print(response)
