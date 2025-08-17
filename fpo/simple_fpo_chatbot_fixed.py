#!/usr/bin/env python3
"""
🏢 Simple FPO (Farmer Producer Organization) Chatbot
Direct access to FPO database with AI optimization for better search
"""

import os
import math
import asyncio
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import google.generativeai as genai
from service import FPOService

class SimpleFPOBot:
    """Simple FPO chatbot with AI optimization for search - processes single input with history"""

    def __init__(self):
        """Initialize with Gemini AI and FPO service"""
        # Configure Gemini AI
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Initialize FPO service
        self.fpo_service = FPOService()
        
        print("✅ Gemini AI initialized for FPO search optimization")

    def optimize_and_extract_search_terms(self, query: str, conversation_history: List[Dict] = None) -> Dict:
        """Use AI to extract and optimize search parameters from user query."""
        
        # Build context from conversation history
        context = ""
        if conversation_history:
            for exchange in conversation_history[-3:]:  # Last 3 exchanges
                context += f"User: {exchange.get('user', '')}\nBot: {exchange.get('bot', '')}\n"
        
        prompt = f"""
        You are an AI assistant helping extract search parameters for FPO (Farmer Producer Organization) queries.
        
        Context from previous conversation:
        {context}
        
        Current query: "{query}"
        
        Extract the following information and return ONLY a JSON object:
        {{
            "search_term": "optimized search term (place/region/crop/activity)",
            "search_type": "state|district|general", 
            "confidence": "high|medium|low"
        }}
        
        Rules:
        - If query mentions a state name, use "state" type
        - If query mentions a district/city, use "district" type  
        - For crop/activity queries, use "general" type
        - Optimize search_term for better matching (expand abbreviations, correct spelling)
        - Set confidence based on clarity of the query
        
        Examples:
        "FPOs in Punjab" → {{"search_term": "Punjab", "search_type": "state", "confidence": "high"}}
        "potato farmers in UP" → {{"search_term": "Uttar Pradesh", "search_type": "state", "confidence": "high"}}
        "nearest FPO to Ludhiana" → {{"search_term": "Ludhiana, Punjab", "search_type": "district", "confidence": "high"}}
        """
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            import json
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback parsing
                return {'search_term': query.strip(), 'search_type': 'general', 'confidence': 'medium'}
                
        except Exception as e:
            print(f"⚠️ AI optimization failed: {e}")
            # Simple fallback extraction
            query_lower = query.lower()
            if any(state in query_lower for state in ['punjab', 'haryana', 'maharashtra', 'gujarat', 'rajasthan']):
                return {'search_term': query.strip(), 'search_type': 'state', 'confidence': 'medium'}
            elif 'nearest' in query_lower or 'near' in query_lower:
                return {'search_term': query.strip(), 'search_type': 'district', 'confidence': 'medium'}
            else:
                return {'search_term': query.strip(), 'search_type': 'general', 'confidence': 'low'}

    def _extract_state_from_query(self, query: str) -> Optional[str]:
        """Extract state name from query"""
        state_mappings = {
            'punjab': 'Punjab',
            'haryana': 'Haryana', 
            'maharashtra': 'Maharashtra',
            'gujarat': 'Gujarat',
            'rajasthan': 'Rajasthan',
            'up': 'Uttar Pradesh',
            'uttar pradesh': 'Uttar Pradesh',
            'mp': 'Madhya Pradesh',
            'madhya pradesh': 'Madhya Pradesh',
            'bihar': 'Bihar',
            'west bengal': 'West Bengal',
            'odisha': 'Odisha',
            'telangana': 'Telangana',
            'andhra pradesh': 'Andhra Pradesh',
            'karnataka': 'Karnataka',
            'tamil nadu': 'Tamil Nadu',
            'kerala': 'Kerala'
        }
        
        query_lower = query.lower()
        for key, value in state_mappings.items():
            if key in query_lower:
                return value
        return None

    def get_fpo_response(self, query: str, conversation_history: List[Dict] = None) -> str:
        """Get direct FPO information with AI-optimized search and smart fallback"""
        try:
            # Single AI call to extract search parameters
            search_data = self.optimize_and_extract_search_terms(query, conversation_history)
            search_term = search_data['search_term']
            search_type = search_data['search_type']
            
            print(f"🔍 Searching for FPOs: '{search_term}' (type: {search_type})")
            
            # Perform search based on optimized parameters
            fpos = []
            
            if search_type == 'state':
                fpos = self.fpo_service.find_fpos_by_state(search_term)
            elif search_type == 'district':
                # Search in district names
                all_fpos = self.fpo_service.fpos
                fpos = [fpo for fpo in all_fpos if search_term.lower() in fpo.district.lower()]
            else:
                # General search in all fields
                all_fpos = self.fpo_service.fpos
                search_lower = search_term.lower()
                fpos = [fpo for fpo in all_fpos if (
                    search_lower in fpo.name.lower() or 
                    search_lower in fpo.district.lower() or 
                    search_lower in fpo.state.lower()
                )]
            
            # If no direct results and this looks like a location query, try state-level fallback
            if not fpos and search_type in ['district', 'general']:
                print(f"🔄 No FPOs found in '{search_term}', trying state-level search...")
                
                # Try to extract state from the search term
                state_extracted = self._extract_state_from_query(search_term)
                if state_extracted:
                    print(f"🏛️ Extracted state: {state_extracted}")
                    state_fpos = self.fpo_service.find_fpos_by_state(state_extracted)
                    print(f"📊 Found {len(state_fpos)} FPOs total in {state_extracted}")
                    
                    if state_fpos:
                        # Extract just the city/town name for better geocoding
                        city_name = search_term.split(',')[0].strip()
                        
                        # Simple approach: geocode user and a few FPOs to find nearest
                        print(f"🔄 Finding nearest FPOs to {city_name} in {state_extracted}...")
                        
                        # First, geocode user location
                        user_coords = self.fpo_service.geocode_location_sync(f"{city_name}, {state_extracted}, India")
                        
                        if user_coords:
                            user_lat, user_lon = user_coords
                            print(f"📍 User at: {user_lat:.4f}, {user_lon:.4f}")
                            
                            # Get unique districts in the state
                            unique_districts = list(set(fpo.district for fpo in state_fpos))
                            print(f"🏛️ Found {len(unique_districts)} districts in {state_extracted}")
                            
                            # Geocode a few districts and calculate distances
                            district_distances = []
                            for district in unique_districts[:10]:  # Limit to first 10 districts
                                district_coords = self.fpo_service.geocode_location_sync(f"{district}, {state_extracted}, India")
                                if district_coords:
                                    dist_lat, dist_lon = district_coords
                                    distance = self.fpo_service.calculate_distance(user_lat, user_lon, dist_lat, dist_lon)
                                    district_distances.append((district, distance))
                                    print(f"📍 {district}: {distance:.1f} km")
                            
                            # Sort districts by distance
                            district_distances.sort(key=lambda x: x[1])
                            
                            # Get FPOs from nearest districts
                            nearest_fpos = []
                            for district, distance in district_distances[:3]:  # Top 3 nearest districts
                                district_fpos = [fpo for fpo in state_fpos if fpo.district == district]
                                for fpo in district_fpos[:2]:  # Max 2 FPOs per district
                                    nearest_fpos.append((fpo, distance))
                            
                            if nearest_fpos:
                                response = f"Found {len(nearest_fpos)} nearest FPOs to {city_name}:\n\n"
                                for i, (fpo, distance) in enumerate(nearest_fpos[:5], 1):
                                    response += f"{i}. {fpo.name}\n"
                                    response += f"   Location: {fpo.district}, {fpo.state}\n"
                                    response += f"   Distance: ~{distance:.1f} km from {city_name}\n"
                                    response += "\n"
                                return response
                            else:
                                print(f"❌ No districts could be geocoded")
                        else:
                            print(f"❌ Could not geocode user location")
                        
                        # Fallback: return first 5 FPOs from the state
                        response = f"Here are some FPOs in {state_extracted}:\n\n"
                        for i, fpo in enumerate(state_fpos[:5], 1):
                            response += f"{i}. {fpo.name}\n"
                            response += f"   Location: {fpo.district}, {fpo.state}\n"
                            response += "\n"
                        return response
                        
        except Exception as e:
            print(f"❌ Error in FPO search: {e}")
            return f"❌ Error processing FPO request: {e}"
            
        if not fpos:
            return f"❌ No FPOs found for '{search_term}' (search type: {search_type})"
        
        # Format results (limit to 10)
        response = f"Found {len(fpos)} FPO(s) for '{search_term}':\n\n"
        for i, fpo in enumerate(fpos[:10], 1):
            response += f"{i}. {fpo.name}\n"
            response += f"   Location: {fpo.district}, {fpo.state}\n"
            response += "\n"
        
        return response

def main():
    """Main function to run the FPO chatbot"""
    print("🚀 Starting Simple FPO Chatbot...")
    
    try:
        bot = SimpleFPOBot()
    except Exception as e:
        print(f"❌ Failed to initialize bot: {e}")
        return
    
    print("\n✅ FPO Chatbot ready! Provide input with conversation history:")
    print("💡 Format: 'HISTORY: <previous exchanges> QUERY: <your FPO question>'")
    print("💡 Or just: '<your FPO question>' (no history)")
    print("💡 Examples:")
    print("   - 'HISTORY: User discussed farming in Punjab QUERY: find FPOs there'")
    print("   - 'FPOs in Maharashtra'")
    print("   - 'cotton producer organizations'")
    print()
    
    # Get user input
    user_input = input("🏢 You: ").strip()
    
    if not user_input:
        print("❌ No input provided")
        return
    
    # Parse input for history and query
    conversation_history = []
    query = user_input
    
    if user_input.upper().startswith('HISTORY:'):
        try:
            parts = user_input.split('QUERY:', 1)
            if len(parts) == 2:
                history_text = parts[0].replace('HISTORY:', '').strip()
                query = parts[1].strip()
                
                # Simple history parsing (you can enhance this)
                if history_text:
                    conversation_history = [{"user": "previous context", "bot": history_text}]
        except Exception:
            pass  # Use original input if parsing fails
    
    print("🔍 Extracting search parameters using AI optimization...")
    
    # Get optimized search data first for display
    search_data = bot.optimize_and_extract_search_terms(query, conversation_history)
    print(f"🔧 Search optimized: Term='{search_data['search_term']}', Type='{search_data['search_type']}', Confidence='{search_data['confidence']}'")
    
    # Get response
    response = bot.get_fpo_response(query, conversation_history)
    
    print("\n🏢 FPO Results:")
    print("-" * 60)
    print(response)
    print("-" * 60)
    print("\n🏢 Thank you for using FPO chatbot!")

if __name__ == "__main__":
    main()
