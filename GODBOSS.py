#!/usr/bin/env python3
"""
🌾 GODBOSS - Intelligent Agricultural Assistant
Smart routing system that uses Gemini AI to analyze queries and route them to appropriate tools:
- Maps service for location-based queries
- FPO service for farmer producer organization queries  
- Weather service for weather-related queries
- RAG system for general agricultural advice
"""

import os
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import google.generativeai as genai
from Advisory.rag.retriever import get_retriever
import asyncio

class GODBOSS:
    """Intelligent Agricultural Assistant with smart tool routing"""
    
    def __init__(self):
        self.setup_gemini()
        self.conversation_history = []
        
    def setup_gemini(self):
        """Initialize Gemini AI"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("⚠️ No Gemini API key found. Please set GEMINI_API_KEY in .env file")
            
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            print("✅ Gemini AI initialized")
        except Exception as e:
            raise ValueError(f"⚠️ Gemini setup failed: {e}")
    
    def analyze_query_intent(self, query: str, history: List[Dict] = None) -> Dict[str, Any]:
        """Use Gemini to analyze query intent and determine which tools to use"""
        
        history_context = ""
        if history:
            history_context = "\n".join([
                f"User: {item.get('user', '')}\nAssistant: {item.get('assistant', '')}" 
                for item in history[-3:]  # Last 3 exchanges for context
            ])
        
        prompt = f"""
You are an intelligent agricultural assistant router. Analyze the user's query and conversation history to determine which tools/services should be used.

Conversation History:
{history_context}

Current User Query: "{query}"

Available Tools:
1. MAPS - For location-based queries (finding places, directions, geographical information)
2. FPO - For Farmer Producer Organization queries (finding FPOs, agricultural cooperatives, farmer groups)
3. WEATHER - For weather-related queries (current weather, forecasts, climate conditions)
4. RAG - For general agricultural advice (crop management, pest control, farming techniques, fertilizers)

Instructions:
- Analyze the query intent carefully
- Consider the conversation context
- You can select multiple tools if the query requires it
- Provide specific parameters for each selected tool
- If location is mentioned, extract it for maps/weather services

Respond in this exact JSON format:
{{
    "tools": [
        {{
            "name": "TOOL_NAME",
            "confidence": 0.95,
            "parameters": {{
                "key": "value"
            }},
            "reasoning": "Why this tool was selected"
        }}
    ],
    "primary_intent": "main intent of the query",
    "extracted_entities": {{
        "location": "location if mentioned",
        "crop": "crop if mentioned", 
        "weather_type": "weather aspect if mentioned",
        "organization_type": "FPO/cooperative if mentioned"
    }}
}}

Examples:
- "What's the weather in Punjab?" → WEATHER tool
- "Find FPOs near Delhi" → FPO + MAPS tools
- "How to control wheat rust?" → RAG tool
- "Weather forecast for my cotton farm in Maharashtra" → WEATHER + RAG tools
- "Directions to nearest agricultural cooperative" → MAPS + FPO tools
"""

        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text.strip())
            return result
        except Exception as e:
            print(f"⚠️ Intent analysis failed: {e}")
            # Fallback to RAG for general queries
            return {
                "tools": [{"name": "RAG", "confidence": 0.5, "parameters": {}, "reasoning": "Fallback due to analysis error"}],
                "primary_intent": "general agricultural query",
                "extracted_entities": {}
            }
    
    def call_maps_service(self, parameters: Dict) -> str:
        """Call maps service with parameters"""
        try:
            from maps.service import search_agri_shops
            
            location = parameters.get('location', parameters.get('query', ''))
            if not location:
                return "❌ No location specified for maps query"
            
            # For now, return a placeholder since we need coordinates for search_agri_shops
            # In a real implementation, you'd geocode the location first
            return f"📍 **Location Information:**\nSearching for agricultural facilities near {location}\n(Maps service integration pending - requires coordinates)"
            
        except Exception as e:
            return f"❌ Maps service error: {e}"
    
    def call_fpo_service(self, parameters: Dict) -> str:
        """Call FPO service with parameters"""
        try:
            from fpo.service import FPOService
            
            query = parameters.get('query', parameters.get('location', ''))
            if not query:
                return "❌ No search term specified for FPO query"
            
            # Create FPO service instance
            fpo_service = FPOService()
            
            # Search by state if it looks like a state name
            fpos = fpo_service.find_fpos_by_state(query)
            
            if not fpos:
                return f"❌ No FPOs found for query: {query}"
            
            # Format results
            result = f"Found {len(fpos)} FPOs:\n\n"
            for i, fpo in enumerate(fpos[:5], 1):  # Limit to 5 results
                result += f"**{i}.** {fpo.name}\n"
                result += f"   Location: {fpo.district}, {fpo.state}\n"
                if fpo.lat and fpo.lon:
                    result += f"   Coordinates: {fpo.lat:.4f}, {fpo.lon:.4f}\n"
                result += "\n"
            
            return f"🏢 **FPO Search Results:**\n{result}"
            
        except Exception as e:
            return f"❌ FPO service error: {e}"
    
    def call_weather_service(self, parameters: Dict) -> str:
        """Call weather service with parameters"""
        try:
            from weather.service import get_weather, generate_agricultural_advice
            
            location = parameters.get('location', parameters.get('query', ''))
            if not location:
                return "❌ No location specified for weather query"
            
            # Parse location (try to extract village and state)
            location_parts = location.split(',')
            if len(location_parts) >= 2:
                village = location_parts[0].strip()
                state = location_parts[1].strip()
            else:
                village = location.strip()
                state = "India"  # Default state
            
            # Use asyncio to run the async function
            async def get_weather_data():
                return await get_weather(village, state)
            
            weather_data = asyncio.run(get_weather_data())
            
            # Format weather information
            result = f"📍 **Location:** {weather_data.location_name}\n"
            result += f"🌡️ **Temperature:** {weather_data.temperature}°C"
            if weather_data.feels_like:
                result += f" (feels like {weather_data.feels_like}°C)"
            result += f"\n☁️ **Condition:** {weather_data.description}\n"
            
            if weather_data.humidity:
                result += f"💧 **Humidity:** {weather_data.humidity}%\n"
            if weather_data.wind_speed:
                result += f"🌬️ **Wind Speed:** {weather_data.wind_speed} m/s\n"
            if weather_data.precipitation_prob:
                result += f"🌧️ **Precipitation Probability:** {weather_data.precipitation_prob}%\n"
            
            # Add agricultural advice
            advice = generate_agricultural_advice(weather_data)
            if advice:
                result += f"\n🌾 **Agricultural Advice:**\n"
                for tip in advice:
                    result += f"• {tip}\n"
            
            return f"🌤️ **Weather Information:**\n{result}"
            
        except Exception as e:
            return f"❌ Weather service error: {e}"
    
    def call_rag_service(self, parameters: Dict) -> str:
        """Call RAG service with parameters"""
        try:
            query = parameters.get('query', '')
            if not query:
                return "❌ No query specified for RAG system"
            
            retriever = get_retriever()
            chunks = retriever.query(query, k=5, min_score=0.2)
            
            if not chunks:
                return "❌ No relevant agricultural information found in the database."
            
            response = "📚 **Agricultural Advisory:**\n\n"
            for i, chunk in enumerate(chunks, 1):
                response += f"**{i}.** {chunk['text']}\n\n"
            
            return response
        except Exception as e:
            return f"❌ RAG service error: {e}"
    
    def execute_tools(self, tools_config: List[Dict], query: str) -> str:
        """Execute the selected tools and combine results"""
        results = []
        
        for tool_config in tools_config:
            tool_name = tool_config.get('name', '').upper()
            parameters = tool_config.get('parameters', {})
            
            # Add original query to parameters if not present
            if 'query' not in parameters:
                parameters['query'] = query
            
            if tool_name == 'MAPS':
                result = self.call_maps_service(parameters)
            elif tool_name == 'FPO':
                result = self.call_fpo_service(parameters)
            elif tool_name == 'WEATHER':
                result = self.call_weather_service(parameters)
            elif tool_name == 'RAG':
                result = self.call_rag_service(parameters)
            else:
                result = f"❌ Unknown tool: {tool_name}"
            
            results.append(result)
        
        return "\n\n" + "="*60 + "\n\n".join(results)
    
    def process_query(self, query: str) -> str:
        """Main method to process user query with intelligent routing"""
        try:
            print("🧠 Analyzing query intent...")
            
            # Analyze intent using Gemini
            intent_analysis = self.analyze_query_intent(query, self.conversation_history)
            
            print(f"🎯 Primary intent: {intent_analysis.get('primary_intent', 'unknown')}")
            print(f"🔧 Selected tools: {[tool['name'] for tool in intent_analysis.get('tools', [])]}")
            
            # Execute selected tools
            tools_config = intent_analysis.get('tools', [])
            if not tools_config:
                return "❌ No appropriate tools identified for this query."
            
            result = self.execute_tools(tools_config, query)
            
            # Update conversation history
            self.conversation_history.append({
                'user': query,
                'assistant': result[:500] + "..." if len(result) > 500 else result,
                'tools_used': [tool['name'] for tool in tools_config],
                'intent': intent_analysis.get('primary_intent', 'unknown')
            })
            
            # Keep only last 10 exchanges
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            return result
            
        except Exception as e:
            return f"❌ Error processing query: {e}"
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation history"""
        if not self.conversation_history:
            return "No conversation history available."
        
        summary = "📖 **Conversation Summary:**\n\n"
        for i, exchange in enumerate(self.conversation_history[-5:], 1):
            summary += f"**{i}.** User: {exchange['user'][:100]}...\n"
            summary += f"    Tools: {', '.join(exchange.get('tools_used', []))}\n"
            summary += f"    Intent: {exchange.get('intent', 'unknown')}\n\n"
        
        return summary
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("✅ Conversation history cleared")

def main():
    """Main function for testing GODBOSS"""
    try:
        print("🚀 Starting GODBOSS - Intelligent Agricultural Assistant...")
        boss = GODBOSS()
        
        print("\n" + "="*80)
        print("🌾 GODBOSS - Your Intelligent Agricultural Assistant")
        print("="*80)
        print("\n🎯 I can help you with:")
        print("📍 Location & Maps - Find places, directions, geographical info")
        print("🏢 FPO Services - Find Farmer Producer Organizations") 
        print("🌤️ Weather - Current weather, forecasts, climate conditions")
        print("📚 Agricultural Advice - Crop management, pest control, farming techniques")
        print("\n💬 I remember our conversation and can handle complex multi-tool queries!")
        print("⌨️ Commands: 'history', 'clear', 'quit'")
        print("="*80)
        
        while True:
            try:
                user_input = input("\n🌾 You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n🌾 Happy farming! Goodbye! 🌾")
                    break
                elif user_input.lower() == 'history':
                    print(boss.get_conversation_summary())
                    continue
                elif user_input.lower() == 'clear':
                    boss.clear_history()
                    continue
                
                # Process the query
                response = boss.process_query(user_input)
                print(f"\n🤖 GODBOSS:")
                print("=" * 60)
                print(response)
                print("=" * 60)
                
            except KeyboardInterrupt:
                print("\n\n🌾 Thank you for using GODBOSS! Happy farming!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Startup error: {e}")

if __name__ == "__main__":
    main()
