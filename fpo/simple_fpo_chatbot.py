#!/usr/bin/env python3
"""
🏢 Simple FPO (Farmer Producer Organization) Chatbot
Direct access to FPO database with AI optimization for better search
"""

import os
import sys
import math
import asyncio
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import google.generativeai as genai
# Ensure project root is on sys.path so sibling packages (maps, weather) can be imported by service
try:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
except Exception:
    pass

from service import FPOService

class SimpleFPOBot:
    """Simple FPO chatbot with AI optimization for search - processes single input with history"""

    def __init__(self):
        self.fpo_service = FPOService()
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
            print("✅ Gemini AI initialized for FPO search optimization")
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
    
    def optimize_and_extract_search_terms(self, user_query: str, conversation_history: List[Dict] = None) -> Dict[str, str]:
        """Use Gemini to optimize query and extract search terms in one API call"""
        if not self.model:
            # Fallback: simple parsing without AI
            return self._fallback_search_parsing(user_query)
            
        try:
            history_context = ""
            if conversation_history:
                history_context = "\n".join([
                    item.get('exchange', '') for item in conversation_history[-3:]  # Last 3 exchanges
                ])
            
            prompt = f"""
You are an FPO (Farmer Producer Organization) search optimization expert for Indian agriculture. Extract search parameters from user queries.

Conversation History:
{history_context}

Current User Query: "{user_query}"

Instructions:
1. Extract the primary search term (state, district, FPO name, or crop type)
2. Identify the search type: "state", "district", "name", or "general"
3. Use conversation history context if current query is ambiguous
4. Handle common Indian place name variations and agricultural terms
5. Consider agricultural context and FPO-related keywords
6. Use LATEST information from query but consider context from history

Respond ONLY in this exact JSON format:
{{
    "search_term": "extracted search term",
    "search_type": "state|district|name|general",
    "confidence": "high|medium|low"
}}

Examples:
- "FPOs in Punjab" → {{"search_term": "Punjab", "search_type": "state", "confidence": "high"}}
- "farmer groups in Ludhiana district" → {{"search_term": "Ludhiana", "search_type": "district", "confidence": "high"}}
- "cotton producer organizations" → {{"search_term": "cotton", "search_type": "general", "confidence": "medium"}}
- "find cooperatives" + History: "...Maharashtra farming..." → {{"search_term": "Maharashtra", "search_type": "state", "confidence": "high"}}
- "list organizations there" + History: "...Karnataka discussion..." → {{"search_term": "Karnataka", "search_type": "state", "confidence": "high"}}
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
            search_data = json.loads(result)
            
            search_term = search_data.get('search_term', '').strip()
            search_type = search_data.get('search_type', 'general').strip()
            confidence = search_data.get('confidence', 'medium').strip()
            
            # Basic validation
            if not search_term or len(search_term) < 2:
                return self._fallback_search_parsing(user_query)
            
            print(f"🔧 Search optimized: Term='{search_term}', Type='{search_type}', Confidence='{confidence}'")
            return {'search_term': search_term, 'search_type': search_type, 'confidence': confidence}
            
        except Exception as e:
            print(f"⚠️  AI search optimization failed: {e}")
            return self._fallback_search_parsing(user_query)
    
    def _fallback_search_parsing(self, query: str) -> Dict[str, str]:
        """Fallback search parsing without AI"""
        query_lower = query.lower()
        
        # Simple keyword detection
        if any(state in query_lower for state in ['punjab', 'haryana', 'uttar pradesh', 'maharashtra', 'gujarat', 'rajasthan', 'karnataka', 'kerala', 'tamil nadu']):
            return {'search_term': query.strip(), 'search_type': 'state', 'confidence': 'medium'}
        elif 'district' in query_lower:
            return {'search_term': query.replace('district', '').strip(), 'search_type': 'district', 'confidence': 'medium'}
        else:
            return {'search_term': query.strip(), 'search_type': 'general', 'confidence': 'low'}

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
                # General search (name, district, state)
                all_fpos = self.fpo_service.fpos
                search_term_lower = search_term.lower()
                fpos = [fpo for fpo in all_fpos if (
                    search_term_lower in fpo.name.lower() or 
                    search_term_lower in fpo.district.lower() or 
                    search_term_lower in fpo.state.lower()
                )]
            
            # If no FPOs found and query contains a city/district, try state-level search
            if not fpos and search_type != 'state':
                print(f"🔄 No FPOs found in '{search_term}', trying state-level search...")
                
                # Extract state from the search term (try common patterns)
                state_extracted = self._extract_state_from_query(search_term, query)
                if state_extracted:
                    print(f"🏛️ Extracted state: {state_extracted}")
                    
                    # Use the existing service functions properly
                    import asyncio
                    try:
                        # First get all FPOs in the state
                        state_fpos = self.fpo_service.find_fpos_by_state(state_extracted)
                        print(f"📊 Found {len(state_fpos)} FPOs total in {state_extracted}")
                        
                        if not state_fpos:
                            print(f"❌ No FPOs found in state {state_extracted}")
                        else:
                            # Extract just the city/town name for better geocoding
                            city_name = search_term.split(',')[0].strip()
                            print(f"🔄 Finding nearest FPOs to {city_name} in {state_extracted} (sync)...")

                            # Use service sync function that geocodes all districts and computes nearest
                            nearest = self.fpo_service.find_nearest_fpos_with_geocoding_sync(
                                city_name, state_extracted, limit=5
                            )

                            if nearest:
                                response = f"Found {len(nearest)} nearest FPOs to {city_name}:\n\n"
                                for i, (fpo, distance) in enumerate(nearest, 1):
                                    response += f"{i}. {fpo.name}\n"
                                    response += f"   Location: {fpo.district}, {fpo.state}\n"
                                    response += f"   Distance: ~{distance:.1f} km from {city_name}\n"
                                    response += "\n"
                                return response

                            # Fallback: return first 5 from the state
                            response = f"Here are some FPOs in {state_extracted}:\n\n"
                            for i, fpo in enumerate(state_fpos[:5], 1):
                                response += f"{i}. {fpo.name}\n"
                                response += f"   Location: {fpo.district}, {fpo.state}\n"
                                response += "\n"
                            return response
                    except Exception as e:
                        print(f"❌ Error using service functions: {e}")
                        import traceback
                        traceback.print_exc()
            
            if not fpos:
                return f"❌ No FPOs found for '{search_term}' (search type: {search_type})"
            
            # Format results (limit to 10)
            response = f"Found {len(fpos)} FPO(s) for '{search_term}':\n\n"
            for i, fpo in enumerate(fpos[:10], 1):
                response += f"{i}. {fpo.name}\n"
                response += f"   Location: {fpo.district}, {fpo.state}\n"
                if fpo.lat and fpo.lon:
                    response += f"   Coordinates: {fpo.lat:.4f}, {fpo.lon:.4f}\n"
                response += "\n"
            
            if len(fpos) > 10:
                response += f"... and {len(fpos) - 10} more FPOs"
                
            return response
            
        except Exception as e:
            return f"❌ Error retrieving FPO information: {e}"
    
    def _extract_state_from_query(self, search_term: str, original_query: str) -> Optional[str]:
        """Extract state name from search term or original query"""
        # Common Indian states (simplified list)
        states = {
            'punjab': 'Punjab',
            'haryana': 'Haryana', 
            'uttar pradesh': 'Uttar Pradesh',
            'up': 'Uttar Pradesh',
            'maharashtra': 'Maharashtra',
            'gujarat': 'Gujarat',
            'rajasthan': 'Rajasthan',
            'madhya pradesh': 'Madhya Pradesh',
            'mp': 'Madhya Pradesh',
            'karnataka': 'Karnataka',
            'tamil nadu': 'Tamil Nadu',
            'andhra pradesh': 'Andhra Pradesh',
            'telangana': 'Telangana',
            'kerala': 'Kerala',
            'odisha': 'Odisha',
            'west bengal': 'West Bengal',
            'bihar': 'Bihar',
            'jharkhand': 'Jharkhand',
            'assam': 'Assam'
        }
        
        # Check if state is mentioned in search term or original query
        combined_text = f"{search_term} {original_query}".lower()
        for state_key, state_name in states.items():
            if state_key in combined_text:
                return state_name
        
        return None
    
    def process_input(self, input_string: str) -> str:
        """Process input string containing history and query, return FPO results"""
        print("🔍 Extracting search parameters using AI optimization...")
        
        # Parse input to get history and current query
        conversation_history, current_query = self.parse_input(input_string)
        
        if conversation_history:
            print(f"📚 Using {len(conversation_history)} previous exchanges for context")
        
        # Get FPO response with context (single AI call for search optimization)
        return self.get_fpo_response(current_query, conversation_history)

    def process_query(self, query: str) -> str:
        """Legacy method for backward compatibility"""
        return self.process_input(query)

    def display_response(self, response: str):
        """Display formatted response"""
        print(f"\n🏢 FPO Results:")
        print("-" * 60)
        print(response.strip())
        print("-" * 60)

    def run(self):
        """Main chatbot loop - answer only one query with conversation history"""
        try:
            print("\n✅ FPO Chatbot ready! Provide input with conversation history:")
            print("💡 Format: 'HISTORY: <previous exchanges> QUERY: <your FPO question>'")
            print("💡 Or just: '<your FPO question>' (no history)")
            print("💡 Examples:")
            print("   - 'HISTORY: User discussed farming in Punjab QUERY: find FPOs there'")
            print("   - 'FPOs in Maharashtra'")
            print("   - 'cotton producer organizations'")
            
            # Get single user input
            user_input = input("\n🏢 You: ").strip()
            
            if user_input:
                # Process input with history and query
                response = self.process_input(user_input)
                self.display_response(response)
            
            print("\n🏢 Thank you for using FPO chatbot!")
                
        except Exception as e:
            print(f"❌ Application error: {e}")

def main():
    """Main function"""
    try:
        print("🚀 Starting Simple FPO Chatbot...")
        bot = SimpleFPOBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🏢 Goodbye!")
    except Exception as e:
        print(f"❌ Startup error: {e}")

if __name__ == "__main__":
    main()
