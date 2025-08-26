import os
import tempfile
import base64
import io
from flask import Flask, request, jsonify, make_response, send_file
from pydantic import BaseModel, ValidationError
from sarvamai import SarvamAI
import google.generativeai as genai
from dotenv import load_dotenv
# Load environment variables once
load_dotenv()

app = Flask(__name__)

gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not gemini_api_key:
    raise RuntimeError("GEMINI_API_KEY / GOOGLE_API_KEY environment variable not set")
genai.configure(api_key=gemini_api_key)

from dotenv import load_dotenv

# SarvamAI client setup
sarvam_api_key = os.getenv("SARVAM_API_KEY")
if not sarvam_api_key:
    raise RuntimeError("SARVAM_API_KEY environment variable not set")
sarvam_client = SarvamAI(api_subscription_key=sarvam_api_key)

# -------- Pydantic schemas --------

class SimpleRequest(BaseModel):
    request: str

class ChatResponse(BaseModel):
    response: str

# -------- Chat endpoint --------

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if data is None:
            return make_response(jsonify({"detail": "Invalid or missing JSON body"}), 400)
        simple_request = SimpleRequest(**data)

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(simple_request.request)
        content = response.text


        response_obj = ChatResponse(response=content)
        return jsonify(response_obj.dict())

    except ValidationError as ve:
        return make_response(jsonify({"detail": ve.errors()}), 422)
    except Exception as e:
        return make_response(jsonify({"detail": str(e)}), 500)

# -------- Text-to-Speech endpoint --------

@app.route("/tts", methods=["POST"])
def text_to_speech():
    try:
        data = request.get_json()
        if not data or "text" not in data:
            return make_response(jsonify({"detail": "Missing 'text' in request body"}), 400)

        response = sarvam_client.text_to_speech.convert(
            text=data["text"],
            target_language_code="en-IN",
        )

        if not response.audios or len(response.audios) == 0:
            return make_response(jsonify({"detail": "No audio returned from TTS"}), 500)

        audio_base64 = response.audios[0]
        audio_bytes = base64.b64decode(audio_base64)

        # Save audio locally as 'output.wav' (optional)
        with open("output.wav", "wb") as f:
            f.write(audio_bytes)
        print("Saved TTS audio locally as output.wav")

        return send_file(
            io.BytesIO(audio_bytes),
            mimetype="audio/wav",
            as_attachment=True,
            download_name="output.wav"
        )
    except Exception as e:
        return make_response(jsonify({"detail": str(e)}), 500)

# -------- Speech-to-Text endpoint --------

@app.route("/stt", methods=["POST"])
def speech_to_text():
    temp_file_path = None
    try:
        content_type = request.content_type
        if not content_type or not content_type.startswith("audio/"):
            return make_response(jsonify({
                "detail": f"Invalid Content-Type: {content_type}. Must be an audio MIME type like audio/wav or audio/mpeg."
            }), 400)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            temp_file_path = tmp.name
            tmp.write(request.data)

        with open(temp_file_path, "rb") as audio_file:
            response = sarvam_client.speech_to_text.transcribe(
                file=audio_file,
                model="saarika:v2",
                language_code="en-IN",
            )

        transcription_text = getattr(response, "transcript", None)
        if not transcription_text:
            print("No transcription text found. Full response:", response)
            return jsonify({"detail": "No transcription text found in response"})

        return jsonify({"transcription": transcription_text})
    except Exception as e:
        return make_response(jsonify({"detail": str(e)}), 500)
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.route("/voice-chat", methods=["POST"])
def voice_chat():
    temp_audio_path = None
    try:
        # Validate incoming audio content-type
        content_type = request.content_type
        if not content_type or not content_type.startswith("audio/"):
            return make_response(jsonify({
                "detail": f"Invalid Content-Type: {content_type}. Must be an audio MIME type like audio/wav or audio/mpeg."
            }), 400)

        # Save incoming audio to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            temp_audio_path = tmp.name
            tmp.write(request.data)

        # Step 1: Speech-to-text (STT)
        with open(temp_audio_path, "rb") as audio_file:
            stt_response = sarvam_client.speech_to_text.transcribe(
                file=audio_file,
                model="saarika:v2",
                language_code="en-IN",
            )

        user_text = getattr(stt_response, "transcript", None)
        if not user_text:
            return make_response(jsonify({"detail": "No transcription text found from STT"}), 500)

        # Step 2: Send transcribed text to LLM chat
        from groq.types.chat import ChatCompletionUserMessageParam
        messages = [ChatCompletionUserMessageParam(role="user", content=user_text)]

        model = genai.GenerativeModel("gemini-1.5-flash")
        chat_response = model.generate_content(user_text)
        llm_text = chat_response.text


        # Step 3: Convert LLM response text back to speech (TTS)
        tts_response = sarvam_client.text_to_speech.convert(
            text=llm_text,
            target_language_code="en-IN",
        )

        if not tts_response.audios or len(tts_response.audios) == 0:
            return make_response(jsonify({"detail": "No audio returned from TTS"}), 500)

        audio_base64 = tts_response.audios[0]
        audio_bytes = base64.b64decode(audio_base64)

        # Return the synthesized audio as WAV file
        return send_file(
            io.BytesIO(audio_bytes),
            mimetype="audio/wav",
            as_attachment=True,
            download_name="response.wav"
        )

    except Exception as e:
        return make_response(jsonify({"detail": str(e)}), 500)

    finally:
        # Cleanup temp audio file
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


# -------- Main --------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
