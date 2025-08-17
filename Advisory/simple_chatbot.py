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
            # For now, skip optimization and use original query directly
            print(f"🔍 Searching database with original query: '{query}'")
            
            retriever = get_retriever()
            
            # Try with no threshold to see if anything comes back
            chunks = retriever.query(query, k=5, min_score=0.0)
            print(f"📊 Found {len(chunks)} chunks with min_score=0.0")
            
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
    

    
    def process_query(self, query: str) -> str:
        """Process user query with optimization and return response"""
        print("🔍 Optimizing search query...")
        
        # Get RAG results with optimized query
        rag_response = self.get_rag_response(query)
        
        # Return direct RAG response (no AI enhancement)
        return rag_response
    
    def show_welcome(self):
        """Display welcome message"""
        pass
    
    def display_response(self, response: str):
        """Display formatted response"""
        print(f"\n🌾 Agricultural Advisor:")
        print("=" * 60)
        print(response.strip())
        print("=" * 60)


    def run(self):
        """Main chatbot loop - answer only one query"""
        try:
            self.show_welcome()
            print("\n✅ Chatbot ready! Ask your agricultural question:")
            
            # Get single user input
            user_input = input("\n🌾 You: ").strip()
            
            if user_input:
                # Process agricultural query
                response = self.process_query(user_input)
                self.display_response(response)
            
            print("\n🌾 Thank you for using the chatbot!")
                
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
