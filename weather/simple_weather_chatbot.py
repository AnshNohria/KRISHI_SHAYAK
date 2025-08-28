#!/usr/bin/env python3
"""
🌤️ Simple Weather Chatbot
Direct access to weather services with AI query optimization and conversation history
"""

import asyncio
import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import google.generativeai as genai
from weather.service import get_weather, get_weather_forecast, generate_agricultural_advice

class SimpleWeatherBot:
    """Simple weather chatbot with AI optimization and conversation history - processes single input with history"""

    def __init__(self):
        self.setup_gemini()
        
    def setup_gemini(self):
        """Initialize Gemini AI for query optimization"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️  No Gemini API key found. Query optimization disabled.")
            self.model = None
            return
            
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            print("✅ Gemini AI initialized for query optimization")
        except Exception as e:
            print(f"⚠️  Gemini setup failed: {e}. Query optimization disabled.")
            self.model = None
    
    def parse_input(self, input_string: str) -> tuple:
        """Parse input string to extract conversation history and current query"""
        try:
            # Expect format: "HISTORY: <history> QUERY: <current_query>"
            if "HISTORY:" in input_string and "QUERY:" in input_string:
                parts = input_string.split("QUERY:")
                history_part = parts[0].replace("HISTORY:", "").strip()
                current_query = parts[1].strip()
                
                # Parse history (simple format: each exchange separated by newlines)
                conversation_history = []
                if history_part:
                    exchanges = history_part.split('\n')
                    for exchange in exchanges:
                        if exchange.strip():
                            conversation_history.append({'exchange': exchange.strip()})
                
                return conversation_history, current_query
            else:
                # If no specific format, treat entire input as current query
                return [], input_string.strip()
                
        except Exception as e:
            print(f"⚠️ Input parsing failed: {e}")
            return [], input_string.strip()
    
    def optimize_and_extract_location(self, user_query: str, conversation_history: List[Dict] = None) -> Dict[str, str]:
        """Use Gemini to optimize query and extract village/state in one API call"""
        if not self.model:
            # Fallback: simple parsing without AI
            return self._fallback_location_parsing(user_query)
            
        try:
            history_context = ""
            if conversation_history:
                history_context = "\n".join([
                    item.get('exchange', '') for item in conversation_history[-3:]  # Last 3 exchanges
                ])
            
            prompt = f"""
You are a weather location extraction expert for Indian agricultural applications. Extract village and state information from the user query.

Conversation History:
{history_context}

Current User Query: "{user_query}"

Instructions:
1. Extract the village/city/district name from the query
2. Extract the state name if mentioned
3. Use conversation history context if current query is ambiguous
4. Handle common Indian place name variations and spellings
5. Consider agricultural context if relevant
6. If state is not clear, use the most likely state for the village
7. Use LATEST information from query but consider context from history
8. Give response to tool in english
Respond ONLY in this exact JSON format:
{{
    "village": "extracted village/city name",
    "state": "extracted state name"
}}

Examples:
- "weather in pilani rajasthan" → {{"village": "Pilani", "state": "Rajasthan"}}
- "mumbai weather" → {{"village": "Mumbai", "state": "Maharashtra"}}
- "temperature in my village" + History: "...farming in Punjab..." → {{"village": "Punjab", "state": "Punjab"}}
- "how is it today?" + History: "...Delhi weather..." → {{"village": "Delhi", "state": "Delhi"}}
- "ludhiana" → {{"village": "Ludhiana", "state": "Punjab"}}
- "weather forecast" + History: "...Bangalore..." → {{"village": "Bangalore", "state": "Karnataka"}}
"""

            response = self.model.generate_content(prompt)
            result = response.text.strip()
            
            # Clean up response - remove markdown formatting if present
            if '```json' in result:
                result = result.split('```json')[1].split('```')[0].strip()
            elif '```' in result:
                result = result.split('```')[1].split('```')[0].strip()
            
            # Parse JSON response
            import json
            location_data = json.loads(result)
            
            village = location_data.get('village', '').strip()
            state = location_data.get('state', '').strip()
            
            # Basic validation
            if not village or len(village) < 2:
                return self._fallback_location_parsing(user_query)
            
            print(f"🔧 Location extracted: Village='{village}', State='{state}'")
            return {'village': village, 'state': state}
            
        except Exception as e:
            print(f"⚠️  AI location extraction failed: {e}")
            return self._fallback_location_parsing(user_query)
    
    def _fallback_location_parsing(self, query: str) -> Dict[str, str]:
        """Fallback location parsing without AI"""
        # Simple parsing logic
        query_clean = query.lower().replace('weather in', '').replace('weather', '').strip()
        
        location_parts = query_clean.split(',')
        if len(location_parts) >= 2:
            village = location_parts[0].strip()
            state = location_parts[1].strip()
        else:
            location_parts = query_clean.split()
            if len(location_parts) >= 2:
                village = location_parts[0]
                state = ' '.join(location_parts[1:])
            else:
                village = query_clean
                state = "India"  # Default
        
        return {'village': village, 'state': state}

    def get_forecast_response(self, query: str, conversation_history: List[Dict] = None, days: int = 5) -> str:
        """Get a multi-day weather forecast with AI-optimized location extraction"""
        try:
            location_data = self.optimize_and_extract_location(query, conversation_history)
            village = location_data['village']
            state = location_data['state']

            async def get_forecast_data():
                return await get_weather_forecast(village, state, days=days)

            forecast_data = asyncio.run(get_forecast_data())
            if not forecast_data:
                return "❌ Error retrieving weather forecast."

            result = f"📍 Location: {forecast_data['location']}\n"
            result += f"📅 5-Day Weather Forecast:\n"
            for day in forecast_data['forecast']:
                result += (f"{day['date']}: {day['description']}, "
                           f"Temp: {day['temp']}°C (min {day['tempmin']}°C, max {day['tempmax']}°C), "
                           f"Precip: {day['precip']}mm ({day['precipprob']}%), "
                           f"Humidity: {day['humidity']}%, "
                           f"Wind: {day['windspeed']} km/h\n")
            return result
        except Exception as e:
            return f"❌ Error retrieving weather forecast: {e}"
    def get_weather_response(self, query: str, conversation_history: List[Dict] = None, forecast: bool = False) -> str:
        """Get direct weather or forecast information with AI-optimized location extraction"""
        if forecast:
            return self.get_forecast_response(query, conversation_history, days=5)
        try:
            # Single AI call to extract village and state
            location_data = self.optimize_and_extract_location(query, conversation_history)
            village = location_data['village']
            state = location_data['state']
            
            # Use asyncio to run the async function
            async def get_weather_data():
                return await get_weather(village, state)
            
            weather_data = asyncio.run(get_weather_data())
            
            # Format weather information
            result = f"📍 Location: {weather_data.location_name}\n"
            result += f"🌡️ Temperature: {weather_data.temperature}°C"
            if weather_data.feels_like:
                result += f" (feels like {weather_data.feels_like}°C)"
            result += f"\n☁️ Condition: {weather_data.description}\n"
            
            if weather_data.humidity:
                result += f"💧 Humidity: {weather_data.humidity}%\n"
            if weather_data.wind_speed:
                result += f"🌬️ Wind Speed: {weather_data.wind_speed} m/s\n"
            if weather_data.precipitation_prob:
                result += f"🌧️ Precipitation Probability: {weather_data.precipitation_prob}%\n"
            if weather_data.pressure:
                result += f"🔄 Pressure: {weather_data.pressure} hPa\n"
            if weather_data.visibility:
                result += f"👁️ Visibility: {weather_data.visibility} km\n"
            if weather_data.uv_index:
                result += f"☀️ UV Index: {weather_data.uv_index}\n"
            if weather_data.cloud_cover:
                result += f"☁️ Cloud Cover: {weather_data.cloud_cover}%\n"
            
            # Add agricultural advice
            advice = generate_agricultural_advice(weather_data)
            if advice:
                result += f"\n🌾 Agricultural Advice:\n"
                for i, tip in enumerate(advice, 1):
                    result += f"{i}. {tip}\n"
            
            return result
            
        except Exception as e:
            return f"❌ Error retrieving weather information: {e}"

    def process_input(self, input_string: str) -> str:
        """Process input string containing history and query, return weather or forecast results"""
        print("🔍 Extracting location using AI optimization...")
        
        # Parse input to get history and current query
        conversation_history, current_query = self.parse_input(input_string)
        
        if conversation_history:
            print(f"📚 Using {len(conversation_history)} previous exchanges for context")

        # If the query contains 'forecast', return 5-day forecast, else current weather
        if 'forecast' in current_query.lower() or 'next 5 days' in current_query.lower() or '5-day' in current_query.lower():
            return self.get_weather_response(current_query, conversation_history, forecast=True)
        else:
            return self.get_weather_response(current_query, conversation_history, forecast=False)

    def process_query(self, query: str) -> str:
        """Legacy method for backward compatibility"""
        return self.process_input(query)

    def display_response(self, response: str):
        """Display formatted response"""
        print(f"\n🌤️ Weather Results:")
        print("-" * 60)
        print(response.strip())
        print("-" * 60)

    def run(self):
        """Main chatbot loop - answer only one query with conversation history"""
        try:
            print("\n✅ Weather Chatbot ready! Provide input with conversation history:")
            print("💡 Format: 'HISTORY: <previous exchanges> QUERY: <your weather question>'")
            print("💡 Or just: '<your weather question>' (no history)")
            print("💡 Examples:")
            print("   - 'HISTORY: User asked about Delhi yesterday QUERY: how is weather today?'")
            print("   - 'weather in Mumbai Maharashtra'")
            
            # Get single user input
            user_input = input("\n🌤️ You: ").strip()
            
            if user_input:
                # Process input with history and query
                response = self.process_input(user_input)
                self.display_response(response)
            
            print("\n🌤️ Thank you for using Weather chatbot!")
                
        except Exception as e:
            print(f"❌ Application error: {e}")

def main():
    """Main function"""
    try:
        print("🚀 Starting Simple Weather Chatbot...")
        bot = SimpleWeatherBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🌤️ Goodbye!")
    except Exception as e:
        print(f"❌ Startup error: {e}")

if __name__ == "__main__":
    main()
