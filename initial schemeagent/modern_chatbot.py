"""
Modern Agriculture Schemes Chatbot with Tool-based Architecture
"""
import google.generativeai as genai
import logging
from typing import List, Dict, Optional, Any
import re

from tool_interface import ToolManager
from scheme_search_tool import SchemeSearchTool
from database import SchemesVectorDB
from data_processor import SchemesDataProcessor
import config

# Set up logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format=config.LOG_FORMAT)
logger = logging.getLogger(__name__)


class AgricultureSchemesBot:
    """Modern agriculture schemes chatbot with tool-based architecture"""
    
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=config.GEMINI_API_KEY)
    self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Initialize tool manager
        self.tool_manager = ToolManager()
        
        # Conversation history
        self.conversation_history: List[Dict[str, str]] = []
        
        # System prompt for the AI
        self.system_prompt = """
You are AgriScheme Bot, an AI assistant specialized in helping farmers and agricultural stakeholders find relevant government schemes and programs in India.

Your primary capabilities:
1. **Scheme Search**: Use the scheme_search tool to find relevant agriculture schemes
2. **Information Synthesis**: Analyze tool results and provide comprehensive, farmer-friendly answers
3. **Guidance**: Help farmers understand eligibility, benefits, application processes
4. **Recommendations**: Suggest the most suitable schemes based on user needs

**Tool Usage Guidelines:**
- ALWAYS use available tools when users ask about schemes, programs, benefits, or assistance
- Analyze tool results thoroughly before responding
- Provide practical, actionable advice based on tool findings
- If multiple tools are relevant, use all of them to provide comprehensive answers

**Response Style:**
- Use simple, farmer-friendly language
- Structure responses with clear headings and bullet points
- Always mention specific scheme names, benefits, and application procedures
- Include contact information or official websites when available
- Be encouraging and supportive

**Important:**
- When using tools, wait for results before crafting your response
- Base your answers on actual tool results, not assumptions
- If no tools are relevant, provide general guidance and suggest how to find specific information

Remember: Your goal is to help farmers access the government benefits they deserve!
"""
    
    def initialize_database(self) -> bool:
        """Initialize the database with schemes data"""
        try:
            # Check if we need to load data
            db = SchemesVectorDB()
            stats = db.get_collection_stats()
            
            if stats.get('total_schemes', 0) > 0:
                logger.info(f"Database already contains {stats['total_schemes']} schemes")
                return True
            
            logger.info("Loading schemes from Excel file...")
            
            # Load and process data from Excel
            processor = SchemesDataProcessor("myscheme-gov-in-2025-08-10.xlsx")
            
            if not processor.load_data():
                logger.error("Failed to load Excel data")
                return False
            
            schemes = processor.process_schemes()
            
            if not schemes:
                logger.error("No schemes processed from Excel data")
                return False
            
            # Add schemes to database
            success = db.add_schemes(schemes)
            
            if success:
                logger.info(f"Successfully loaded {len(schemes)} schemes into database")
                return True
            else:
                logger.error("Failed to add schemes to database")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            return False
    
    def setup_tools(self):
        """Setup and register all available tools"""
        try:
            # Initialize database
            db = SchemesVectorDB()
            
            # Create and register scheme search tool
            scheme_tool = SchemeSearchTool(db)
            self.tool_manager.register_tool(scheme_tool)
            
            logger.info("All tools registered successfully")
            
        except Exception as e:
            logger.error(f"Error setting up tools: {str(e)}")
            raise
    
    def process_user_query(self, user_input: str) -> str:
        """Process user query and generate response using tools as needed"""
        try:
            logger.info(f"Processing query: {user_input[:100]}...")
            
            # Get relevant tools for this query
            relevant_tools = self.tool_manager.get_relevant_tools(user_input)
            
            # Execute relevant tools
            tool_results = []
            if relevant_tools:
                logger.info(f"Using {len(relevant_tools)} tools: {[t.name for t in relevant_tools]}")
                
                for tool in relevant_tools:
                    result = self.tool_manager.execute_tool(tool.name, user_input)
                    result['tool_name'] = tool.name
                    tool_results.append(result)
            
            # Generate AI response
            response = self._generate_ai_response(user_input, tool_results)
            
            # Update conversation history
            self.conversation_history.append({
                'user': user_input,
                'bot': response,
                'tools_used': [t.name for t in relevant_tools]
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing user query: {str(e)}")
            return "I apologize, but I encountered an error while processing your request. Please try asking your question again or rephrase it."
    
    def _generate_ai_response(self, user_input: str, tool_results: List[Dict]) -> str:
        """Generate AI response using Gemini with tool results"""
        try:
            # Build the prompt
            prompt = f"{self.system_prompt}\n\n"
            
            # Add conversation history (limited)
            if self.conversation_history:
                prompt += "Recent conversation:\n"
                for msg in self.conversation_history[-3:]:  # Last 3 exchanges
                    prompt += f"User: {msg['user']}\n"
                    prompt += f"Bot: {msg['bot'][:200]}...\n\n"
            
            # Add tool results if available
            if tool_results:
                prompt += "Tool Results:\n"
                for result in tool_results:
                    tool_name = result.get('tool_name', 'Unknown')
                    success = result.get('success', False)
                    
                    if success:
                        prompt += f"## {tool_name} Results:\n"
                        prompt += f"{result.get('result', 'No results')}\n\n"
                    else:
                        prompt += f"## {tool_name} Error:\n"
                        prompt += f"{result.get('message', 'Tool execution failed')}\n\n"
            else:
                prompt += "No tools were used for this query.\n\n"
            
            # Add current user query
            prompt += f"Current User Query: {user_input}\n\n"
            
            # Add instructions for response
            if tool_results:
                prompt += """
Based on the tool results above, provide a comprehensive, helpful response to the user's query. 

Guidelines:
1. Use the actual information from tool results, the info might not be structured properly, but info included is all there and correct so interpret the info as given but in a sensible structure.
2. Structure your response clearly with headings and bullet points
3. Be specific about scheme names, benefits, and procedures etc.
4. Use farmer-friendly language
5. Provide actionable next steps
6. Include contact information or websites when available

Response:"""
            else:
                prompt += """
The user's query didn't trigger any specific tools. Provide general guidance about agriculture schemes and suggest how they can find more specific information.

Guidelines:
1. Be helpful and encouraging
2. Suggest specific types of schemes they might be interested in
3. Recommend they ask more specific questions
4. Provide general information about common agriculture schemes

Response:"""
            
            # Generate response using Gemini
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text.strip()
            else:
                return "I apologize, but I'm having trouble generating a response right now. Please try asking your question again."
                
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "I encountered an error while processing your request. Please try again or contact support if the issue persists."
    
    def get_help_message(self) -> str:
        """Get help message with available commands and features"""
        tools_info = self.tool_manager.get_tools_summary()
        
        return f"""
🌾 **Welcome to AgriScheme Bot!** 🌾

I'm here to help you find relevant government agriculture schemes and programs in India.

**What I can help you with:**
• Find schemes based on your farming needs
• Explain eligibility criteria and benefits
• Guide you through application processes
• Provide information about subsidies and assistance
• Search by state, category, or specific requirements

**Available Tools:**
{tools_info}

**Sample Questions:**
• "What financial assistance schemes are available for small farmers?"
• "How can I apply for crop insurance?"
• "I need information about irrigation subsidies in Maharashtra"
• "What are the benefits of PM-KISAN scheme?"
• "Are there any schemes for organic farming?"

**Commands:**
• `help` - Show this help message
• `tools` - List available tools
• `stats` - Show database statistics
• `clear` - Clear conversation history
• `quit` - Exit the bot

**Tips for better results:**
• Be specific about your farming needs
• Mention your state if looking for state-specific schemes
• Ask about particular aspects like eligibility, benefits, or application process

Let's help you access the agricultural support you deserve! 🌱
"""
    
    def get_database_stats(self) -> str:
        """Get database statistics"""
        try:
            db = SchemesVectorDB()
            stats = db.get_collection_stats()
            
            result = f"📊 **Database Statistics:**\n"
            result += f"• Total Schemes: {stats.get('total_schemes', 0)}\n"
            result += f"• Database Path: {stats.get('database_path', 'Unknown')}\n"
            result += f"• Collection: {stats.get('collection_name', 'Unknown')}\n"
            
            if 'sample_categories' in stats:
                categories = list(stats['sample_categories'].keys())[:5]
                result += f"• Sample Categories: {', '.join(categories)}\n"
            
            if 'sample_states' in stats:
                states = list(stats['sample_states'].keys())[:10]
                result += f"• States Covered: {', '.join(states)}\n"
            
            return result
            
        except Exception as e:
            return f"Error getting database stats: {str(e)}"
    
    def chat_session(self):
        """Interactive chat session"""
        print("🌾 Initializing AgriScheme Bot...")
        
        # Initialize database
        if not self.initialize_database():
            print("⚠️  Warning: Database initialization failed. Some features may not work.")
        else:
            print("✅ Database initialized successfully!")
        
        # Setup tools
        try:
            self.setup_tools()
            print("✅ Tools initialized successfully!")
        except Exception as e:
            print(f"⚠️  Warning: Tool setup failed: {e}")
        
        print("\n" + "="*60)
        print(self.get_help_message())
        print("="*60)
        
        while True:
            try:
                user_input = input("\n🧑‍🌾 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n🌾 Thank you for using AgriScheme Bot! Happy farming! 🌾")
                    break
                
                elif user_input.lower() in ['help', 'commands']:
                    print("\n" + self.get_help_message())
                    continue
                
                elif user_input.lower() == 'tools':
                    print("\n" + self.tool_manager.get_tools_summary())
                    continue
                
                elif user_input.lower() == 'stats':
                    print("\n" + self.get_database_stats())
                    continue
                
                elif user_input.lower() in ['clear', 'reset']:
                    self.conversation_history.clear()
                    print("\n🤖 Bot: Conversation history cleared. How can I help you today?")
                    continue
                
                # Process normal query
                print("\n🤖 Bot: ", end="", flush=True)
                response = self.process_user_query(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\n🌾 Thank you for using AgriScheme Bot! Happy farming! 🌾")
                break
            except Exception as e:
                logger.error(f"Error in chat session: {str(e)}")
                print("\n🤖 Bot: I encountered an error. Please try again.")
    
    def process_single_query(self, query: str) -> str:
        """Process a single query (for API usage)"""
        return self.process_user_query(query)


def main():
    """Main function to run the chatbot"""
    try:
        bot = AgricultureSchemesBot()
        bot.chat_session()
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        print("❌ Failed to start the chatbot. Please check the configuration and try again.")


if __name__ == "__main__":
    main()
