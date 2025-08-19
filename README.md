# 🌾 Krishi Dhan Sahayak - AI-Powered Agriculture Assistant

A comprehensive, AI-driven agricultural assistant that helps Indian farmers with intelligent guidance, weather information, FPO connections, and government scheme access. Built with modern tool-based architecture for reliability and extensibility.

## 📥 Prices Dataset Setup (for Market Price tools)

The price tools use a local CSV of historical mandi prices.

- Create a folder named `data/` at the repo root (if it doesn't exist).
- Place your dataset file as `data/historical_prices.csv`.
- Open `marketPrice.py` and update the `HISTORICAL_CSV` path to point to this file on Windows, for example:
   - `HISTORICAL_CSV = ".\\data\\historical_prices.csv"`
   - Download The CSV here : https://drive.google.com/file/d/1F8eoP0YY1P87deEZ6Ysr8HRCZw-c395o/view?usp=sharing

If you have a different filename or location, set the full path accordingly.

## 🚀 Quick Start (Windows PowerShell)

```powershell
# 1) Create virtual environment and install dependencies
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) Set up API keys (copy .env.example to .env and add your keys)
$env:OPENWEATHER_API_KEY = "..."         # Weather data
$env:VISUAL_CROSSING_API_KEY = "..."     # Weather fallback
$env:GEOAPIFY_API_KEY = "..."            # Maps/shops/KVK
$env:LocationIQ_API_KEY = "..."          # Primary geocoding
$env:GEMINI_API_KEY = "..."              # AI agent

# 3) Run the app
# If you have a runner script named main.py
& .\.venv\Scripts\python.exe .\main.py

# Or run the orchestrator directly
& .\.venv\Scripts\python.exe .\orchestrator.py
```

## 🏗️ Architecture Overview

### Modern Tool-Based Agent System
- **AI Agent**: Routes all queries through intelligent tool selection
- **Multi-Tool Integration**: Weather, Maps, FPO, RAG, KVK search
- **Fallback Systems**: Multiple API providers for reliability
- **Data-Driven**: All responses backed by verified data sources

### Core Components

1. **AI Agent** (`ai/agent.py` & `ai/function_agent.py`)
   - Intelligent query routing and tool selection
   - Context-aware conversation handling
   - Gemini-powered natural language understanding

2. **Weather Service** (`weather/service.py`)
   - Dual API support (OpenWeatherMap + Visual Crossing)
   - Comprehensive geocoding with LocationIQ primary + Geoapify fallback
   - Farmer-specific weather insights

3. **Maps & Location Services** (`maps/`)
   - Agricultural shop search
   - Krishi Vigyan Kendra (KVK) finder
   - Dual API architecture (Geoapify + Foursquare)

4. **FPO Service** (`fpo/service.py`)
   # Krishi Dhan Sahayak

   🌾 **Krishi Dhan Sahayak** is an advanced, modular agricultural assistant for Indian farmers, FPOs, and agri-entrepreneurs. It combines state-of-the-art retrieval-augmented generation (RAG), real-time weather, market, and scheme search, and a multilingual voice interface powered by Sarvam.

   ---

   ## 🚀 Features

   - **Conversational AI Orchestrator**: Unified agent routes queries to the right tool (weather, market, FPO, maps, RAG, schemes) and returns clear, actionable answers.
   - **RAG Chatbot**: ChromaDB-powered retrieval from ICAR advisories and PDFs, with Gemini-based query optimization and context-aware search.
   - **Weather Chatbot**: Real-time weather for any Indian location, with agricultural advice, using OpenWeatherMap and Visual Crossing APIs.
   - **Market Price Tools**: Predicts and fetches mandi prices for any commodity, district, and state.
   - **FPO Finder**: Returns the 3–5 nearest FPOs in your state, using robust geocoding and distance logic.
   - **Maps Chatbot**: Finds KVKs, agri shops, and more, using Geoapify and dual geocoding APIs.
   - **Scheme Search**: Semantic search for government schemes, with eligibility and benefit summaries.
   - **Multilingual Voice Frontend (Sarvam Integration)**:
     - � **Voice input in any language**: Users can speak their query in Hindi, Punjabi, Tamil, Marathi, etc.
     - 🗣️ **Voice output in user's language**: The answer is returned in the same language as the query.
     - 🌐 **How it works**: Sarvam handles speech-to-text and text-to-speech, detects language, and pipes the text query to the orchestrator. The orchestrator returns the answer, which is then spoken back in the user's language.

   ---

   ## 🏗️ Project Structure

   ```
   Krishi_Dhan_Sahayak/
   ├── Advisory/
   │   ├── rag/                # RAG ingestion and retriever logic
   │   └── simple_chatbot.py   # RAG chatbot
   ├── fpo/                    # FPO finder and chatbot
   ├── maps/                   # Maps/KVK/agri shop chatbot
   ├── weather/                # Weather chatbot and service
   ├── marketPrice.py          # Market price tools
   ├── scheme_search_tool.py   # Scheme search
   ├── orchestrator.py         # Main agentic orchestrator
   ├── requirements.txt        # All dependencies
   └── ...
   ```

   ---

   ## ⚡ Quickstart

   1. **Clone the repo**
   2. **Install dependencies**
      ```powershell
      python -m venv .venv
      .venv\Scripts\activate
      pip install -r requirements.txt
      ```
   3. **Set up your .env file**
      - Add API keys for OpenWeatherMap, Visual Crossing, Geoapify, Gemini, etc.
   4. **Ingest PDFs for RAG**
      ```powershell
      python ingest.py 2
      ```
   5. **Run the orchestrator**
      ```powershell
      python orchestrator.py
      ```
   6. **(Optional) Run a chatbot directly**
      ```powershell
      python Advisory/simple_chatbot.py
      python weather/simple_weather_chatbot.py
      python maps/simple_maps_chatbot.py
      ```
   7. **Voice Frontend (Sarvam)**
      - Follow Sarvam’s setup instructions (see their docs)
      - Start the Sarvam voice interface; it will handle user speech, call the orchestrator, and speak the answer back in the user’s language.

   ---

   ## 🗣️ Sarvam Voice Integration

   - **Truly Multilingual**: Users can speak in any Indian language; Sarvam detects, transcribes, and translates as needed.
   - **Seamless Orchestration**: Sarvam passes the recognized text to the orchestrator, which routes the query and returns a text answer.
   - **Natural Output**: The answer is spoken back in the same language, making the system accessible to all.
   - **Plug-and-play**: No code changes needed—just run Sarvam and the orchestrator.

   ---

   ## 🧠 Tech Stack
   - Python 3.8+
   - ChromaDB (vector store)
   - SentenceTransformers (embeddings)
   - Google Gemini (Generative AI)
   - Geoapify, LocationIQ, OpenWeatherMap, Visual Crossing (APIs)
   - Sarvam (voice interface)
   - Langchain (agent framework)
   - BeautifulSoup4, Requests, Pydantic, etc.

   ---

   ## 📝 Notes
   - **ChromaDB data is not versioned in git**: Always re-ingest PDFs after clone.
   - **API keys required**: See `.env.example` for all needed keys.
   - **PDFs**: Only ingest advisories, not FPO lists.
   - **Voice**: Sarvam is optional but highly recommended for accessibility.

   ---

   ## 🤝 Credits
   - ICAR, IMD, and government sources for advisories and data
   - Sarvam for the open-source voice interface
   - ChromaDB, SentenceTransformers, and the open-source Python community

   ---

   ## 📄 License
   MIT
### Dual Maps API
- **Geoapify + Foursquare**: Combined coverage for shop and service discovery
- **Smart Routing**: Automatic selection based on query type and availability
- **Comprehensive Results**: Agricultural shops, KVKs, and input suppliers

## 🔧 Future Enhancements

1. **Mobile App**: Native Android/iOS applications
2. **Voice Interface**: Speech-to-text for hands-free operation
3. **Crop Monitoring**: Image-based disease and pest identification  
4. **Market Prices**: Real-time commodity pricing integration
5. **Weather Alerts**: Proactive notifications for farming activities

## 📄 License

This project is designed to help farmers access government schemes and support agricultural development in India.

---

**Built with ❤️ for Indian farmers** 🇮🇳🌾

Transform your agricultural decision-making with AI intelligence! 🚜🤖
