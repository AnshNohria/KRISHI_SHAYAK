"""
Multi-Agent Agriculture Chatbot with LangChain Integration
"""
import logging
from typing import Optional
from datetime import datetime

from orchestrator_agent import OrchestratorAgent
import config

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, 'INFO'),
    format=config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('multiagent_chatbot.log')
    ]
)
logger = logging.getLogger(__name__)


class MultiAgentAgricultureBot:
    """
    Main chatbot interface using multi-agent architecture with LangChain
    """
    
    def __init__(self):
        self.orchestrator = None
        self.session_start_time = datetime.now()
        logger.info("Multi-Agent Agriculture Bot initialized")
    
    def initialize(self) -> bool:
        """Initialize the orchestrator and all agents"""
        try:
            print("🤖 Initializing Multi-Agent Agriculture Bot...")
            print("📊 Loading database and setting up agents...")
            
            self.orchestrator = OrchestratorAgent()
            
            # Verify system status
            status = self.orchestrator.get_system_status()
            print(f"✅ System initialized with {status['total_agents']} agents")
            
            if status.get('database', {}).get('total_schemes'):
                print(f"✅ Database loaded with {status['database']['total_schemes']} schemes")
            else:
                print("⚠️  Database status unknown")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing system: {str(e)}")
            print(f"❌ Failed to initialize: {str(e)}")
            return False
    
    def process_query(self, query: str) -> str:
        """Process a user query through the orchestrator"""
        if not self.orchestrator:
            return "❌ System not initialized. Please restart the application."
        
        try:
            return self.orchestrator.process_query(query)
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return "I apologize, but I encountered an error. Please try rephrasing your question."
    
    def get_help_message(self) -> str:
        """Get comprehensive help message"""
        return """
🌾 **Welcome to Multi-Agent Agriculture Bot!** 🌾

I'm your intelligent farming assistant powered by specialized AI agents that work together to help you.

**🤖 My Specialized Agents:**
• **SchemeAgent**: Expert in government schemes, subsidies, and benefits
• *(More agents coming soon: PriceAgent, WeatherAgent, CropAdvisoryAgent)*

**🎯 What I Can Help You With:**
• Find relevant government agriculture schemes
• Explain eligibility criteria and benefits  
• Guide you through application processes
• Provide state-specific scheme information
• Answer follow-up questions intelligently

**💬 Sample Questions:**
• "What schemes are available for small farmers?"
• "How can I apply for PM-KISAN scheme?"
• "What crop insurance options do I have?"
• "I'm from Punjab, what subsidies are available?"
• "Tell me more about the eligibility criteria" (follow-up)

**🔧 Commands:**
• `help` - Show this help message
• `status` - Show system status
• `history` - Show conversation history
• `suggestions` - Get query suggestions
• `clear` - Clear conversation history
• `quit` - Exit the bot

**🧠 Smart Features:**
• **Context Awareness**: I remember our conversation
• **Follow-up Handling**: Ask follow-up questions naturally
• **State Recognition**: Mention your state for personalized results
• **Multi-turn Conversations**: Build on previous topics

**💡 Tips:**
• Be specific about your farming needs
• Mention your location for better recommendations
• Ask follow-up questions for detailed information
• Use natural language - I understand context!

Ready to help you access agricultural support! 🌱
"""
    
    def get_system_status(self) -> str:
        """Get formatted system status"""
        if not self.orchestrator:
            return "❌ System not initialized"
        
        try:
            status = self.orchestrator.get_system_status()
            
            response = "📊 **System Status:**\n"
            response += f"🤖 **Agents**: {status['total_agents']} active\n"
            
            for agent in status['agents']:
                status_icon = "✅" if agent['initialized'] else "⚠️"
                response += f"   {status_icon} {agent['name']}: {len(agent['tools'])} tools\n"
            
            response += f"\n💬 **Conversation**: {status['conversation_history_length']} exchanges\n"
            response += f"🎯 **Last Agent**: {status.get('last_agent_used', 'None')}\n"
            
            # User profile
            profile = status['user_profile']
            if profile['location'] or profile['crops_of_interest']:
                response += f"\n👤 **Your Profile**:\n"
                if profile['location']:
                    response += f"   📍 Location: {profile['location']}\n"
                if profile['crops_of_interest']:
                    response += f"   🌾 Crops: {', '.join(profile['crops_of_interest'])}\n"
            
            # Database status
            if 'database' in status:
                db_info = status['database']
                if db_info.get('total_schemes'):
                    response += f"\n💾 **Database**: {db_info['total_schemes']} schemes available\n"
            
            uptime = datetime.now() - self.session_start_time
            response += f"\n⏱️ **Session**: {str(uptime).split('.')[0]}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return f"❌ Error retrieving status: {str(e)}"
    
    def get_conversation_history(self) -> str:
        """Get formatted conversation history"""
        if not self.orchestrator:
            return "❌ System not initialized"
        
        try:
            history = self.orchestrator.get_conversation_history()
            if history.strip() == "No previous conversation.":
                return "💬 No conversation history yet. Start by asking about agriculture schemes!"
            
            return f"📜 **Conversation History:**\n{history}"
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return f"❌ Error retrieving history: {str(e)}"
    
    def get_suggestions(self) -> str:
        """Get query suggestions"""
        if not self.orchestrator:
            return "❌ System not initialized"
        
        try:
            suggestions = self.orchestrator.suggest_queries()
            
            response = "💡 **Suggested Questions:**\n"
            for i, suggestion in enumerate(suggestions, 1):
                response += f"{i}. {suggestion}\n"
            
            response += "\n*Just type any of these questions or ask something similar!*"
            return response
            
        except Exception as e:
            logger.error(f"Error getting suggestions: {str(e)}")
            return f"❌ Error getting suggestions: {str(e)}"
    
    def clear_conversation(self) -> str:
        """Clear conversation history"""
        if not self.orchestrator:
            return "❌ System not initialized"
        
        try:
            self.orchestrator.clear_conversation()
            return "🧹 **Conversation cleared!** How can I help you today?"
        except Exception as e:
            logger.error(f"Error clearing conversation: {str(e)}")
            return f"❌ Error clearing conversation: {str(e)}"
    
    def chat_session(self):
        """Run interactive chat session"""
        if not self.initialize():
            print("❌ Failed to initialize the system. Exiting...")
            return
        
        print("\n" + "="*70)
        print(self.get_help_message())
        print("="*70)
        
        while True:
            try:
                user_input = input("\n🧑‍🌾 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                    print("\n🌾 Thank you for using Multi-Agent Agriculture Bot!")
                    print("Happy farming and may your crops prosper! 🌱")
                    break
                
                elif user_input.lower() in ['help', 'commands']:
                    print("\n" + self.get_help_message())
                    continue
                
                elif user_input.lower() == 'status':
                    print("\n" + self.get_system_status())
                    continue
                
                elif user_input.lower() in ['history', 'conversation']:
                    print("\n" + self.get_conversation_history())
                    continue
                
                elif user_input.lower() in ['suggestions', 'suggest']:
                    print("\n" + self.get_suggestions())
                    continue
                
                elif user_input.lower() in ['clear', 'reset']:
                    print("\n" + self.clear_conversation())
                    continue
                
                # Process normal query
                print("\n🤖 Bot: ", end="", flush=True)
                response = self.process_query(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\n🌾 Thank you for using Multi-Agent Agriculture Bot!")
                print("Happy farming! 🌱")
                break
            except Exception as e:
                logger.error(f"Error in chat session: {str(e)}")
                print("\n🤖 Bot: I encountered an error. Please try again or type 'help' for assistance.")
    
    def process_single_query(self, query: str) -> str:
        """Process a single query (for API usage)"""
        if not self.orchestrator:
            if not self.initialize():
                return "System initialization failed"
        
        return self.process_query(query)


def main():
    """Main function to run the multi-agent chatbot"""
    try:
        print("🚀 Starting Multi-Agent Agriculture Bot...")
        bot = MultiAgentAgricultureBot()
        bot.chat_session()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print("❌ A critical error occurred. Please check the logs and try again.")


if __name__ == "__main__":
    main()
