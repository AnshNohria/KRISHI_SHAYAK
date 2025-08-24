import os
import tempfile
import base64
import io
import logging
from flask import Flask, request, jsonify, make_response, send_file
from flask_cors import CORS
from pydantic import BaseModel, ValidationError
from sarvamai import SarvamAI
from dotenv import load_dotenv
from pathlib import Path
from collections import defaultdict
import threading
import json
from groq.types.chat import ChatCompletionUserMessageParam
import google.generativeai as genai
import sys


current_dir = os.path.dirname(os.path.abspath(__file__))  # backend/
parent_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))  # KRISHI_SHAYAK

sys.path.append(parent_dir)
from orchestrator import OrchestratorAgent

orchestrator_obj = OrchestratorAgent()

# Load environment variables once
# Always load .env from KRISHI_SHAYAK root, not local/backend
KRISHI_SHAYAK_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=KRISHI_SHAYAK_ROOT / '.env', override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)



app = Flask(__name__)
CORS(app)

# SarvamAI client setup
sarvam_api_key = os.getenv("SARVAM_API_KEY")
if not sarvam_api_key:
    logger.error("SARVAM_API_KEY environment variable not set")
    raise RuntimeError("SARVAM_API_KEY environment variable not set")
sarvam_client = SarvamAI(api_subscription_key=sarvam_api_key)

# Gemini API key setup
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    logger.error("GEMINI_API_KEY environment variable not set")
    raise RuntimeError("GEMINI_API_KEY environment variable not set")
genai.configure(api_key=gemini_api_key)

# -------- Pydantic schemas --------

class SimpleRequest(BaseModel):
    request: str

class ChatResponse(BaseModel):
    response: str

CHAT_HISTORY_DIR = os.path.join(os.path.dirname(__file__), "chat_history")
if not os.path.exists(CHAT_HISTORY_DIR):
    os.makedirs(CHAT_HISTORY_DIR)

def load_history(session_id):
    path = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
    if os.path.exists(path):
        history = []
        with open(path, "r") as f:
            for line in f:
                if line.startswith("User: "):
                    history.append({"role": "user", "content": line[len("User: "):].strip()})
                elif line.startswith("Bot: "):
                    history.append({"role": "assistant", "content": line[len("Bot: "):].strip()})
                elif line.startswith("System: "):
                    history.append({"role": "system", "content": line[len("System: "):].strip()})
        return history
    return []

def save_history(session_id, history):
    path = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
    # Save in human-readable format
    with open(path, "w") as f:
        for msg in history:
            if msg["role"] == "user":
                f.write(f"User: {msg['content']}\n")
            elif msg["role"] == "assistant":
                f.write(f"Bot: {msg['content']}\n")
            elif msg["role"] == "system":
                f.write(f"System: {msg['content']}\n")

def get_user_language(history, header_language_code):
    # Only use header value, ignore detection
    return header_language_code or "hi-IN"


@app.route("/voice-chat", methods=["POST"])
def voice_chat():
    temp_audio_path = None
    try:
        logger.info("Received /voice-chat request content-type=%s size=%d", request.content_type, len(request.data or b''))

        # --- Validate & session setup ---
        session_id = request.headers.get('X-Session-ID')
        if not session_id:
            return make_response(jsonify({"detail": "Missing X-Session-ID header"}), 400)
        language_code = request.headers.get('X-Language-Code', 'en-IN')
        user_language_code = language_code
        history = load_history(session_id)
        if not history:
            history.append({"role": "system", "content": (
                "You are 'Agri Mitra', a concise and friendly AI voice assistant for Indian farmers. "
                "If the user's question is about agriculture, government schemes, or crop advice that requires knowing their state and district, ask for those details. "
                "Otherwise, answer directly and keep it brief. Reply in the user's language."
            )})

        # --- Persist inbound audio ---
        audio_file = request.files.get("file")
        if audio_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                temp_audio_path = tmp.name
                audio_file.save(temp_audio_path)
        else:
            if not request.data:
                return make_response(jsonify({"detail": "No audio payload received"}), 400)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                temp_audio_path = tmp.name
                tmp.write(request.data)
        logger.info("Saved incoming audio: %s (%d bytes)", temp_audio_path, os.path.getsize(temp_audio_path))

        # --- STT ---
        with open(temp_audio_path, "rb") as aud:
            stt_response = sarvam_client.speech_to_text.transcribe(
                file=aud,
                model="saarika:v2",
                language_code=user_language_code,
            )
        user_text = getattr(stt_response, "transcript", None)
        logger.info("Transcription: %s", user_text)
        if not user_text:
            return make_response(jsonify({"detail": "No transcription text returned"}), 500)
        history.append({"role": "user", "content": user_text})

        # --- Build Gemini prompt (reference style) ---
        def history_to_prompt(hist):
            p = "This is a persistent conversation. Use prior info (name, location, preferences)."
            for msg in hist:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "system":
                    p += f"\nSystem: {content}"
                elif role == "user":
                    p += f"\nUser: {content}"
                elif role == "assistant":
                    p += f"\nAssistant: {content}"
            return p
        language_name_map = {"hi-IN": "Hindi", "en-IN": "English", "pa-IN": "Punjabi", "bn-IN": "Bengali", "gu-IN": "Gujarati", "kn-IN": "Kannada", "ml-IN": "Malayalam", "mr-IN": "Marathi", "od-IN": "Odia", "ta-IN": "Tamil", "te-IN": "Telugu"}
        language_name = language_name_map.get(user_language_code, "Hindi")
        gemini_prompt = history_to_prompt(history) + f"\nAlways reply ONLY in this language: {language_name}. Keep it concise."

        # --- LLM Response (primary orchestrator; fallback to raw Gemini) ---
        llm_text = None
        try:
            llm_text = orchestrator_obj.handle_query(user_text)
        except Exception as e:
            logger.warning("Orchestrator failed, will fallback to Gemini: %s", e)
        if not llm_text or len(llm_text.strip()) < 2:
            model = genai.GenerativeModel("gemini-1.5-flash")
            try:
                chat_response = model.generate_content(gemini_prompt)
                llm_text = (getattr(chat_response, 'text', '') or '').strip()
            except Exception as e:
                logger.error("Gemini fallback failed: %s", e)
                llm_text = "I heard you. Could you please repeat or clarify your farming question?"

        # --- Sanitize for TTS ---
        def sanitize_tts(text: str) -> str:
            if not text:
                return "Please repeat your question."
            cleaned = text.replace('**', '').replace('*', '')
            cleaned = cleaned.replace('#', '')
            if len(cleaned) > 800:
                cleaned = cleaned[:800] + '...'
            return cleaned.strip()
        tts_input = sanitize_tts(llm_text)
        if not tts_input:
            tts_input = "Please repeat your question."

        # --- TTS ---
        tts_response = sarvam_client.text_to_speech.convert(
            text=tts_input,
            target_language_code=user_language_code,
            speaker="anushka",
            pitch=0,
            pace=1,
            loudness=1,
            speech_sample_rate=22050,
            enable_preprocessing=True,
            model="bulbul:v2"
        )
        if not getattr(tts_response, 'audios', None):
            return make_response(jsonify({"detail": "No audio returned from TTS"}), 500)
        audio_base64 = tts_response.audios[0]

        # Infer mime (simple header check)
        def infer_mime(b64data: str) -> str:
            try:
                raw = base64.b64decode(b64data[:60] + '==', validate=False)
                if raw.startswith(b'RIFF'):
                    return 'audio/wav'
                if raw.startswith(b'ID3') or raw[:2] == b'\xff\xfb':
                    return 'audio/mpeg'
                if raw.startswith(b'OggS'):
                    return 'audio/ogg'
            except Exception:
                pass
            return 'audio/wav'
        audio_mime = infer_mime(audio_base64)

        history.append({"role": "assistant", "content": llm_text})
        save_history(session_id, history)

        return jsonify({
            "transcription": user_text,
            "response": llm_text,
            "audio_base64": audio_base64,
            "audio_mime": audio_mime,
            "chat_history": history
        })

    except Exception as e:
        logger.exception("Error in /voice-chat: %s", str(e))
        return make_response(jsonify({"detail": str(e)}), 500)

    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            logger.info("Deleted temp file: %s", temp_audio_path)


# -------- Main --------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
