"""
Simplified Multi-Agent Agriculture Chatbot
Fixed version that works with Google Gemini and ChromaDB
"""
import logging
from typing import Dict, Any
from simple_orchestrator import SimpleOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class SimplifiedMultiAgentBot:
    """Simplified multi-agent agriculture chatbot"""
    
    def __init__(self):
        print("🚀 Starting Simplified Multi-Agent Agriculture Bot...")
        logger.info("Simplified Multi-Agent Agriculture Bot initialized")
        
        try:
            print("🤖 Initializing orchestrator and agents...")
            self.orchestrator = SimpleOrchestrator()
            
            # Get system status
            status = self.orchestrator.get_agent_status()
            print(f"✅ System initialized with {status['total_agents']} agents")
            print("✅ Database loaded with schemes")
            
        except Exception as e:
            print(f"❌ Error initializing system: {str(e)}")
            logger.error(f"Error initializing bot: {str(e)}")
            raise
    
    def display_welcome_message(self):
        """Display welcome message and instructions"""
        print("\n" + "="*70)
        print("\n🌾 **Welcome to Simplified Multi-Agent Agriculture Bot!** 🌾")
        print("\nI'm your intelligent farming assistant powered by specialized AI agents.")
        
        status = self.orchestrator.get_agent_status()
        print(f"\n**🤖 Active Agents ({status['total_agents']}):**")
        for agent_name, details in status['agent_details'].items():
            print(f"• **{agent_name.replace('_', ' ').title()}**: {details['description']}")
        
        print("\n**🎯 What I Can Help You With:**")
        print("• Find relevant government agriculture schemes")
        print("• Explain eligibility criteria and benefits")
        print("• Guide you through application processes")
        print("• Provide state-specific scheme information")
        print("• Answer follow-up questions intelligently")
        
        print("\n**💬 Sample Questions:**")
        print('• "What schemes are available for small farmers?"')
        print('• "How can I get a loan for buying a tractor?"')
        print('• "What crop insurance options do I have?"')
        print('• "I\'m from Punjab, what subsidies are available?"')
        
        print("\n**🔧 Commands:**")
        print("• `help` - Show this help message")
        print("• `status` - Show system status")
        print("• `history` - Show conversation history")
        print("• `clear` - Clear conversation history")
        print("• `quit` or `exit` - Exit the bot")
        
        print("\n**💡 Tips:**")
        print("• Be specific about your farming needs")
        print("• Mention your location for better recommendations")
        print("• Ask follow-up questions for detailed information")
        print("• Use natural language - I understand context!")
        
        print(f"\nReady to help you access agricultural support! 🌱")
        print("\n" + "="*70)
    
    def handle_command(self, user_input: str) -> bool:
        """Handle special commands. Returns True if it was a command."""
        command = user_input.strip().lower()
        
        if command == 'help':
            self.display_welcome_message()
            return True
            
        elif command == 'status':
            status = self.orchestrator.get_agent_status()
            print(f"\n📊 **System Status:**")
            print(f"• Total Agents: {status['total_agents']}")
            print(f"• Active Agents: {', '.join(status['active_agents'])}")
            for agent_name, details in status['agent_details'].items():
                print(f"  - {agent_name}: {details['tools']} tools available")
            return True
            
        elif command == 'history':
            history = self.orchestrator.get_conversation_history()
            if history:
                print(f"\n📝 **Recent Conversation History:**")
                for i, query in enumerate(history[-5:], 1):  # Show last 5
                    print(f"{i}. {query}")
            else:
                print("\n📝 No conversation history available.")
            return True
            
        elif command == 'clear':
            self.orchestrator.clear_conversation_history()
            print("\n🗑️ Conversation history cleared!")
            return True
            
        elif command in ['quit', 'exit']:
            print("\n🌾 Thank you for using Simplified Multi-Agent Agriculture Bot!")
            print("Happy farming! 🌱")
            return True
            
        return False
    
    def chat_session(self):
        """Start interactive chat session"""
        self.display_welcome_message()
        
        while True:
            try:
                # Get user input
                user_input = input("\n🧑‍🌾 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if self.handle_command(user_input):
                    if user_input.lower() in ['quit', 'exit']:
                        break
                    continue
                
                # Process query through orchestrator
                print(f"\n🤖 Bot: ", end="", flush=True)
                response = self.orchestrator.process_query(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\n🌾 Thank you for using Simplified Multi-Agent Agriculture Bot!")
                print("Happy farming! 🌱")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                logger.error(f"Error in chat session: {str(e)}")
                print("Please try again.")


def main():
    """Main function to run the chatbot"""
    try:
        bot = SimplifiedMultiAgentBot()
        bot.chat_session()
    except Exception as e:
        print(f"❌ Failed to start bot: {str(e)}")
        logger.error(f"Failed to start bot: {str(e)}")


if __name__ == "__main__":
    main()
