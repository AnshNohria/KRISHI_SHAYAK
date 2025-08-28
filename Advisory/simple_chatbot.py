#!/usr/bin/env python3
"""
🌾 Simple Krishi Advisory Chatbot
Focused ChromaDB + Conversational AI tool for agricultural guidance
"""

import os
import asyncio
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import google.generativeai as genai
from Advisory.rag.retriever import get_retriever
from Advisory.rag.ingest import ingest_kharif_rabi

class SimpleKrishiBot:
    """Simple agricultural advisor using ChromaDB + Gemini conversation"""
    
    def __init__(self):
        # Auto-ingest kharif and rabi crops on bot startup
        # try:
        #     ingest_kharif_rabi()
        #     print("✅ RAG crops ingested (kharif/rabi)")
        # except Exception as e:
        #     print(f"⚠️  RAG ingestion failed: {e}")
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
    
    def optimize_query(self, user_query: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Optimize user query using Gemini for better RAG search results, with optional history context."""
        if not self.model:
            return user_query  # Return original if no AI available

        try:
            history_context = ""
            if conversation_history:
                # Use last 3 exchanges' content only (role/content schema expected)
                recent = [item.get('content', '') for item in conversation_history[-3:] if isinstance(item, dict)]
                history_context = "\n".join([c for c in recent if c])

            prompt = f"""
You are an agricultural search optimization expert. Convert user questions to high-recall search terms for retrieving relevant agronomic guidance.

Conversation History (optional, latest last):
{history_context}

User Query: "{user_query}"

Instructions:
1. Extract core agricultural concepts, crop names, practices, or problems.
2. Include relevant synonyms and technical/agronomy terms.
3. Include both common and scientific terms when useful.
4. Keep concise, keywords-only; no sentences.
5. Prefer Indian context terms where applicable (e.g., kharif/rabi, paddy, etc.).

Examples:
- "when to sow wheat in punjab" → "wheat sowing time Punjab planting schedule timing cultivation"
- "rice pest problem" → "rice pest control disease management insect paddy crop protection"
- "organic farming" → "organic farming practices sustainable agriculture natural methods chemical-free cultivation"

Respond with ONLY the optimized terms (no quotes, no extra text) """

            response = self.model.generate_content(prompt)
            optimized = (response.text or "").strip()

            # Fallback to original if optimization seems wrong
            if len(optimized) < 5 or len(optimized) > 200:
                return user_query

            print(f"🔧 Query optimized: '{user_query}' → '{optimized}'")
            return optimized

        except Exception as e:
            print(f"⚠️  Query optimization failed: {e}")
            return user_query

    def get_rag_response(self, query: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Get response from ChromaDB RAG system using an optimized query and optional conversation history."""
        try:
            retriever = get_retriever()

            # Optimize query (with history) when possible
            optimized_query = self.optimize_query(query, conversation_history)
            q_used = optimized_query or query
            print(f"🔍 Querying database: text='{q_used}', k=5, min_score=0.0")

            # First pass
            chunks = retriever.query(q_used, k=5, min_score=0.0)
            print(f"📊 Found {len(chunks)} chunks with min_score=0.0")

            # Fallback to original raw query if optimization yielded nothing
            if not chunks and q_used != query:
                print("↩️ No results with optimized terms; retrying with original query…")
                chunks = retriever.query(query, k=5, min_score=0.0)
                print(f"📊 Fallback found {len(chunks)} chunks")

            if not chunks:
                return "❌ No relevant agricultural information found in the database."

            # Format RAG response
            response = "📚 **Agricultural Advisory:**\n\n"

            for i, chunk in enumerate(chunks, 1):
                score_pct = (chunk.get('score') or 0) * 100
                response += f"**{i}.** {chunk['text']}\n"
                if chunk.get('source'):
                    response += f"   *Source: {chunk['source']}*\n"
                response += f"   *Relevance: {score_pct:.1f}%*\n\n"

            response += f"💡 *Found {len(chunks)} relevant results*\n"

            return response

        except Exception as e:
            return f"❌ Error retrieving information: {e}"
    

    
    def process_query(self, query: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Process user query with optimization and optional conversation history, then return RAG response."""
        print("🔍 Optimizing search query…")

        # Get RAG results with optimized query and history
        return self.get_rag_response(query, conversation_history)
    
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
