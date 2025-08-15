#!/usr/bin/env python3
"""
🌾 Krishi Dhan Sahayak - Agent-First Terminal Chatbot
Minimal interface that routes all queries through the Gemini agent (tools-backed).
"""

import os
import asyncio
from typing import Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from weather.service import (
    geocode_openweather,
    geocode_visual_crossing,
    geocode_freeform,
    check_api_configuration,
)
from core.profile import update_last_location, get_last_location
from ai.agent import GeminiToolAgent

class KrishiChatbot:
    """Agent-first Agricultural Terminal Chatbot (minimal)."""

    def __init__(self):
        self.running = True
        self.agent = GeminiToolAgent() 

    def show_welcome(self):
        """Display welcome message"""
        print("\n" + "="*80)
        print("🌾 Welcome to Krishi Dhan Sahayak!")
        print("="*80)
        print("\n📚 I can help you with topics like:")
        print("🌤️  Weather Advice")
        print("🏛️  FPO & KVK Information")  
        print("🌱  Crop Management")
        print("🐛  Pest & Disease Control")
        print("💧  Irrigation Guidance")
        print("🧪  Fertilizer Advice")
        print("\n⌨️  You can use commands like 'help', 'clear', 'quit', or 'exit'.")
        print("🗣️  Feel free to ask your questions in English.")
        print("="*80)


    def get_response(self, query: str) -> str:
        processed = query.lower()
        for wrong, right in self.keyword_corrections.items():
            processed = processed.replace(wrong, right)
        # Save location command
        if processed.startswith('set my location to ') or processed.startswith('set location to '):
            loc_frag = processed.replace('set my location to ', '').replace('set location to ', '').strip()
            v = s = None
            if ',' in loc_frag:
                v, s = self._parse_village_state_simple(loc_frag)
            if not (v and s):
                # Try free-form geocoding as a convenience
                async def _free():
                    return await geocode_freeform(loc_frag)
                gff = asyncio.run(_free())
                if gff:
                    update_last_location(gff['name'], gff.get('state') or '', gff['lat'], gff['lon'])
                    return f"📍 Saved location: {gff['name']}, {gff.get('state','').title()} ({gff['lat']:.4f},{gff['lon']:.4f})"
                return "❌ Use comma separated: set my location to Patna, Bihar"
            async def _geo():
                return await geocode_openweather(v, s) or await geocode_visual_crossing(v, s)
            geo = asyncio.run(_geo())
            if geo:
                update_last_location(v.title(), s.title(), geo['lat'], geo['lon'])
                return f"📍 Saved location: {v.title()}, {s.title()} ({geo['lat']:.4f},{geo['lon']:.4f})"
            return "❌ Could not geocode that location. Use format: set my location to Patna, Bihar"
        # Extract village/state hint
        v = s = None
        if ' in ' in processed:
            loc_frag = processed.split(' in ', 1)[1].strip()
            # Trim trailing add-ons like "also fpo", "and fpo", etc., to isolate location
            for stopper in [' also ', ' and fpo', ' also kvk', ' also shop']:
                if stopper in loc_frag:
                    loc_frag = loc_frag.split(stopper, 1)[0].strip()
            v, s = self._parse_village_state_simple(loc_frag)
            if not (v and s):
                async def _free2():
                    return await geocode_freeform(loc_frag)
                gff2 = asyncio.run(_free2())
                if gff2:
                    v, s = gff2['name'], gff2.get('state') or ''
        if not (v and s):
            last = get_last_location()
            if last:
                v, s = last.get('village'), last.get('state')
    # Always route through agent (Gemini not required for fallback stitching)
        try:
            return asyncio.run(self.agent.run(query, v, s))
        except Exception:
            return "I don't have enough verified data to answer."

    def display_response(self, response):
        """Display response in terminal"""
        print(f"\n🤖 Assistant's Response:")
        print("=" * 60)
        print(response.strip())
        print("=" * 60)

    # Legacy handlers removed to keep a minimal agent-first interface.

    def show_help(self):
        """Show concise help information"""
        print(
            "\nHelp: Ask agriculture questions (weather, FPO, KVK, shops, advisories).\n"
            "Examples: 'nearest fertilizer shop in Moga, Punjab', 'FPO for seeds in Moga, Punjab', 'kharif rice advisory'.\n"
            "Use: set my location to Village, State.\n"
        )

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        self.show_welcome()

    def run(self):
        """Main chatbot loop"""
        try:
            self.show_welcome()
            # Inform about weather API configuration status
            try:
                check_api_configuration()
            except Exception:
                pass
            print("\n✅ Chatbot is ready!")
            print("🗣️  Type your question below:\n")
            
            while self.running:
                try:
                    # Get user input
                    user_input = input("🌾 You: ").strip()
                    
                    if not user_input:
                        continue
                    
                    # Handle commands
                    if user_input.lower() in ['quit', 'exit', 'bye']:
                        print("\n🌾 Thank you for using the assistant. Happy farming! 🌾")
                        break
                        
                    elif user_input.lower() in ['help']:
                        self.show_help()
                        continue
                        
                    elif user_input.lower() in ['clear']:
                        self.clear_screen()
                        continue
                    
                    # Process the query
                    print("🔍 Processing...")
                    response = self.get_response(user_input)
                    
                    # Display response
                    self.display_response(response)
                    print()  # Add spacing
                    
                except KeyboardInterrupt:
                    print("\n\n🌾 Thank you! Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Application error: {e}")

def main():
    """Main function"""
    try:
        print("🚀 Starting Krishi Dhan Sahayak...")
        
        # Create and run chatbot
        chatbot = KrishiChatbot()
        chatbot.run()
        
    except KeyboardInterrupt:
        print("\n\n🌾 Thank you!")
    except Exception as e:
        print(f"❌ Error starting application: {e}")

if __name__ == "__main__":
    main()
