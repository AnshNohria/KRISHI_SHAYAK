from sarvamai import SarvamAI
import os
from dotenv import load_dotenv

API_KEY = os.getenv("SARVAM_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set the API_KEY environment variable")

client = SarvamAI(api_subscription_key=API_KEY)

response = client.speech_to_text.transcribe(
    file=open("speech.mp3", "rb"),
    model="saarika:v2",
    language_code="en-IN"
)

print(response)
