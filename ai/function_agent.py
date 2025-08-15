"""
Gemini Function-Calling Agent: Uses Gemini's native function calling to directly route
queries to appropriate tools. Much cleaner than manual parsing!
"""
from __future__ import annotations
import os
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None

# Local tools
import weather.service as ws
from fpo.service import FPOService
from rag.retriever import get_retriever
from maps.service import search_kvk
from maps.dual_api_service import search_agri_shops_dual, geocode_dual_api


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    data: Any
    error: Optional[str] = None


class GeminiFunctionAgent:
    def __init__(self):
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not api_key or not genai:
            raise RuntimeError("GOOGLE_API_KEY is required and google-generativeai must be installed")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Initialize services
        self.rag = get_retriever()
        self.fpo_service = FPOService()
        
    async def get_weather(self, village: str, state: str) -> ToolResult:
        """Get weather information for a location."""
        try:
            weather_data = await ws.get_weather(village, state)
            advice = ws.generate_agricultural_advice(weather_data)
            
            result = {
                "location": f"{weather_data.location_name} ({weather_data.lat:.4f},{weather_data.lon:.4f})",
                "temperature": f"{weather_data.temperature:.1f}°C" if weather_data.temperature else None,
                "humidity": f"{weather_data.humidity:.0f}%" if weather_data.humidity else None,
                "wind": f"{weather_data.wind_speed:.1f} m/s" if weather_data.wind_speed else None,
                "rain_chance": f"{weather_data.precipitation_prob:.0f}%" if weather_data.precipitation_prob else None,
                "advice": advice,
                "sources": weather_data.data_sources
            }
            return ToolResult("get_weather", True, result)
        except Exception as e:
            return ToolResult("get_weather", False, None, str(e))

    async def search_krishi_vigyan_kendra(self, village: str, state: str) -> ToolResult:
        """Search for Krishi Vigyan Kendra near a location."""
        try:
            # Geocode location first
            geo = await ws.geocode_openweather(village, state) or await ws.geocode_visual_crossing(village, state)
            if not geo:
                return ToolResult("search_krishi_vigyan_kendra", False, None, f"Could not find location: {village}, {state}")
                
            api_key = os.getenv('GEOAPIFY_API_KEY')
            if not api_key:
                return ToolResult("search_krishi_vigyan_kendra", False, None, "GEOAPIFY_API_KEY not configured")
                
            results, used_radius = await search_kvk(geo['lat'], geo['lon'], api_key)
            
            # Filter results to only include actual KVKs
            filtered_results = []
            for result in results:
                name = result.get('name', '').lower()
                address = result.get('address', '').lower()
                
                # Check if it's actually a KVK
                if any(term in name for term in ['krishi vigyan kendra', 'kvk', 'agricultural', 'farm', 'rural']):
                    filtered_results.append(result)
                elif any(term in address for term in ['krishi vigyan kendra', 'kvk']):
                    filtered_results.append(result)
                # Exclude obvious non-KVK institutions
                elif any(term in name for term in ['school', 'college', 'university', 'hospital', 'bank']):
                    continue
                else:
                    # If name contains "krishi" or is explicitly named "Krishi Vigyan Kendra", include it
                    if 'krishi' in name or name.strip() == 'krishi vigyan kendra':
                        filtered_results.append(result)
            
            if not filtered_results:
                km = int(round(used_radius/1000))
                return ToolResult("search_krishi_vigyan_kendra", True, {
                    "kvks": [],
                    "message": f"No actual Krishi Vigyan Kendra found within {km} km of {village}, {state}. Found {len(results)} educational institutions, but none appear to be KVKs.",
                    "radius_km": km,
                    "suggestions": "Try searching for the nearest agricultural university or contact local agricultural department for KVK information."
                })
                
            return ToolResult("search_krishi_vigyan_kendra", True, {
                "kvks": filtered_results,
                "location": f"{village}, {state}",
                "radius_km": int(round(used_radius/1000)),
                "total_found": len(results),
                "actual_kvks": len(filtered_results)
            })
            
        except Exception as e:
            return ToolResult("search_krishi_vigyan_kendra", False, None, str(e))

    async def search_agricultural_shops(self, shop_type: str, village: str, state: str) -> ToolResult:
        """Search for agricultural shops."""
        try:
            # Use dual API geocoding
            result = await geocode_dual_api(f"{village}, {state}")
            if not result:
                return ToolResult("search_agricultural_shops", False, None, f"Could not find location: {village}, {state}")
                
            # Map shop type to search terms
            shop_keywords = {
                "fertilizer": "fertilizer shop",
                "seed": "seed shop", 
                "pesticide": "pesticide shop",
                "tractor": "tractor dealer",
                "equipment": "farm machinery"
            }
            keyword = shop_keywords.get(shop_type, shop_type)
            
            # Search using dual maps API
            results = await search_agri_shops_dual(keyword, result.lat, result.lon)
            
            if not results:
                return ToolResult("search_agricultural_shops", True, {
                    "shops": [],
                    "message": f"No {keyword} found near {village}, {state}",
                    "type": keyword
                })
                
            shops = []
            for shop in results[:5]:
                shops.append({
                    "name": shop['name'],
                    "address": shop.get('address', ''),
                    "distance_km": shop.get('distance_km', ''),
                    "maps_url": shop.get('maps_url', ''),
                    "source": shop.get('source', 'dual_api')
                })
                
            return ToolResult("search_agricultural_shops", True, {
                "shops": shops,
                "type": keyword,
                "location": f"{village}, {state}"
            })
            
        except Exception as e:
            return ToolResult("search_agricultural_shops", False, None, str(e))

    async def search_fpo(self, state: str) -> ToolResult:
        """Search for FPOs in a state."""
        try:
            state_fpos = self.fpo_service.get_fpos_by_state(state)
            fpos = []
            
            for fpo in state_fpos:
                fpos.append({
                    "name": fpo.name,
                    "district": fpo.district,
                    "state": fpo.state,
                    "coordinates": f"({fpo.lat:.4f}, {fpo.lon:.4f})" if (fpo.lat != 0.0 or fpo.lon != 0.0) else "N/A"
                })
                
            if not fpos:
                return ToolResult("search_fpo", True, {
                    "fpos": [],
                    "message": f"No FPO data available for {state}. Database contains {self.fpo_service.total_fpos()} FPOs total.",
                    "type": "state_search",
                    "data_source": "json_loaded" if self.fpo_service.json_source_loaded() else "sample_data"
                })
                
            return ToolResult("search_fpo", True, {
                "fpos": fpos, 
                "type": "state", 
                "state": state,
                "total_in_state": len(state_fpos),
                "data_source": "json_loaded" if self.fpo_service.json_source_loaded() else "sample_data"
            })
            
        except Exception as e:
            return ToolResult("search_fpo", False, None, str(e))

    async def get_agricultural_advice(self, query: str) -> ToolResult:
        """Get agricultural advice from RAG system."""
        try:
            docs = self.rag.query(query, k=5)
            if not docs:
                return ToolResult("get_agricultural_advice", True, {
                    "advice": [],
                    "message": "No specific advisory found for your query"
                })
                
            advice = []
            for doc in docs:
                advice.append({
                    "title": doc.get('heading') or doc.get('source') or 'Agricultural Advisory',
                    "content": doc['text'][:500] + "..." if len(doc['text']) > 500 else doc['text'],
                    "source": doc.get('source', 'ICAR Guidelines')
                })
                
            return ToolResult("get_agricultural_advice", True, {"advice": advice})
            
        except Exception as e:
            return ToolResult("get_agricultural_advice", False, None, str(e))

    async def process_query(self, query: str) -> str:
        """Process user query by having Gemini decide which tools to use."""
        try:
            # Let Gemini analyze the query and decide which functions to call
            analysis_prompt = f"""You are Krishi Dhan Sahayak, an intelligent agricultural assistant.
Analyze the user's query and respond with a JSON object indicating which function(s) to call:

Available functions:
1. get_weather(village, state) - for weather information
2. search_krishi_vigyan_kendra(village, state) - for KVK/agricultural center searches
3. search_agricultural_shops(shop_type, village, state) - for fertilizer/seed/pesticide shop searches
4. search_fpo(state) - for Farmer Producer Organization searches
5. get_agricultural_advice(query) - for farming advice and guidance

User query: "{query}"

Respond with JSON in this format:
{{
  "functions_to_call": [
    {{"name": "function_name", "args": {{"param1": "value1", "param2": "value2"}}}}
  ],
  "reasoning": "why these functions were chosen"
}}

Only include functions that are relevant to the user's specific query."""

            response = self.model.generate_content(analysis_prompt)
            analysis_text = getattr(response, 'text', '')
            
            # Parse the JSON response
            try:
                # Extract JSON from response
                start = analysis_text.find('{')
                end = analysis_text.rfind('}') + 1
                json_text = analysis_text[start:end]
                analysis = json.loads(json_text)
                
                functions_to_call = analysis.get('functions_to_call', [])
                print(f"🔍 Gemini decided to call: {[f['name'] for f in functions_to_call]}")
                
            except Exception as e:
                print(f"⚠️  Failed to parse Gemini analysis: {e}")
                # Fallback: simple keyword-based routing
                functions_to_call = self._fallback_function_selection(query)
            
            # Execute the selected functions
            tool_results = []
            for func_call in functions_to_call:
                func_name = func_call['name']
                func_args = func_call['args']
                
                if hasattr(self, func_name):
                    try:
                        result = await getattr(self, func_name)(**func_args)
                        tool_results.append(result)
                        print(f"✅ Executed {func_name}: {'Success' if result.success else 'Failed'}")
                    except Exception as e:
                        print(f"❌ Error executing {func_name}: {e}")
            
            # If no functions were called successfully, provide general advice
            if not tool_results:
                result = await self.get_agricultural_advice(query)
                tool_results.append(result)
            
            # Compose final response
            return await self._compose_final_response(query, tool_results)
            
        except Exception as e:
            return f"I encountered an error while processing your request: {str(e)}"
    
    def _fallback_function_selection(self, query: str) -> List[Dict]:
        """Fallback function selection using simple keyword matching."""
        query_lower = query.lower()
        functions = []
        
        # Extract location if present
        words = query_lower.split()
        village = None
        state = None
        
        # Simple location extraction
        if 'bihar' in query_lower:
            state = 'Bihar'
        if 'patna' in query_lower:
            village = 'Patna'
        
        # Function selection based on keywords
        if any(word in query_lower for word in ['kvk', 'krishi vigyan kendra', 'agricultural center']):
            if village and state:
                functions.append({
                    "name": "search_krishi_vigyan_kendra",
                    "args": {"village": village, "state": state}
                })
        
        elif any(word in query_lower for word in ['weather', 'temperature', 'rain']):
            if village and state:
                functions.append({
                    "name": "get_weather", 
                    "args": {"village": village, "state": state}
                })
        
        elif any(word in query_lower for word in ['shop', 'fertilizer', 'seed', 'pesticide']):
            shop_type = 'fertilizer'  # default
            if 'seed' in query_lower:
                shop_type = 'seed'
            elif 'pesticide' in query_lower:
                shop_type = 'pesticide'
            
            if village and state:
                functions.append({
                    "name": "search_agricultural_shops",
                    "args": {"shop_type": shop_type, "village": village, "state": state}
                })
        
        elif 'fpo' in query_lower or 'farmer producer' in query_lower:
            if state:
                functions.append({
                    "name": "search_fpo",
                    "args": {"state": state}
                })
        
        # Default to agricultural advice if no specific function matches
        if not functions:
            functions.append({
                "name": "get_agricultural_advice",
                "args": {"query": query}
            })
        
        return functions

    async def _compose_final_response(self, query: str, tool_results: List[ToolResult]) -> str:
        """Let Gemini compose a natural response from tool results."""
        
        # Build context from tool results
        context_parts = []
        for result in tool_results:
            if result.success and result.data:
                context_parts.append(f"Tool: {result.tool_name}\nResult: {json.dumps(result.data, indent=2)}")
            elif not result.success:
                context_parts.append(f"Tool: {result.tool_name}\nError: {result.error}")
                
        if not context_parts:
            return "I don't have enough information to answer your question. Please provide more details."
            
        context = "\n\n".join(context_parts)
        
        prompt = f"""You are Krishi Dhan Sahayak, a helpful agricultural assistant. Based on the tool results below, 
        provide a natural, conversational response to the user's question. Be specific, helpful, and farmer-friendly.

User Question: {query}

Tool Results:
{context}

Please provide a comprehensive, helpful response based on this information."""

        try:
            response = self.model.generate_content(prompt)
            return getattr(response, 'text', 'I apologize, but I cannot generate a response right now.')
        except Exception:
            # Fallback response
            if tool_results and tool_results[0].success:
                data = tool_results[0].data
                if isinstance(data, dict):
                    if 'kvks' in data:
                        kvks = data['kvks']
                        if kvks:
                            response = f"I found {len(kvks)} Krishi Vigyan Kendra(s) near your location:\n\n"
                            for i, kvk in enumerate(kvks, 1):
                                response += f"{i}. **{kvk['name']}**\n"
                                response += f"   📍 Address: {kvk['address']}\n"
                                response += f"   📏 Distance: {kvk['distance_km']:.2f} km\n\n"
                            return response
                        else:
                            return data.get('message', 'No results found.')
            
            return "I found some information but couldn't format it properly. Please try asking again."


# For backward compatibility
GeminiToolAgent = GeminiFunctionAgent
