# Krishi Dhan Sahayak (Minimal Agent‑First)

A lean, terminal-based agriculture assistant. All queries route through an agent that uses tools only (Weather, Maps, FPO, RAG). Answers are strictly data-backed. If the topic isn’t farming or there isn’t enough verified data, it says so.

## Quick start (Windows PowerShell)

```powershell
# 1) Create venv and install
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) Optional: set API keys
$env:OPENWEATHER_API_KEY = "..."
$env:VISUAL_CROSSING_API_KEY = "..."
$env:GEOAPIFY_API_KEY = "..."       # shops/KVK
$env:GEMINI_API_KEY = "..."         # lets the agent summarize sources

# 3) Run
& .\.venv\Scripts\python.exe .\chatbot.py
```

## What it can do
- Weather advisory (OpenWeather + Visual Crossing)
- Nearby shops and KVK via Maps
- FPO lookup (nearest or by state)
- Advisory answers using RAG over ICAR PDFs (Chroma; optional)
- Strict: Only uses gathered sources; won’t hallucinate

## Project layout
```
ai/         # Gemini agent orchestrator (tools + composition)
chatbot.py  # Terminal entry; routes to agent
core/       # Profile (last location), config helpers
fpo/        # FPO dataset + service
maps/       # Maps/places helpers (shops, KVK)
rag/        # Chroma ingest/retrieve (optional; degrades gracefully)
weather/    # Geocoding + weather + advice
tests/      # Basic tests
```

## Notes
- Chroma on Windows: use Docker HTTP server or local PersistentClient (requirements include chromadb 1.0.x).
- ICAR PDFs: put under `PDFs/` and run ingestion when needed; app still runs without RAG.
- If `GEMINI_API_KEY` isn’t set, the agent returns stitched summaries from the retrieved sources.

## Run tests
```powershell
& .\.venv\Scripts\python.exe -m pytest -q
```

## License
For educational and agricultural support purposes.

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For issues and feature requests:
1. Check the troubleshooting section
2. Verify API keys are correctly configured
3. Ensure all dependencies are installed
4. Check network connectivity

---

**Made with ❤️ for Indian Farmers**

*Empowering agriculture through technology and AI assistance*
<!-- Removed duplicated environment variable lines moved to a single section below -->
```

### 3. Run the Application

```bash
# Recommended: Complete menu system
python app.py

# Advanced: AI Chatbot (requires Gemini API)
python chat.py

# Individual services
python -m weather.cli    # Weather only
python -m fpo.cli       # FPO info only
python main.py          # Weather + FPO combined
```

## 🎯 Features Overview

### 🤖 **AI Chatbot** (NEW!)
- **Natural conversation** about farming, weather, and FPOs
- **Context-aware responses** using Gemini AI
- **Integrated services** - automatically gets weather and FPO data
- **Rich interface** with beautiful formatting and commands
- **Chat history** and session saving

### ⛅️ **Weather Intelligence**
- **Dual Weather APIs** - OpenWeatherMap + Visual Crossing with automatic fallback
- **Agricultural Focus** - Crop-specific advice, irrigation recommendations, spraying guidance
- **India-Optimized** - Works with villages across all Indian states
- **Natural Language** - "My village is Moga in Punjab"

### 🏛️ **FPO (Farmer Producer Organization) Guidance**
- **Location-Based Search** - Find nearest FPOs using GPS coordinates
- **Comprehensive Database** - 20+ major FPOs across agricultural states
- **Registration Guidance** - Complete step-by-step process to start/join FPOs
- **Government Schemes** - Latest information on FPO support programs

### 🇮🇳 **Complete India Coverage**
- **All States Supported** - 28 states and 8 union territories
- **Village-Level Data** - Works with small villages and towns
- **Regional FPOs** - State-wise FPO database with contact details

## 📋 Usage Examples

### AI Chatbot Conversations:
```
You: What's the weather like in Batala, Punjab?
AI: I'll get the current weather for Batala, Punjab...
    🌡️ Temperature: 28°C, partly cloudy
    💧 Humidity: 65% - good for crop growth
    🌬️ Wind: 5 m/s - suitable for field operations
    
    Based on these conditions, it's a good day for:
    • Field preparation and sowing
    • Light irrigation if needed
    • Fertilizer application

You: Are there any FPOs near my village?
AI: Based on your location in Batala, Punjab, I found these nearby FPOs:
    
    🏛️ Punjab Kisan Producer Company Ltd (45 km away)
    📞 Contact: +91-9876543210
    🌾 Crops: wheat, rice, cotton, sugarcane
    
    Would you like registration guidance or more details about their services?
```

### Weather Service:
```
📍 Enter location: Batala, Punjab
🌡️ Temperature: 28°C - suitable for most crops
💧 Humidity: 65% - good for crop growth  
🌧️ Rain chance: 20% - good for field operations
```

### FPO Service:
```
📍 Location: Batala, Punjab
🏛️ Found 3 FPOs near your location:
   1. Punjab Kisan Producer Company Ltd (45.2 km)
   2. Majha Farmers Producer Organization (78.1 km)
```

## 📁 Project Structure

```
├── app.py               # 🎯 Main menu application (START HERE)
├── chat.py              # 🤖 AI Chatbot launcher  
├── main.py              # 🚀 Integrated weather + FPO
│
├── core/                # 🔧 Core utilities
│   ├── config.py        #   Configuration & API keys
│   └── __init__.py      #   Package exports
│
├── weather/             # 🌤️ Weather module
│   ├── cli.py           #   CLI interface
│   ├── service.py       #   API services (dual API)
│   └── __init__.py      #   Package exports
│
├── fpo/                 # 🏛️ FPO module  
│   ├── cli.py           #   CLI interface
│   ├── service.py       #   FPO database & search
│   └── __init__.py      #   Package exports
│
├── chatbot/             # 🤖 AI Chatbot module
│   ├── interface.py     #   Rich UI interface
│   ├── service.py       #   Gemini AI integration
│   └── __init__.py      #   Package exports
│
├── requirements.txt     # 📦 Dependencies
├── .env.example         # 🔑 API key template
└── README.md           # 📚 This file
```

## 🤖 AI Chatbot Commands

Once in the chatbot, you can use these commands:

- `/help` - Show help and commands
- `/suggestions` - Get suggested questions based on context
- `/context` - Show current context (location, weather, etc.)
- `/clear` - Clear conversation context
- `/history` - Show recent chat history
- `/save` - Save current chat session
- `/quit` - Exit the chatbot

## 🔑 API Keys Setup

### Required for AI Chatbot:
1. **Google Gemini AI** (Free)
   - Visit: https://makersuite.google.com/app/apikey
   - Create account and generate API key
   - Add to `.env`: `GEMINI_API_KEY=your_key_here`

### Optional for Enhanced Weather:
2. **OpenWeatherMap** (Free - 1000 calls/day)
   - Visit: https://openweathermap.org/api
   - Register and get API key
   - Add to `.env`: `OPENWEATHER_API_KEY=your_key_here`

3. **Visual Crossing** (Free - 1000 calls/day)
   - Visit: https://www.visualcrossing.com/
   - Register and get API key  
   - Add to `.env`: `VISUAL_CROSSING_API_KEY=your_key_here`

## 📦 Dependencies

```
httpx==0.27.0              # HTTP client for API calls
python-dotenv==1.0.1       # Environment variable management
google-generativeai==0.3.2 # Gemini AI integration
rich==13.7.0              # Beautiful terminal formatting
colorama==0.4.6           # Cross-platform colored terminal text
```

**Total: 5 dependencies** - Clean and focused!

## 🌾 Service Capabilities

### 🤖 AI Chatbot Features:
- **Smart Context** - Remembers your location and previous questions
- **Weather Integration** - Automatically gets weather data when you mention location
- **FPO Integration** - Finds nearby FPOs based on your location
- **Agricultural Expertise** - Trained on Indian farming practices
- **Government Schemes** - Up-to-date information on farming subsidies
- **Natural Language** - Chat naturally, no commands needed

### 🏛️ FPO Database (20+ Organizations):
- **Punjab**: 3 FPOs (Ludhiana, Bathinda, Amritsar)
- **Haryana**: 2 FPOs (Karnal, Nuh)
- **Uttar Pradesh**: 2 FPOs (Meerut, Jhansi)
- **Maharashtra**: 2 FPOs (Nagpur, Pune)
- **Karnataka**: 2 FPOs (Chikmagalur, Belgaum)
- **Gujarat**: 2 FPOs (Rajkot, Kutch)
- And more across Tamil Nadu, Andhra Pradesh, West Bengal, etc.

### 📊 Government Schemes Covered:
1. Formation and Promotion of FPOs Scheme (2020-2028)
2. NABARD Producer Organization Development Fund

## ⚙️ Recommended Setup for RAG (Option 2: WSL/Linux/mac with Python 3.11)

For a stable ChromaDB experience, run ingestion and retrieval in Linux/mac or WSL with Python 3.11 and NumPy 1.26.x. The Windows host can keep using PowerShell for everything else.

### 1) Prepare environment (WSL/Linux/mac)

```bash
# Create and activate a Python 3.11 venv
python3.11 -m venv .venv
source .venv/bin/activate

# Install core deps
pip install -r requirements.txt

# Pin NumPy and install Chroma
pip install "numpy==1.26.4" "chromadb==0.5.5"

# Optional: speed-ups and telemetry deps pulled by chroma are fine on Linux/mac
```

### 2) Ingest ICAR PDFs into Chroma

```bash
python -m rag.ingest "ICAR-En-Kharif-Agro-Advisories-for-Farmers-2025.pdf" \
                     "Rabi-Agro-Advisory-2021-22.pdf"
# Vectors are stored under data/vector/chroma (git-ignored)
```

### 3) Run the chatbot

```bash
python chatbot.py
```

Notes
- If you work from Windows VS Code, use the Remote - WSL extension to open this folder in WSL and run the above commands there.
- The repository already falls back gracefully when Chroma isn’t present; the above steps enable full advisory retrieval.

## 🪟 Windows (No WSL) — Use Chroma Server via Docker

Avoid local build issues by running Chroma as a container and connecting over HTTP.

1) Start Chroma Server (Docker Desktop installed)

```powershell
docker volume create chroma_data
docker run -d --name chroma `
   -p 8000:8000 `
   -v chroma_data:/chroma/index `
   ghcr.io/chroma-core/chroma:latest
```

2) Point the app to the server (PowerShell)

```powershell
$env:CHROMA_HOST = "localhost"
$env:CHROMA_PORT = "8000"
# or set a full URL
# $env:CHROMA_HTTP_URL = "http://localhost:8000"
```

3) Ingest PDFs (Windows PowerShell)

```powershell
& .\.venv\Scripts\python.exe -m rag.ingest "ICAR-En-Kharif-Agro-Advisories-for-Farmers-2025.pdf" "Rabi-Agro-Advisory-2021-22.pdf"
```

4) Run chatbot

```powershell
& .\.venv\Scripts\python.exe .\chatbot.py
```

This path requires no compiler toolchain on Windows, and works with the code’s new HTTP client support.

3. SFAC Support Programs
4. Mission for Integrated Development of Horticulture
5. National Food Security Mission
6. Paramparagat Krishi Vikas Yojana (Organic)
7. PM-KISAN FPO Scheme

## 🎮 How to Use

### For Beginners:
```bash
python app.py
# Choose option 1-7 from the menu
```

### For AI Experience:
```bash
python chat.py
# Chat naturally with the AI assistant
```

### Examples of what you can ask the AI:
- "What should I plant in Punjab this month?"
- "Is today good for spraying pesticides in Ludhiana?"
- "How do I join an FPO near Batala?"
- "What government schemes are available for cotton farmers?"
- "My crops are showing yellow leaves, what should I do?"

## 🎯 Perfect For:

✅ **Indian Farmers** looking for intelligent agricultural guidance  
✅ **Agricultural Extension Workers** needing comprehensive farmer support tools  
✅ **FPO Coordinators** helping farmers find and join organizations  
✅ **Agricultural Students** learning about modern farming practices  
✅ **Government Officials** providing citizen services  

## 🌟 What Makes It Special:

1. **AI-Powered** - Smart conversations, not just command responses
2. **Context-Aware** - Remembers your location and farming context
3. **Integrated Services** - Weather + FPO + AI in one seamless experience
4. **India-Focused** - Built specifically for Indian agriculture
5. **Easy to Use** - Simple menu system + natural language chat
6. **Free to Use** - Open source with free API tiers

Transform your agricultural decision-making with AI intelligence! 🚜🤖
