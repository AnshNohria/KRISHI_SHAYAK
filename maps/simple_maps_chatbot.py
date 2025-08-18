#!/usr/bin/env python3
"""
📍 Simple Maps Chatbot
Direct access to maps/location services with AI optimization for better location extraction
"""

import asyncio
import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import google.generativeai as genai
# from service import search_agri_shops, search_kvk

class SimpleMapsBot:
    """Simple maps chatbot with AI optimization for location extraction - processes single input with history"""

    def __init__(self):
        self.api_key = os.getenv('GEOAPIFY_API_KEY', '')
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
            print("✅ Gemini AI initialized for maps search optimization")
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
    
    def optimize_and_extract_location_intent(self, user_query: str, conversation_history: List[Dict] = None) -> Dict[str, str]:
        """Use Gemini to optimize query and extract location/service intent in one API call"""
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
You are a maps/location service optimization expert for Indian agricultural applications. Extract location and service intent from user queries.

Conversation History:
{history_context}

Current User Query: "{user_query}"

Instructions:
1. Extract the location (city/village/district/state) from the query
2. Identify the service type: "kvk", "agri_shop", "general_info"
3. Use conversation history context if current query is ambiguous
4. Handle common Indian place name variations
5. Consider agricultural facility keywords (KVK, shops, stores, etc.)
6. Use LATEST information from query but consider context from history

Respond ONLY in this exact JSON format:
{{
    "location": "extracted location",
    "service_type": "kvk|agri_shop|general_info",
    "confidence": "high|medium|low"
}}

Examples:
- "KVK near Delhi" → {{"location": "Delhi", "service_type": "kvk", "confidence": "high"}}
- "agricultural shops in Punjab" → {{"location": "Punjab", "service_type": "agri_shop", "confidence": "high"}}
- "find fertilizer stores ludhiana" → {{"location": "Ludhiana", "service_type": "agri_shop", "confidence": "high"}}
- "where are facilities?" + History: "...Mumbai farming..." → {{"location": "Mumbai", "service_type": "general_info", "confidence": "high"}}
- "locations there" + History: "...KVK in Karnataka..." → {{"location": "Karnataka", "service_type": "kvk", "confidence": "high"}}
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
            
            location = location_data.get('location', '').strip()
            service_type = location_data.get('service_type', 'general_info').strip()
            confidence = location_data.get('confidence', 'medium').strip()
            
            # Basic validation
            if not location or len(location) < 2:
                return self._fallback_location_parsing(user_query)
            
            print(f"🔧 Location intent extracted: Location='{location}', Service='{service_type}', Confidence='{confidence}'")
            return {'location': location, 'service_type': service_type, 'confidence': confidence}
            
        except Exception as e:
            print(f"⚠️  AI location extraction failed: {e}")
            return self._fallback_location_parsing(user_query)
    
    def _fallback_location_parsing(self, query: str) -> Dict[str, str]:
        """Fallback location parsing without AI"""
        query_lower = query.lower()
        
        # Simple keyword detection
        if 'kvk' in query_lower or 'krishi vigyan' in query_lower:
            service_type = 'kvk'
        elif any(keyword in query_lower for keyword in ['shop', 'store', 'fertilizer', 'seed', 'pesticide']):
            service_type = 'agri_shop'
        else:
            service_type = 'general_info'
        
        # Extract location (simple approach)
        location = query.replace('KVK', '').replace('shop', '').replace('store', '').strip()
        if len(location) < 2:
            location = "India"
        
        return {'location': location, 'service_type': service_type, 'confidence': 'low'}

    def get_maps_response(self, query: str, conversation_history: List[Dict] = None) -> str:
        """Get direct maps/location information with AI-optimized location extraction"""
        try:
            # Single AI call to extract location and service intent
            location_data = self.optimize_and_extract_location_intent(query, conversation_history)
            location = location_data['location']
            service_type = location_data['service_type']
            confidence = location_data['confidence']
            
            if not self.api_key:
                return (f"❌ Maps service requires GEOAPIFY_API_KEY in .env file\n\n"
                       f"Extracted intent: Location='{location}', Service='{service_type}'\n\n"
                       f"Available services:\n"
                       f"• Agricultural shops search\n"
                       f"• Krishi Vigyan Kendra (KVK) search\n"
                       f"• Location-based facility finder")
            
            # Provide service-specific information based on AI extraction
            if service_type == 'kvk':
                return self._provide_kvk_info(location)
            elif service_type == 'agri_shop':
                return self._provide_agri_shop_info(location)
            else:
                return self._provide_general_maps_info(location, query)
                
        except Exception as e:
            return f"❌ Error retrieving maps information: {e}"

    def _provide_kvk_info(self, location: str) -> str:
        """Provide actual KVK search results"""
        if not self.api_key:
            return (f"❌ Maps service requires GEOAPIFY_API_KEY in .env file\n\n"
                   f"To search for KVKs near '{location}'")
        
        try:
            # Use geocoding to get coordinates for the location
            from dual_api_service import geocode_dual_api
            from service import search_kvk
            import asyncio
            
            # Get coordinates for the location
            print(f"🌍 Geocoding location: {location}")
            geocode_result = asyncio.run(geocode_dual_api(location))
            
            if not geocode_result:
                return (f"❌ Could not find coordinates for '{location}'\n\n"
                       f"Please try a more specific location like 'Jaipur, Rajasthan' or 'Mumbai, Maharashtra'")
            
            # Use the geocoding result
            lat, lon = geocode_result.lat, geocode_result.lon
            print(f"📍 Found coordinates: {lat}, {lon} for {geocode_result.display_name}")
            
            # Search for KVKs
            print(f"🔍 Searching for Krishi Vigyan Kendras near {location}...")
            kvk_results = asyncio.run(search_kvk(
                lat, lon, self.api_key, 
                radius_m=50000, limit=5  # Start with 50km for KVKs
            ))
            
            if not kvk_results:
                # Try with broader search
                kvk_results = asyncio.run(search_kvk(
                    lat, lon, self.api_key, 
                    radius_m=200000, limit=8  # Expand to 200km for KVKs
                ))
            
            if not kvk_results:
                return (f"🏫 Krishi Vigyan Kendra Search for '{location}'\n\n"
                       f"📍 Location: {geocode_result.display_name}\n"
                       f"🔍 No KVKs found within 200km radius.\n\n"
                       f"**What KVKs provide:**\n"
                       f"• Agricultural technology demonstrations\n"
                       f"• Farmer training programs\n"
                       f"• Crop advisory services\n"
                       f"• Soil testing facilities\n\n"
                       f"**Suggestions:**\n"
                       f"• Contact your district agriculture office\n"
                       f"• Try searching in the nearest major district\n"
                       f"• Visit the official ICAR-KVK website for directory")
            
            # Format the results
            response = f"🏫 Krishi Vigyan Kendras near '{location}'\n\n"
            response += f"📍 Search center: {geocode_result.display_name}\n"
            response += f"🔍 Found {len(kvk_results)} KVK facilities:\n\n"
            
            for i, kvk in enumerate(kvk_results, 1):
                name = kvk.get('name', 'Unknown KVK')
                address = kvk.get('address', 'Address not available')
                distance = kvk.get('distance_km', 0)
                
                response += f"**{i}. {name}**\n"
                response += f"   📍 {address}\n"
                if distance > 0:
                    response += f"   🚗 {distance:.1f} km away\n"
                
                # Add maps link if available
                maps_url = kvk.get('maps_url')
                if maps_url:
                    response += f"   🗺️ [View on Map]({maps_url})\n"
                response += "\n"
            
            response += f"🌾 **KVK Services Available:**\n"
            response += f"• Technology demonstrations and training\n"
            response += f"• Soil and water testing\n"
            response += f"• Crop advisory and extension services\n"
            response += f"• Livestock and dairy guidance\n"
            response += f"• Agricultural machinery rental\n\n"
            response += f"💡 **Visit Tips:** Contact in advance to know about ongoing programs and training schedules.\n"
            
            return response
            
        except Exception as e:
            print(f"❌ Error searching KVKs: {e}")
            return (f"❌ Error searching for KVKs near '{location}': {e}\n\n"
                   f"Please try again with a different location or check your internet connection.")

    def _provide_agri_shop_info(self, location: str) -> str:
        """Provide actual agricultural shop search results"""
        if not self.api_key:
            return (f"❌ Maps service requires GEOAPIFY_API_KEY in .env file\n\n"
                   f"To search for agricultural shops near '{location}'")
        
        try:
            # Use geocoding to get coordinates for the location
            from dual_api_service import geocode_location, search_shops_near_location
            import asyncio
            
            # Get coordinates for the location
            print(f"� Geocoding location: {location}")
            geocode_results = asyncio.run(geocode_location(location))
            
            if not geocode_results:
                return (f"❌ Could not find coordinates for '{location}'\n\n"
                       f"Please try a more specific location like 'Ludhiana, Punjab' or 'Delhi'")
            
            # Use the first geocoding result
            place = geocode_results[0]
            lat, lon = place['lat'], place['lon']
            print(f"📍 Found coordinates: {lat}, {lon} for {place.get('formatted', location)}")
            
            # Search for agricultural shops
            print(f"🔍 Searching for agricultural shops near {location}...")
            shop_results = asyncio.run(search_shops_near_location(
                "fertilizer shop", lat, lon, self.api_key, 
                radius_m=15000, max_results=8
            ))
            
            if not shop_results:
                # Try with broader search
                shop_results = asyncio.run(search_shops_near_location(
                    "agriculture shop", lat, lon, self.api_key, 
                    radius_m=50000, max_results=8
                ))
            
            if not shop_results:
                return (f"🏪 Agricultural Shops Search for '{location}'\n\n"
                       f"📍 Location: {place.get('formatted', location)}\n"
                       f"🔍 No agricultural shops found within 50km radius.\n\n"
                       f"Suggestions:\n"
                       f"• Try a different nearby city/town\n"
                       f"• Check if the location name is spelled correctly\n"
                       f"• Agricultural shops might be listed under general 'shops' in rural areas")
            
            # Format the results
            response = f"🏪 Agricultural Shops near '{location}'\n\n"
            response += f"📍 Search center: {place.get('formatted', location)}\n"
            response += f"🔍 Found {len(shop_results)} agricultural facilities:\n\n"
            
            for i, shop in enumerate(shop_results, 1):
                name = shop.get('name', 'Unknown Shop')
                address = shop.get('address', 'Address not available')
                distance = shop.get('distance_km', 0)
                
                response += f"**{i}. {name}**\n"
                response += f"   📍 {address}\n"
                if distance > 0:
                    response += f"   🚗 {distance:.1f} km away\n"
                
                # Add maps link if available
                maps_url = shop.get('maps_url')
                if maps_url:
                    response += f"   🗺️ [View on Map]({maps_url})\n"
                response += "\n"
            
            response += f"💡 **Tips:**\n"
            response += f"• Call ahead to confirm shop timings and stock\n"
            response += f"• Carry proper identification for fertilizer purchases\n"
            response += f"• Ask about seasonal agricultural advice\n"
            
            return response
            
        except Exception as e:
            print(f"❌ Error searching shops: {e}")
            return (f"❌ Error searching for shops near '{location}': {e}\n\n"
                   f"Please try again with a different location or check your internet connection.")

    def _provide_general_maps_info(self, location: str, original_query: str) -> str:
        """Provide general maps information"""
        return (f"📍 Maps Service Information for '{location}'\n\n"
               f"Original query: {original_query}\n\n"
               f"Available location services:\n"
               f"• 🏪 Agricultural shops and stores\n"
               f"• 🏫 Krishi Vigyan Kendras (KVKs)\n"
               f"• 📍 Location-based facility search\n"
               f"• 🗺️ Geographic information\n\n"
               f"For better results, specify:\n"
               f"• Clear location (city, district, state)\n"
               f"• Type of facility you're looking for\n\n"
               f"Examples:\n"
               f"• 'KVK near {location}'\n"
               f"• 'Agricultural shops in {location}'\n"
               f"• 'Fertilizer stores near {location}'")

    def process_input(self, input_string: str) -> str:
        """Process input string containing history and query, return maps results"""
        print("🔍 Extracting location and service intent using AI optimization...")
        
        # Parse input to get history and current query
        conversation_history, current_query = self.parse_input(input_string)
        
        if conversation_history:
            print(f"📚 Using {len(conversation_history)} previous exchanges for context")
        
        # Get maps response with context (single AI call for location/intent extraction)
        return self.get_maps_response(current_query, conversation_history)

    def process_query(self, query: str) -> str:
        """Legacy method for backward compatibility"""
        return self.process_input(query)

    def display_response(self, response: str):
        """Display formatted response"""
        print(f"\n📍 Maps Results:")
        print("-" * 60)
        print(response.strip())
        print("-" * 60)

    def run(self):
        """Main chatbot loop - answer only one query with conversation history"""
        try:
            print("\n✅ Maps Chatbot ready! Provide input with conversation history:")
            print("💡 Format: 'HISTORY: <previous exchanges> QUERY: <your maps question>'")
            print("💡 Or just: '<your maps question>' (no history)")
            print("💡 Examples:")
            print("   - 'HISTORY: User discussed farming in Delhi QUERY: find KVK there'")
            print("   - 'KVK near Mumbai'")
            print("   - 'agricultural shops in Punjab'")
            print("   - 'fertilizer stores ludhiana'")
            
            # Get single user input
            user_input = input("\n📍 You: ").strip()
            
            if user_input:
                # Process input with history and query
                response = self.process_input(user_input)
                self.display_response(response)
            
            print("\n📍 Thank you for using Maps chatbot!")
                
        except Exception as e:
            print(f"❌ Application error: {e}")

def main():
    """Main function"""
    try:
        print("🚀 Starting Simple Maps Chatbot...")
        bot = SimpleMapsBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n📍 Goodbye!")
    except Exception as e:
        print(f"❌ Startup error: {e}")

if __name__ == "__main__":
    main()
