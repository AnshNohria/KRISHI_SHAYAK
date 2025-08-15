#!/usr/bin/env python3
"""
🌾 Simple Krishi Advisory Chatbot
Focused ChromaDB + Conversational AI tool for agricultural guidance
"""

import os
import asyncio
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import google.generativeai as genai
from rag.retriever import get_retriever

class SimpleKrishiBot:
    """Simple agricultural advisor using ChromaDB + Gemini conversation"""
    
    def __init__(self):
        self.setup_gemini()
        self.running = True
        
    def setup_gemini(self):
        """Initialize Gemini AI"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️  No Gemini API key found. RAG-only mode.")
            self.model = None
            return
            
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            print("✅ Gemini AI initialized")
        except Exception as e:
            print(f"⚠️  Gemini setup failed: {e}. RAG-only mode.")
            self.model = None
    
    def optimize_query(self, user_query: str) -> str:
        """Optimize user query using Gemini for better RAG search results"""
        if not self.model:
            return user_query  # Return original if no AI available
            
        try:
            prompt = f"""
You are an agricultural search optimization expert. Your job is to convert user queries into better search terms for finding relevant agricultural information.

User Query: "{user_query}"

Instructions:
1. Extract the core agricultural concepts, crops, practices, or problems
2. Add relevant synonyms and technical terms farmers might use
3. Include both common and scientific terminology when applicable
4. Focus on actionable agricultural advice keywords
5. Keep it concise but comprehensive
6. If the query is already well-formed, enhance it slightly

Examples:
- "when to sow wheat in punjab" → "wheat sowing time Punjab planting schedule timing cultivation"
- "rice pest problem" → "rice pest control disease management insect paddy crop protection"
- "organic farming" → "organic farming practices sustainable agriculture natural methods chemical-free cultivation"

Optimized Search Query (respond with ONLY the optimized terms):"""

            response = self.model.generate_content(prompt)
            optimized = response.text.strip()
            
            # Fallback to original if optimization seems wrong
            if len(optimized) < 5 or len(optimized) > 200:
                return user_query
                
            print(f"🔧 Query optimized: '{user_query}' → '{optimized}'")
            return optimized
            
        except Exception as e:
            print(f"⚠️  Query optimization failed: {e}")
            return user_query

    def get_rag_response(self, query: str) -> str:
        """Get response from ChromaDB RAG system with optimized query"""
        try:
            # First optimize the query using Gemini
            optimized_query = self.optimize_query(query)
            
            retriever = get_retriever()
            chunks = retriever.query(optimized_query, k=5, min_score=0.2)
            
            if not chunks:
                return "❌ No relevant agricultural information found in the database."
            
            # Format RAG response
            response = "📚 **Agricultural Advisory:**\n\n"
            
            for i, chunk in enumerate(chunks, 1):
                score_pct = chunk.get('score', 0) * 100
                response += f"**{i}.** {chunk['text']}\n"
                if chunk.get('source'):
                    response += f"   *Source: {chunk['source']}*\n"
                response += f"   *Relevance: {score_pct:.1f}%*\n\n"
            
            response += f"💡 *Found {len(chunks)} relevant results*\n"
                
            return response
            
        except Exception as e:
            return f"❌ Error retrieving information: {e}"
    
    def get_enhanced_response(self, query: str, rag_results: str) -> str:
        """Enhance RAG results with conversational AI"""
        if not self.model:
            return rag_results
            
        try:
            prompt = f"""
You are an expert agricultural advisor helping Indian farmers. 

User Query: {query}

Agricultural Information from Database:
{rag_results}

Instructions:
1. Use ONLY the information provided above from the database
2. Create a clear, conversational response for the farmer
3. Structure the advice in an easy-to-understand format
4. Include practical, actionable steps when relevant
5. If the database information doesn't match the query well, say so
6. Always prioritize farmer safety and sustainable practices

Response:"""

            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"⚠️  AI enhancement failed: {e}")
            return rag_results
    
    def process_query(self, query: str) -> str:
        """Process user query with optimization and return response"""
        print("🔍 Optimizing search query...")
        
        # Get RAG results with optimized query
        rag_response = self.get_rag_response(query)
        
        if "❌" in rag_response:
            return rag_response
        
        # Enhance with AI if available
        if self.model:
            print("🤖 Enhancing with conversational AI...")
            return self.get_enhanced_response(query, rag_response)
        else:
            return rag_response
    
    def show_welcome(self):
        """Display welcome message"""
        print("\n" + "="*80)
        print("🌾 Smart Krishi Advisory Chatbot")
        print("="*80)
        print("\n✨ Features:")
        print("🔧 AI Query Optimization - Your questions are enhanced for better results")
        print("📚 ChromaDB Agricultural Database - 6,010+ expert advisory chunks")
        print("🤖 Conversational AI - Technical info made farmer-friendly")
        print("\n📚 Ask me about:")
        print("🌱 Crop cultivation and management")
        print("🐛 Pest and disease control")  
        print("💧 Irrigation and water management")
        print("🧪 Fertilizers and soil health")
        print("🌤️  Weather-based farming advice")
        print("📋 Government schemes and programs")
        print("\n⌨️  Commands: 'help', 'clear', 'quit'")
        print("🗣️  Ask questions in simple English")
        print("="*80)
    
    def display_response(self, response: str):
        """Display formatted response"""
        print(f"\n🌾 Agricultural Advisor:")
        print("=" * 60)
        print(response.strip())
        print("=" * 60)
    
    def show_help(self):
        """Show help information"""
        print("\n📖 Help - Smart Krishi Advisory Chatbot")
        print("-" * 50)
        print("This bot uses AI to optimize your questions and provides agricultural")
        print("advice using a comprehensive database of farming information.")
        print("\n✨ How it works:")
        print("1. 🔧 AI optimizes your question for better search")
        print("2. 📚 Searches ChromaDB agricultural database") 
        print("3. 🤖 AI makes technical information farmer-friendly")
        print("\nExample questions:")
        print("• 'How to control aphids in cotton?'")
        print("• 'Best fertilizer for wheat crops?'")
        print("• 'Irrigation schedule for rice?'")
        print("• 'Organic farming practices'")
        print("• 'Soil testing importance'")
        print("\nCommands:")
        print("• 'help' - Show this help")
        print("• 'clear' - Clear screen") 
        print("• 'quit' or 'exit' - Exit chatbot")
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        self.show_welcome()
    
    def run(self):
        """Main chatbot loop"""
        try:
            self.show_welcome()
            print("\n✅ Chatbot ready! Ask your agricultural questions:")
            
            while self.running:
                try:
                    # Get user input
                    user_input = input("\n🌾 You: ").strip()
                    
                    if not user_input:
                        continue
                    
                    # Handle commands
                    if user_input.lower() in ['quit', 'exit', 'bye']:
                        print("\n🌾 Happy farming! Goodbye! 🌾")
                        break
                    elif user_input.lower() == 'help':
                        self.show_help()
                        continue
                    elif user_input.lower() == 'clear':
                        self.clear_screen()
                        continue
                    
                    # Process agricultural query
                    response = self.process_query(user_input)
                    self.display_response(response)
                    
                except KeyboardInterrupt:
                    print("\n\n🌾 Thank you! Happy farming!")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
        except Exception as e:
            print(f"❌ Application error: {e}")

def main():
    """Main function"""
    try:
        print("🚀 Starting Smart Krishi Advisory Chatbot...")
        bot = SimpleKrishiBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🌾 Goodbye!")
    except Exception as e:
        print(f"❌ Startup error: {e}")

if __name__ == "__main__":
    main()
