"""
Simplified Base Agent Interface for Multi-Agent Agriculture System
Using direct tool calling instead of complex LangChain agents
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.tools import BaseTool
from conversation_context import ConversationContextManager, QueryContext
import config

logger = logging.getLogger(__name__)


class SimpleBaseAgent(ABC):
    """Simplified base class for all agents in the agriculture system"""
    
    def __init__(self, name: str, description: str, tools: List[BaseTool]):
        self.name = name
        self.description = description
        self.tools = tools
        self.context_manager = ConversationContextManager()
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=config.LLM_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=config.LLM_TEMPERATURE,
            convert_system_message_to_human=config.CONVERT_SYSTEM_MESSAGE_TO_HUMAN
        )
        
        logger.info(f"Initialized {name} agent with {len(tools)} tools")
    
    def process_query(self, query: str, context: Optional[QueryContext] = None) -> str:
        """Process a query using available tools"""
        try:
            # Extract conversation context for decision making
            conversation_context = ""
            if hasattr(self, 'context_manager') and self.context_manager:
                conversation_context = self.context_manager.get_conversation_summary(last_n=3)
            
            # Determine if tools are needed (with context)
            if self.should_use_tools(query, conversation_context):
                # Use tools to get information
                tool_result = self.use_tools(query)
                if tool_result:
                    return self.generate_response_with_tool_result(query, tool_result)
            
            # Generate direct response
            return self.generate_direct_response(query)
            
        except Exception as e:
            logger.error(f"Error in {self.name} processing query: {str(e)}")
            return f"I apologize, but I encountered an error while processing your request. Please try again."
    
    def should_use_tools(self, query: str, conversation_context: str = "") -> bool:
        """Use LLM to determine if the query requires tool usage"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are an expert at analyzing queries in conversation context to determine if they need tool assistance.

This agent specializes in: {self.description}

Analyze the user query along with conversation context to determine if it requires using tools/database search to get specific information.

Return "TRUE" if the query:
- Needs specific, detailed information that requires database/tool lookup not available in context
- Asks for current, specific, or detailed data beyond what was previously discussed
- Requests searches, lists, or comprehensive information not covered in context
- Needs factual information beyond general knowledge and previous conversation

Return "FALSE" if the query:
- Is conversational, general, or greeting-like
- Can be answered with general knowledge or information from conversation context
- Is asking for basic definitions or explanations
- Is a casual response, acknowledgment, or follow-up that doesn't need new data

Consider the agent's specialization and conversation context when making the decision.

Respond with only "TRUE" or "FALSE"."""),
            ("user", f"Previous conversation context:\n{conversation_context if conversation_context else 'No previous conversation'}\n\nCurrent query: {query}\n\nConsidering the context and agent specialization, does this query need tools/database search?")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            decision = response.content.strip().upper()
            
            logger.info(f"LLM tool decision for {self.name}: {decision}")
            return decision == "TRUE"
            
        except Exception as e:
            logger.error(f"Error in LLM tool decision: {str(e)}")
            # Conservative fallback - use tools when in doubt
            return True
    
    def use_tools(self, query: str) -> Optional[Dict[str, Any]]:
        """Use the first appropriate tool to get information"""
        if not self.tools:
            return None
        
        try:
            # For now, use the first tool (scheme search)
            tool = self.tools[0]
            
            # Check if tool has 'execute' method (our custom tools)
            if hasattr(tool, 'execute'):
                result = tool.execute(query)
            # Check if tool has 'run' method (LangChain tools)
            elif hasattr(tool, 'run'):
                result = tool.run(query)
            else:
                logger.error(f"Tool {tool.name} has no execute or run method")
                return None
                
            return {"tool_name": tool.name, "result": result}
        except Exception as e:
            logger.error(f"Error using tool: {str(e)}")
            return None
    
    def generate_response_with_tool_result(self, query: str, tool_result: Dict[str, Any]) -> str:
        """Generate response incorporating tool results"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a helpful AI assistant specializing in {self.description}.

CRITICAL INSTRUCTION: You must ONLY use the information provided in the tool results below. Do NOT add any information from your training data or general knowledge.

A user asked: "{query}"

I found the following relevant information using my tools:
{tool_result['result']}

STRICT GUIDELINES:
- Base your response ENTIRELY on the tool results provided
- Do NOT add scheme details, benefits, procedures, or other information not in the tool results  
- If the tool results are insufficient or empty, acknowledge this limitation
- Do NOT supplement with your general knowledge about agriculture schemes or programs
- If the results mention specific schemes, use ONLY the information provided about them
- Be farmer-friendly and practical, but stay within the bounds of provided information

Please provide a comprehensive, helpful response based STRICTLY on this information."""),
            ("user", query)
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            # Fallback to raw tool result
            return str(tool_result['result'])
    
    def generate_direct_response(self, query: str) -> str:
        """Generate a direct response without tools"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a helpful AI assistant specializing in {self.description}.

CRITICAL: You do NOT have access to current, specific information about government schemes, programs, or their details. Do NOT provide specific scheme names, benefits, eligibility criteria, application procedures, or contact information from your training data.

WHAT YOU CAN DO:
- Provide general guidance about the types of support available
- Suggest categories of programs that might be relevant
- Guide users on how to get specific, current information
- Be encouraging and supportive

WHAT YOU CANNOT DO:
- Mention specific scheme names, amounts, or benefits
- Provide detailed eligibility criteria or application processes
- Give specific contact information or deadlines
- Make up or assume details about government programs

Provide helpful guidance and suggest specific questions the user can ask to get the information they need.
Keep responses practical and farmer-friendly while being honest about your limitations."""),
            ("user", query)
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Error generating direct response: {str(e)}")
            return "I'm here to help with agriculture-related questions. Please feel free to ask about specific schemes, loans, or farming assistance programs."


class AgentRegistry:
    """Registry to manage all agents in the system"""
    
    def __init__(self):
        self.agents: Dict[str, SimpleBaseAgent] = {}
        logger.info("Agent registry initialized")
    
    def register_agent(self, agent: SimpleBaseAgent):
        """Register an agent"""
        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
    
    def get_agent(self, name: str) -> Optional[SimpleBaseAgent]:
        """Get agent by name"""
        return self.agents.get(name)
    
    def get_all_agents(self) -> Dict[str, SimpleBaseAgent]:
        """Get all registered agents"""
        return self.agents.copy()
    
    def find_relevant_agents(self, query: str, conversation_context: str = "") -> List[str]:
        """Use LLM to find agents that might be relevant to the query"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are an expert at routing queries to the most appropriate agent based on context.

Available agents and their specializations:
- scheme_agent: Government agriculture schemes, subsidies, loans, benefits, application processes, eligibility criteria, PM-KISAN, PMFBY, KCC, equipment schemes, state-specific programs
- price_agent: Market prices, costs, rates, buying/selling information
- weather_agent: Weather forecasts, climate information, seasonal planning
- crop_agent: Crop varieties, planting techniques, cultivation methods, harvest guidance

Analyze the user query along with conversation context to determine which agent(s) would be most relevant.

Rules:
1. Most agriculture-related queries about government support, financial assistance, or schemes should go to scheme_agent
2. Location-specific queries about farming support typically need scheme_agent
3. Questions about "which scheme to choose" or eligibility should go to scheme_agent
4. Follow-up questions about previously discussed schemes should go to scheme_agent
5. Consider conversation context - if schemes were discussed before, follow-ups likely need scheme_agent

Return the agent name(s) as a comma-separated list (e.g., "scheme_agent" or "scheme_agent,price_agent").
If no specific agent is clearly relevant, return "scheme_agent" as default for agriculture queries."""),
            ("user", f"Previous conversation context:\n{conversation_context if conversation_context else 'No previous conversation'}\n\nCurrent query: {query}\n\nConsidering the context, which agent(s) should handle this query?")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            agent_names = response.content.strip()
            
            # Parse the response and filter for existing agents
            relevant = []
            for name in agent_names.split(','):
                name = name.strip()
                if name in self.agents:
                    relevant.append(name)
            
            logger.info(f"LLM agent routing for query '{query[:50]}...': {relevant}")
            return relevant if relevant else ['scheme_agent'] if 'scheme_agent' in self.agents else list(self.agents.keys())[:1]
            
        except Exception as e:
            logger.error(f"Error in LLM agent routing: {str(e)}")
            # Fallback to scheme_agent for agriculture queries
            return ['scheme_agent'] if 'scheme_agent' in self.agents else list(self.agents.keys())[:1]
