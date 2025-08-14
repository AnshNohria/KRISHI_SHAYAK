"""
Simplified Orchestrator Agent for Multi-Agent Agriculture System
"""
from typing import Dict, List, Any, Optional
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from simple_base_agent import AgentRegistry
from simple_scheme_agent import SimpleSchemeAgent
from database import SchemesVectorDB
from conversation_context import ConversationContextManager
import config

logger = logging.getLogger(__name__)


class SimpleOrchestrator:
    """Simplified orchestrator to manage multi-agent conversations"""
    
    def __init__(self):
        self.agent_registry = AgentRegistry()
        self.context_manager = ConversationContextManager()
        
        # Initialize LLM for general responses
        self.llm = ChatGoogleGenerativeAI(
            model=config.LLM_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=config.LLM_TEMPERATURE,
            convert_system_message_to_human=config.CONVERT_SYSTEM_MESSAGE_TO_HUMAN
        )
        
        # Setup agents
        self._setup_agents()
        
        logger.info("Simple Orchestrator initialized")
    
    def _setup_agents(self):
        """Initialize and register all agents"""
        try:
            # Initialize database
            db = SchemesVectorDB()
            
            # Create and register Scheme Agent
            scheme_agent = SimpleSchemeAgent(db)
            self.agent_registry.register_agent(scheme_agent)
            
            logger.info("All agents registered successfully")
            
        except Exception as e:
            logger.error(f"Error setting up agents: {str(e)}")
            raise
    
    def process_query(self, query: str) -> str:
        """Process user query through appropriate agents"""
        try:
            logger.info(f"Processing query: {query[:50]}...")
            
            # Always try to get conversation context first
            conversation_summary = self.context_manager.get_conversation_summary(last_n=3)
            
            # Check if we have meaningful context
            has_context = len(self.context_manager.query_history) > 0
            
            if has_context:
                logger.info("Context available, attempting context-aware response first")
                
                # Always try context-first approach
                context_response = self._try_context_response(query, conversation_summary)
                
                if context_response:
                    logger.info("Successfully answered using context")
                    self._track_context(query, "context_based", "context_handler", context_response)
                    return context_response
                
                # If context isn't sufficient, check if we need agent help
                logger.info("Context insufficient, checking if agents can help")
                needs_agent = self._query_needs_agent_assistance(query, conversation_summary)
                
                if needs_agent:
                    logger.info("Query needs agent assistance with context")
                    
                    # Check if user provided details after previous brief response
                    user_provided_details = self._user_provided_details(query, conversation_summary)
                    
                    if user_provided_details:
                        # User provided details - give comprehensive, detailed response
                        enhanced_query = f"""Previous conversation context:
{conversation_summary}

User's current input with additional details: {query}

IMPORTANT: The user has provided specific details in response to previous questions. Now provide a DETAILED, COMPREHENSIVE response that includes:
1. Specific scheme recommendations based on their details
2. Exact eligibility criteria for their situation  
3. Specific benefits and amounts
4. Step-by-step application process
5. Required documents list
6. Contact information and deadlines
7. Any state-specific variations

Be thorough and actionable - this is when you should provide complete information."""
                    else:
                        # Regular context-enhanced query
                        enhanced_query = f"""Previous conversation context:
{conversation_summary}

User's current input: {query}

Please provide a brief, concise response that builds upon the previous discussion. Ask targeted follow-up questions to get specific details needed."""

                    relevant_agents = self.agent_registry.find_relevant_agents(enhanced_query, conversation_summary)
                    
                    if relevant_agents:
                        agent_name = relevant_agents[0]
                        agent = self.agent_registry.get_agent(agent_name)
                        if agent:
                            logger.info(f"Routing context-enhanced query to {agent_name}")
                            response = agent.process_query(enhanced_query)
                            self._track_context(query, "context_enhanced_search", agent_name, response)
                            return response
            
            # No context or context not helpful - process as new query
            logger.info("Processing as new query without context")
            relevant_agents = self.agent_registry.find_relevant_agents(query, conversation_summary)
            logger.info(f"Found {len(relevant_agents)} relevant agents for query")
            
            if relevant_agents:
                agent_name = relevant_agents[0]
                agent = self.agent_registry.get_agent(agent_name)
                
                if agent:
                    logger.info(f"Routing query to {agent_name}")
                    
                    # ALWAYS provide context if available, even for "new" queries
                    final_query = query
                    if has_context:
                        final_query = f"""Previous conversation context:
{conversation_summary}

User's current input: {query}

Please provide a comprehensive response that considers both the previous discussion and the new query. Reference the previous conversation when relevant."""
                        logger.info("Adding context to new query routing")
                    
                    response = agent.process_query(final_query)
                    self._track_context(query, "new_search_with_context" if has_context else "new_search", agent_name, response)
                    return response
            
            # Fallback to general response
            response = self._generate_general_response(query)
            self._track_context(query, "general", "general", response)
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return "I apologize, but I encountered an error while processing your request. Please try asking your question again."
    
    def _try_context_response(self, query: str, conversation_summary: str) -> str:
        """Try to answer the query using conversation context"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant for Indian farmers and agricultural stakeholders.

CRITICAL: You must ONLY provide information based on the conversation context provided below. Do NOT use your general knowledge or training data to add scheme details, benefits, or procedures that are not mentioned in the context.

The user is continuing a conversation about agriculture schemes. Based STRICTLY on the conversation context, provide a helpful response.

IMPORTANT GUIDELINES:
1. **Follow-up questions about SAME topic** (like "which one is best", "what about for my state", "I'm from X location"): Reference ONLY the schemes and information already discussed in the conversation context.

2. **User providing details** (like "Punjab, 2 hectares, tractor loan"): Use ONLY the schemes previously discussed in context + new details. If the context doesn't contain specific details about eligibility, benefits, or procedures, do NOT add them from your knowledge.

3. **Completely NEW topic** (asking about seeds/fertilizers when previous was about tractors): Return "NEED_DATABASE_SEARCH" for fresh information.

4. **Insufficient context**: If the conversation context doesn't contain enough information to answer the query properly, return "NEED_MORE_INFO" or "NEED_DATABASE_SEARCH".

STRICT RULE: Only use information that is explicitly mentioned in the conversation context below. Do not supplement with external knowledge about schemes, government programs, or procedures."""),
            ("user", f"Previous conversation:\n{conversation_summary}\n\nCurrent input: {query}\n\nProvide a detailed response if user provided specifics, or indicate if fresh database search is needed.")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            response_content = response.content.strip()
            
            # Check for indicators that agent search is needed
            if any(indicator in response_content.upper() for indicator in ["NEED_DATABASE_SEARCH", "NEED_MORE_INFO"]):
                return None
            
            return response_content
            
        except Exception as e:
            logger.error(f"Error in context response: {str(e)}")
            return None
    
    def _query_needs_agent_assistance(self, query: str, conversation_summary: str) -> bool:
        """Use LLM to determine if query needs agent assistance for new information"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing user queries in context to determine if they need database/agent assistance.

Analyze the current query along with the previous conversation context to determine if the user needs NEW INFORMATION from agents/tools.

Return "TRUE" if:
- User is asking for specific schemes, programs, or detailed information NOT already covered in the conversation
- User is asking about NEW topics/categories different from what was previously discussed
- User is requesting searches, lists, or comprehensive information beyond what's in context
- User provided specific details (location, land size, etc.) that require database lookup for personalized recommendations
- User is asking about latest/updated/current information not in previous discussion
- Query requires fresh database search even if topic was discussed before (like "show me more schemes")

Return "FALSE" if:
- User is asking follow-up questions about schemes/information already discussed in context
- User wants clarification, comparison, or recommendations from schemes already mentioned
- User is asking "which one should I choose" about options already presented
- Query can be adequately answered using the conversation history and context
- User is acknowledging or thanking for previous information

Consider the full conversation context when making this decision. The goal is to avoid unnecessary database calls when context can answer the query.

Respond with only "TRUE" or "FALSE"."""),
            ("user", f"Previous conversation context:\n{conversation_summary if conversation_summary else 'No previous conversation'}\n\nCurrent query: {query}\n\nBased on the conversation context and current query, does this need NEW information from agents/tools?")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            decision = response.content.strip().upper()
            
            # Return True if LLM says TRUE, otherwise False
            return decision == "TRUE"
            
        except Exception as e:
            logger.error(f"Error in LLM decision making: {str(e)}")
            # Fallback to conservative approach - use agents when in doubt
            return True
    
    def _needs_new_information(self, query: str) -> bool:
        """Use LLM to determine if a follow-up query needs new information from tools/agents"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing follow-up queries to determine if they need new database information.

Analyze the query to determine if it needs NEW INFORMATION from database/tools or can be answered from existing context.

Return "TRUE" if the query needs new information:
- Asking for more/additional/other schemes or options
- Requesting searches for different categories or types
- Looking for latest/updated/current information
- Asking about alternative or different solutions
- Requesting comprehensive lists or comparisons

Return "FALSE" if query can use existing context:
- Asking to choose/select from previously discussed options  
- Seeking recommendations from existing information
- Asking for clarification about previously mentioned schemes
- Questions about eligibility, application process of discussed schemes
- Comparing benefits of schemes already mentioned

Consider that this is typically a follow-up question in an ongoing conversation.

Respond with only "TRUE" or "FALSE"."""),
            ("user", f"Follow-up query: {query}\n\nDoes this need new information from database?")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            decision = response.content.strip().upper()
            
            return decision == "TRUE"
            
        except Exception as e:
            logger.error(f"Error in LLM new information decision: {str(e)}")
            # Conservative fallback - default to not needing new information for follow-ups
            return False
    
    def _user_provided_details(self, query: str, conversation_summary: str) -> bool:
        """Use LLM to check if user provided specific details in response to previous questions"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing conversations to detect when users provide specific details in context.

Analyze the conversation flow to determine if the user's current message contains SPECIFIC DETAILS that build upon or respond to the previous discussion.

Return "TRUE" if the user provided:
- Location/state information when previous context discussed schemes or asked for location
- Specific measurements (land size, area) relevant to agricultural schemes discussed
- Financial details, loan amounts, or budget information in context of schemes
- Multiple specific details that help narrow down scheme recommendations
- Personal/farm details that respond to previous questions or scheme discussions
- Specific categories or types (like crop type, farming scale) relevant to context

Return "FALSE" if:
- User is asking general questions without providing context-relevant specifics
- Query doesn't contain actionable details for scheme recommendations
- Details provided are not relevant to the previous conversation topic
- User is just asking questions without giving information about their situation

IMPORTANT: Consider the conversation context. Details are only meaningful if they relate to what was previously discussed and can help provide better, more targeted recommendations.

Respond with only "TRUE" or "FALSE"."""),
            ("user", f"Previous conversation context:\n{conversation_summary if conversation_summary else 'No previous conversation - this is the first message'}\n\nCurrent user message: {query}\n\nConsidering the conversation context, did the user provide specific actionable details?")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            decision = response.content.strip().upper()
            
            return decision == "TRUE"
            
        except Exception as e:
            logger.error(f"Error in LLM detail detection: {str(e)}")
            # Fallback - look for basic patterns
            return ',' in query and len(query.split(',')) >= 2
    
    
    def _track_context(self, query: str, intent: str, agent_used: str, response: str):
        """Helper method to track context"""
        try:
            from conversation_context import QueryContext
            from datetime import datetime
            context = QueryContext(
                query=query,
                timestamp=datetime.now(),
                intent=intent,
                entities={},
                agent_used=agent_used,
                response_summary=response  # Store full response without truncation
            )
            self.context_manager.add_query(context)
        except Exception as ctx_e:
            logger.warning(f"Context tracking failed: {str(ctx_e)}")
    
    def _generate_followup_response(self, original_query: str, conversation_summary: str) -> str:
        """Generate a context-aware follow-up response"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant for Indian farmers and agricultural stakeholders.

The user is asking a follow-up question related to our previous conversation. Use the conversation context to provide a relevant, helpful response.

Be specific and reference the previous discussion. If the follow-up is about choosing between options discussed earlier, provide clear recommendations based on the user's situation.

Keep responses farmer-friendly and practical."""),
            ("user", f"Previous conversation:\n{conversation_summary}\n\nCurrent question: {original_query}")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Error generating follow-up response: {str(e)}")
            return self._generate_general_response(original_query)
    
    def _generate_general_response(self, query: str) -> str:
        """Generate a general response when no agents are relevant"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant for Indian farmers and agricultural stakeholders.

CRITICAL: You cannot access specific information about government agriculture schemes, subsidies, or programs. Do NOT provide specific scheme names, benefits, eligibility criteria, or application procedures from your training data.

When you cannot find specific information to answer a user's query, provide general guidance and suggest how they can get the specific information they need.

STRICT GUIDELINES:
- Do NOT mention specific scheme names (like PM-KISAN, PMFBY, etc.) unless they were mentioned in the user's query
- Do NOT provide specific benefits amounts, eligibility criteria, or application procedures
- Do NOT give detailed step-by-step processes for schemes
- Do ONLY provide general categories of support available and direct them to get specific information

Be encouraging, supportive, and provide practical next steps. Mention that they can ask about:
- Government agriculture schemes and subsidies
- Crop-specific assistance programs  
- State-specific farming support
- Application processes for various schemes

Keep responses farmer-friendly and avoid technical jargon. Focus on being helpful while being honest about your limitations."""),
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
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        agents = self.agent_registry.get_all_agents()
        return {
            "total_agents": len(agents),
            "active_agents": list(agents.keys()),
            "agent_details": {
                name: {
                    "description": agent.description,
                    "tools": len(agent.tools)
                }
                for name, agent in agents.items()
            }
        }
    
    def get_conversation_history(self) -> List[str]:
        """Get recent conversation history"""
        try:
            history = []
            for query_ctx in self.context_manager.query_history:
                timestamp = query_ctx.timestamp.strftime("%H:%M")
                history.append(f"[{timestamp}] User: {query_ctx.query}")
                if query_ctx.response_summary:
                    history.append(f"[{timestamp}] Bot: {query_ctx.response_summary}")
            return history
        except Exception as e:
            logger.warning(f"Failed to get conversation history: {str(e)}")
            return []
    
    def clear_conversation_history(self):
        """Clear conversation history"""
        try:
            self.context_manager.clear_session()
            logger.info("Conversation history cleared")
        except Exception as e:
            logger.warning(f"Failed to clear conversation history: {str(e)}")
