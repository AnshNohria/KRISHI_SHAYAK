"""
Gemini Tool-Calling Agent: Uses Gemini to intelligently route queries to appropriate tools
(weather, maps, FPO, RAG) and compose responses. Gemini acts as the orchestrator that
decides which tools to call based on user intent and composes the final response.

Activation: set GEMINI_API_KEY in environment. This is now required for proper operation.
"""
from __future__ import annotations
import os
import glob
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None  # Optional dependency

from sentence_transformers import SentenceTransformer

# Local tools
import weather.service as ws
from fpo.service import FPOService
from rag.retriever import get_retriever
from maps.dual_api_service import search_agri_shops_dual, geocode_dual_api


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    data: Any
    error: Optional[str] = None


class GeminiToolAgent:
    def __init__(self):
        # Check for both GOOGLE_API_KEY (new) and GEMINI_API_KEY (old) for compatibility
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.enabled = bool(api_key) and genai is not None
        if not self.enabled:
            raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY is required for the tool-calling agent")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.rag = get_retriever()
        
    def _extract_intent_and_location(self, query: str) -> Dict[str, Any]:
        """Use Gemini to extract intent and location from any free-form query."""
        schema_prompt = """
Extract information from the user query and respond with JSON only:
{
  "intent": "weather|shop|kvk|fpo|advisory|other",
  "location": {
    "village": "village name or null", 
    "state": "state name or null"
  },
  "shop_type": "fertilizer|seed|pesticide|tractor|equipment or null",
  "needs_weather": true/false,
  "needs_location": true/false
}

Intent meanings:
- weather: user wants weather information
- shop: user wants to find agricultural shops (fertilizer, seed, pesticide, tractor dealers)
- kvk: user wants KVK (Krishi Vigyan Kendra) information
- fpo: user wants FPO (Farmer Producer Organization) information  
- advisory: user wants farming advice/guidance
- other: general agricultural questions

User query: """ + query

        try:
            response = self.model.generate_content(schema_prompt)
            text = getattr(response, 'text', '') or ''
            text = text.strip().strip('`json').strip('`')
            
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                text = text[start:end+1]
                
            return json.loads(text)
        except Exception:
            return {
                "intent": "other",
                "location": {"village": None, "state": None},
                "shop_type": None,
                "needs_weather": False,
                "needs_location": False
            }

    async def _execute_get_weather(self, village: str, state: str) -> ToolResult:
        """Execute weather tool."""
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

    async def _execute_search_shops(self, shop_type: str, village: str, state: str) -> ToolResult:
        """Execute shop search tool using dual maps API."""
        try:
            # Use dual API geocoding
            result = await geocode_dual_api(f"{village}, {state}")
            if not result:
                return ToolResult("search_shops", False, None, f"Could not find location: {village}, {state}")
                
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
                return ToolResult("search_shops", True, {
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
                
            return ToolResult("search_shops", True, {
                "shops": shops,
                "count": len(results),
                "type": keyword
            })
        except Exception as e:
            return ToolResult("search_shops", False, None, str(e))

    async def _execute_search_kvk(self, village: str, state: str) -> ToolResult:
        """Execute KVK search tool."""
        try:
            # Geocode location first
            geo = await ws.geocode_openweather(village, state) or await ws.geocode_visual_crossing(village, state)
            if not geo:
                return ToolResult("search_kvk", False, None, f"Could not find location: {village}, {state}")
                
            key = os.getenv('GEOAPIFY_API_KEY')
            if not key:
                return ToolResult("search_kvk", False, None, "GEOAPIFY_API_KEY not configured")
                
            from maps.service import search_kvk
            results, used_radius = await search_kvk(geo['lat'], geo['lon'], key)
            
            if not results:
                km = int(round(used_radius/1000))
                return ToolResult("search_kvk", True, {
                    "kvks": [],
                    "message": f"No KVK found within {km} km of {village}, {state}",
                    "radius_km": km
                })
                
            kvks = []
            for kvk in results[:5]:
                kvks.append({
                    "name": kvk['name'],
                    "address": kvk.get('address', ''),
                    "distance_km": kvk.get('distance_km', ''),
                    "maps_url": kvk.get('maps_url', '')
                })
                
            return ToolResult("search_kvk", True, {
                "kvks": kvks,
                "count": len(results)
            })
        except Exception as e:
            return ToolResult("search_kvk", False, None, str(e))

    async def _execute_search_fpo(self, village: Optional[str], state: str) -> ToolResult:
        """Execute FPO search tool with finalized enhanced logic."""
        try:
            svc = FPOService()
            
            if village:
                # Use the finalized nearest FPO logic with geocoding
                nearest_fpos = await svc.find_nearest_fpos_with_geocoding(village, state, limit=5)
                
                if nearest_fpos:
                    fpos = []
                    for fpo, distance in nearest_fpos:
                        fpos.append({
                            "name": fpo.name,
                            "district": fpo.district,
                            "state": fpo.state,
                            "distance_km": f"{distance:.1f}",
                            "coordinates": f"({fpo.lat:.4f}, {fpo.lon:.4f})" if (fpo.lat != 0.0 or fpo.lon != 0.0) else "N/A",
                            "geocoding_source": "dual_maps_api"
                        })
                    
                    return ToolResult("search_fpo", True, {
                        "fpos": fpos, 
                        "type": "nearest", 
                        "location": f"{village}, {state}",
                        "total_found": len(fpos),
                        "search_method": "enhanced_geocoding_with_distance_calculation"
                    })
            
            # Fallback: Find FPOs by state using the service method
            state_fpos = svc.find_fpos_by_state(state)[:5]
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
                    "message": f"No FPO data available for {state}. Database contains {svc.total_fpos()} FPOs total.",
                    "type": "state_search",
                    "data_source": "json_loaded" if svc.json_source_loaded() else "sample_data"
                })
                
            return ToolResult("search_fpo", True, {
                "fpos": fpos, 
                "type": "state", 
                "state": state,
                "total_in_state": len(state_fpos),
                "data_source": "json_loaded" if svc.json_source_loaded() else "sample_data"
            })
            
        except Exception as e:
            return ToolResult("search_fpo", False, None, str(e))

    def _execute_get_advisory(self, query: str) -> ToolResult:
        """Execute RAG-based advisory tool."""
        try:
            docs = self.rag.query(query, k=5)
            if not docs:
                return ToolResult("get_advisory", True, {
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
                
            return ToolResult("get_advisory", True, {"advice": advice})
            
        except Exception as e:
            return ToolResult("get_advisory", False, None, str(e))

    async def run(self, query: str, village: Optional[str] = None, state: Optional[str] = None) -> str:
        """Main entry point - analyze query and execute appropriate tools."""
        
        # Extract intent and location using Gemini
        parsed = self._extract_intent_and_location(query)
        
        # Override with provided location if available
        location_village = parsed.get("location", {}).get("village") or village
        location_state = parsed.get("location", {}).get("state") or state
        intent = parsed.get("intent", "other")
        shop_type = parsed.get("shop_type")
        
        # Execute appropriate tools based on intent
        tool_results = []
        
        try:
            if intent == "weather" and location_village and location_state:
                result = await self._execute_get_weather(location_village, location_state)
                tool_results.append(result)
                
            elif intent == "shop" and location_village and location_state and shop_type:
                result = await self._execute_search_shops(shop_type, location_village, location_state)
                tool_results.append(result)
                
            elif intent == "kvk" and location_village and location_state:
                result = await self._execute_search_kvk(location_village, location_state)
                tool_results.append(result)
                
            elif intent == "fpo" and location_state:
                result = await self._execute_search_fpo(location_village, location_state)
                tool_results.append(result)
                
            elif intent == "advisory":
                result = self._execute_get_advisory(query)
                tool_results.append(result)
                
            else:
                # Default: try to get advisory for any agricultural query
                result = self._execute_get_advisory(query)
                tool_results.append(result)
                
        except Exception as e:
            return f"Error processing your request: {str(e)}"
            
        # Use Gemini to compose final response from tool results
        return self._compose_response(query, tool_results, parsed)
        
    def _compose_response(self, query: str, tool_results: List[ToolResult], parsed: Dict) -> str:
        """Use Gemini to compose a natural response from tool results."""
        
        # Build context from tool results
        context_parts = []
        for result in tool_results:
            if result.success and result.data:
                context_parts.append(f"Tool: {result.tool_name}\nResult: {json.dumps(result.data, indent=2)}")
            elif not result.success:
                context_parts.append(f"Tool: {result.tool_name}\nError: {result.error}")
                
        if not context_parts:
            return "I don't have enough information to answer your question. Please provide more details about your location or specify what you're looking for."
            
        context = "\n\n".join(context_parts)
        
        prompt = f"""You are a helpful agricultural assistant. Based on the tool results below, provide a natural, conversational response to the user's question.

User Question: {query}

Tool Results:
{context}

Instructions:
- Be conversational and helpful
- Include specific details from the tool results (distances, names, addresses)
- If location services found nearby facilities, mention them specifically
- If weather data is available, include relevant agricultural advice
- If no results were found, suggest alternatives or ask for clarification
- Keep the response focused and practical for farmers

Response:"""

        try:
            response = self.model.generate_content(prompt)
            text = getattr(response, 'text', '') or ''
            return text.strip() if text.strip() else "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
        except Exception:
            # Fallback: simple formatting
            lines = [f"Here's what I found for your query:"]
            for result in tool_results:
                if result.success and result.data:
                    if result.tool_name == "get_weather":
                        data = result.data
                        lines.append(f"Weather: {data.get('temperature', 'N/A')}, {data.get('humidity', 'N/A')}")
                    elif result.tool_name == "search_shops":
                        shops = result.data.get('shops', [])
                        if shops:
                            lines.append(f"Found {len(shops)} {result.data.get('type', 'shops')}:")
                            for shop in shops[:3]:
                                lines.append(f"- {shop['name']} ({shop['distance_km']} km)")
                        else:
                            lines.append(result.data.get('message', 'No shops found'))
                    elif result.tool_name == "search_kvk":
                        kvks = result.data.get('kvks', [])
                        if kvks:
                            lines.append(f"Found {len(kvks)} KVK centers:")
                            for kvk in kvks[:3]:
                                lines.append(f"- {kvk['name']} ({kvk['distance_km']} km)")
                        else:
                            lines.append(result.data.get('message', 'No KVK found'))
                    elif result.tool_name == "search_fpo":
                        fpos = result.data.get('fpos', [])
                        if fpos:
                            lines.append(f"Found {len(fpos)} FPOs:")
                            for fpo in fpos[:3]:
                                lines.append(f"- {fpo['name']} - {fpo['district']}")
                        else:
                            lines.append(result.data.get('message', 'No FPOs found'))
                    elif result.tool_name == "get_advisory":
                        advice = result.data.get('advice', [])
                        if advice:
                            lines.append("Agricultural Advisory:")
                            lines.append(advice[0]['content'][:200] + "...")
                        else:
                            lines.append(result.data.get('message', 'No specific advisory available'))
                elif not result.success:
                    lines.append(f"Error with {result.tool_name}: {result.error}")
                    
            return "\n".join(lines)


