# 🌾 Krishi Dhan Sahayak - AI-Powered Agriculture Assistant

A comprehensive, AI-driven agricultural assistant that helps Indian farmers with intelligent guidance, weather information, FPO connections, and government scheme access. Built with modern tool-based architecture for reliability and extensibility.

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

# 3) Run the chatbot
& .\.venv\Scripts\python.exe .\chatbot.py
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
   - 2,947 Farmer Producer Organizations database
   - Distance-based nearest FPO search
   - Smart geocoding with fallback systems

5. **RAG System** (`rag/`)
   - 6,010+ agricultural advisory chunks
   - ChromaDB vector database
   - Semantic search for farming guidance

## ✨ Key Features

### 🤖 AI-Powered Intelligence
- **Natural Language Processing**: Chat naturally about farming needs
- **Context Awareness**: Remembers location and farming context  
- **Smart Tool Selection**: Automatically chooses appropriate data sources
- **Verified Responses**: All answers backed by reliable data

### 🛠️ Comprehensive Tool Suite
- **Weather Intelligence**: Current conditions + agricultural forecasts
- **Location Services**: Find shops, KVKs, and FPOs nearby
- **Government Schemes**: 534+ schemes with eligibility and application details
- **Farming Guidance**: Expert agricultural advice and best practices

### 🌐 Multi-Provider Reliability
- **Weather**: OpenWeatherMap → Visual Crossing fallback
- **Geocoding**: LocationIQ → Geoapify fallback  
- **Maps**: Geoapify → Foursquare fallback
- **Error Handling**: Graceful degradation when services are unavailable

### 🇮🇳 India-Focused Design
- **Regional Optimization**: Built specifically for Indian agriculture
- **Local Context**: State-specific schemes and regional farming practices
- **Farmer-Friendly**: Simple interface with actionable information

## 🎮 How to Use

### Example Conversations:
```
🌾 You: What should I plant in Punjab this month?
🤖 Assistant: Based on current weather and season data...

🌾 You: Is today good for spraying pesticides in Ludhiana?  
🤖 Assistant: Checking weather conditions for optimal spraying...

🌾 You: How do I join an FPO near Batala?
🤖 Assistant: Found 5 FPOs near Batala, Punjab...

🌾 You: What government schemes are available for cotton farmers?
🤖 Assistant: Here are relevant schemes from our database...

🌾 You: My crops are showing yellow leaves, what should I do?
🤖 Assistant: Based on agricultural best practices...
```

## 📊 Database Coverage

### Government Schemes
- **534+ Active Schemes**: Comprehensive government program database
- **State-Specific**: Schemes filtered by region and eligibility
- **Detailed Information**: Benefits, eligibility, application process

### FPO Network  
- **2,947 Organizations**: Complete FPO database across India
- **Location-Based Search**: Find nearest FPOs with distance calculation
- **Contact Information**: Direct connections to local organizations

### Agricultural Advisory
- **6,010+ Knowledge Chunks**: Expert farming guidance
- **Semantic Search**: Natural language query understanding
- **Context-Aware**: Responses tailored to farming conditions

### Location Services
- **Krishi Vigyan Kendras**: Agricultural extension centers
- **Input Shops**: Seed, fertilizer, and equipment suppliers
- **Weather Stations**: Hyperlocal weather data

## 🎯 Perfect For:

✅ **Indian Farmers** seeking intelligent agricultural guidance  
✅ **Agricultural Extension Workers** providing comprehensive farmer support  
✅ **FPO Coordinators** helping farmers find and join organizations  
✅ **Agricultural Students** learning about modern farming practices  
✅ **Government Officials** delivering citizen services  

## 🛠️ Technical Features

### Reliability & Performance
- **Multi-Provider Fallbacks**: Never lose service due to single API failures
- **Intelligent Caching**: Optimized response times for repeated queries  
- **Error Handling**: Graceful degradation with informative messages
- **Rate Limiting**: Built-in protection against API quota exhaustion

### Data Quality
- **Verified Sources**: All information from authoritative agricultural sources
- **Regular Updates**: Database refreshed with latest scheme information
- **Quality Assurance**: Responses validated against multiple data points

### Developer Experience
- **Modular Architecture**: Easy to extend with new tools and services
- **Clean APIs**: Well-defined interfaces between components
- **Comprehensive Logging**: Full observability for debugging and monitoring
- **Type Safety**: Python type hints throughout the codebase

## 📝 Recent Updates

### LocationIQ Integration
- **Primary Geocoding**: LocationIQ as first choice for address resolution
- **Geoapify Fallback**: Automatic fallback for rate limit protection
- **Enhanced Accuracy**: Better location resolution for FPO searches

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
