"""
Orchestrator Agent - Routes queries to appropriate specialized agents using LangChain
"""
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage, HumanMessage, SystemMessage

from base_agent import BaseAgent, AgentRegistry
from scheme_agent import SchemeAgent
from conversation_context import ConversationContextManager, QueryContext
from database import SchemesVectorDB
import config

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Master orchestrator that routes queries to appropriate specialized agents
    and handles conversation flow management
    """
    
    def __init__(self):
        # Initialize components
        self.context_manager = ConversationContextManager()
        self.agent_registry = AgentRegistry()
        
        # Initialize LLM for orchestrator decisions
        self.llm = ChatGoogleGenerativeAI(
            model=config.LLM_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.1,
            convert_system_message_to_human=config.CONVERT_SYSTEM_MESSAGE_TO_HUMAN
        )
        
        # Initialize and register agents
        self._setup_agents()
        
        logger.info("Orchestrator Agent initialized")
    
    def _setup_agents(self):
        """Initialize and register all specialized agents"""
        try:
            # Initialize database
            db = SchemesVectorDB()
            
            # Create and register Scheme Agent
            scheme_agent = SchemeAgent(db)
            self.agent_registry.register_agent(scheme_agent)
            
            logger.info("All agents registered successfully")
            
        except Exception as e:
            logger.error(f"Error setting up agents: {str(e)}")
            raise
    
    def process_query(self, query: str) -> str:
        """
        Process a user query by routing to appropriate agent(s) or handling as follow-up
        """
        try:
            logger.info(f"Processing query: {query[:100]}...")
            
            # Extract entities and classify intent
            entities = self.context_manager.extract_entities(query)
            intent = self.context_manager.classify_intent(query)
            is_followup = self.context_manager.is_followup_query(query)
            
            # Get context for decision making
            context = self.context_manager.get_context_for_agent('orchestrator')
            
            # Decide how to handle the query
            if is_followup and self.context_manager.last_agent_used:
                response = self._handle_followup_query(query, intent, entities, context)
            else:
                response = self._route_to_agent(query, intent, entities, context)
            
            # Update conversation context
            query_context = QueryContext(
                query=query,
                timestamp=datetime.now(),
                intent=intent,
                entities=entities,
                agent_used=getattr(self, '_last_agent_used', None),
                tools_used=getattr(self, '_last_tools_used', []),
                response_summary=response[:100] + "..." if len(response) > 100 else response
            )
            
            self.context_manager.add_query(query_context)
            self.context_manager.update_user_profile(entities)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return "I apologize, but I encountered an error while processing your request. Please try asking your question again or rephrase it."
    
    def _handle_followup_query(self, query: str, intent: str, entities: Dict, context: Dict) -> str:
        """Handle follow-up queries that don't need new agent routing"""
        last_agent_name = self.context_manager.last_agent_used
        
        if not last_agent_name:
            return self._route_to_agent(query, intent, entities, context)
        
        # Get the last agent
        last_agent = self.agent_registry.get_agent(last_agent_name)
        if not last_agent:
            return self._route_to_agent(query, intent, entities, context)
        
        # Check if the follow-up is still relevant to the same agent
        if last_agent.is_relevant_for_query(query, context):
            logger.info(f"Routing follow-up to {last_agent_name}")
            
            # For scheme agent, check if it can handle without tools
            if last_agent_name == 'scheme_agent' and self._is_simple_followup(query):
                return self._generate_contextual_response(query, context)
            
            # Otherwise, route to the agent
            result = last_agent.process_query(query, context)
            self._last_agent_used = last_agent_name
            self._last_tools_used = result.get('tools_used', [])
            
            return result.get('response', 'I apologize, but I could not generate a response.')
        
        else:
            # Follow-up is not relevant to last agent, route to new agent
            return self._route_to_agent(query, intent, entities, context)
    
    def _route_to_agent(self, query: str, intent: str, entities: Dict, context: Dict) -> str:
        """Route query to the most appropriate agent"""
        # Find relevant agents
        relevant_agents = self.agent_registry.find_relevant_agents(query, context)
        
        if not relevant_agents:
            return self._generate_general_response(query, intent, entities)
        
        # For now, use the first relevant agent (can be enhanced with scoring)
        selected_agent = relevant_agents[0]
        
        logger.info(f"Routing query to {selected_agent.name}")
        
        # Get agent-specific context
        agent_context = self.context_manager.get_context_for_agent(selected_agent.name)
        
        # Process query with selected agent
        result = selected_agent.process_query(query, agent_context)
        
        # Store for follow-up handling
        self._last_agent_used = selected_agent.name
        self._last_tools_used = result.get('tools_used', [])
        
        if result.get('success'):
            return result.get('response', 'No response generated')
        else:
            error_msg = result.get('response', 'Agent processing failed')
            return f"I encountered an issue: {error_msg}. Please try rephrasing your question."
    
    def _is_simple_followup(self, query: str) -> bool:
        """Check if query is a simple follow-up that doesn't need tool execution"""
        query_lower = query.lower()
        
        simple_followup_patterns = [
            'tell me more', 'more details', 'elaborate', 'explain',
            'what about', 'how about', 'and what about',
            'the first one', 'the second one', 'that scheme', 'this one'
        ]
        
        for pattern in simple_followup_patterns:
            if pattern in query_lower:
                return True
        
        return False
    
    def _generate_contextual_response(self, query: str, context: Dict) -> str:
        """Generate a contextual response without using agent tools"""
        conversation_summary = context.get('conversation_summary', '')
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant specializing in agriculture schemes and farming support.
            
Based on the recent conversation history, provide a helpful response to the user's follow-up question.
Keep your response informative, farmer-friendly, and encourage the user to ask for specific details if they need them.

If you cannot provide specific information based on the conversation history, politely guide them to ask more specific questions."""),
            ("user", f"""Recent conversation:
{conversation_summary}

Current follow-up question: {query}

Please provide a helpful response based on the conversation context.""")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Error generating contextual response: {str(e)}")
            return "I'd be happy to help! Could you please be more specific about what you'd like to know?"
    
    def _generate_general_response(self, query: str, intent: str, entities: Dict) -> str:
        """Generate a general response when no agents are relevant"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant for Indian farmers and agricultural stakeholders.

When you cannot find specific information to answer a user's query, provide general guidance and suggest how they can get the specific information they need.

Be encouraging, supportive, and provide practical next steps. Mention that they can ask about:
- Government agriculture schemes and subsidies
- Crop-specific assistance programs  
- State-specific farming support
- Application processes for various schemes

Keep responses farmer-friendly and avoid technical jargon."""),
            ("user", f"User query: {query}\n\nPlease provide a helpful general response and guide them on how to get specific information.")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Error generating general response: {str(e)}")
            return """I'm here to help you with agriculture-related questions! I can assist you with:

🌾 **Government Schemes**: Information about schemes like PM-KISAN, PMFBY, KCC, and state-specific programs
🎯 **Eligibility & Benefits**: Details about who can apply and what benefits are available
📝 **Application Processes**: Step-by-step guidance on how to apply
📍 **Location-Specific Info**: Schemes available in your state or region

Please feel free to ask about any specific agriculture scheme, farming assistance, or support program you're interested in!"""
    
    def get_conversation_history(self) -> str:
        """Get formatted conversation history"""
        return self.context_manager.get_conversation_summary()
    
    def clear_conversation(self):
        """Clear conversation context"""
        self.context_manager.clear_session()
        logger.info("Conversation cleared by user")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all system components"""
        agents_info = self.agent_registry.list_agents()
        
        stats = {
            'total_agents': len(agents_info),
            'agents': agents_info,
            'conversation_history_length': len(self.context_manager.query_history),
            'last_agent_used': self.context_manager.last_agent_used,
            'user_profile': {
                'location': self.context_manager.user_profile.location,
                'crops_of_interest': self.context_manager.user_profile.crops_of_interest,
                'schemes_applied': self.context_manager.user_profile.schemes_applied
            }
        }
        
        # Add database stats for scheme agent
        scheme_agent = self.agent_registry.get_agent('scheme_agent')
        if scheme_agent:
            try:
                db_stats = scheme_agent.db.get_collection_stats()
                stats['database'] = db_stats
            except:
                stats['database'] = {'status': 'unavailable'}
        
        return stats
    
    def suggest_queries(self) -> List[str]:
        """Suggest relevant queries based on conversation context"""
        base_suggestions = [
            "What schemes are available for small farmers?",
            "How can I apply for crop insurance?",
            "Tell me about PM-KISAN scheme",
            "What subsidies are available for irrigation?",
            "How to get Kisan Credit Card?"
        ]
        
        # Add context-based suggestions
        user_profile = self.context_manager.user_profile
        
        contextual_suggestions = []
        
        if user_profile.location:
            contextual_suggestions.append(f"What schemes are available in {user_profile.location}?")
        
        if user_profile.crops_of_interest:
            for crop in user_profile.crops_of_interest[:2]:  # Limit to 2 crops
                contextual_suggestions.append(f"What support is available for {crop.lower()} farming?")
        
        # Combine and return
        all_suggestions = contextual_suggestions + base_suggestions
        return all_suggestions[:5]  # Return top 5 suggestions


def main():
    """Test the Orchestrator Agent"""
    print("🤖 Testing Orchestrator Agent")
    print("=" * 50)
    
    orchestrator = OrchestratorAgent()
    
    # Test conversation flow
    test_conversation = [
        "What schemes are available for small farmers?",
        "Tell me more about PM-KISAN",
        "What are the eligibility criteria?",
        "How to apply for it?",
        "What about crop insurance schemes?",
    ]
    
    for i, query in enumerate(test_conversation, 1):
        print(f"\n{i}. User: {query}")
        response = orchestrator.process_query(query)
        print(f"   Bot: {response[:200]}...")
        print(f"   Last Agent: {orchestrator.context_manager.last_agent_used}")
        print("-" * 30)
    
    # Test system status
    print(f"\n📊 System Status:")
    status = orchestrator.get_system_status()
    print(f"   Agents: {status['total_agents']}")
    print(f"   Conversation Length: {status['conversation_history_length']}")
    print(f"   User Location: {status['user_profile']['location']}")
    print(f"   Database Schemes: {status.get('database', {}).get('total_schemes', 'N/A')}")
    
    # Test suggestions
    print(f"\n💡 Suggested Queries:")
    for suggestion in orchestrator.suggest_queries():
        print(f"   - {suggestion}")


if __name__ == "__main__":
    main()
