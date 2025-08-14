"""
Base Agent Interface for Multi-Agent Agriculture System using LangChain
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging
from langchain.agents import AgentExecutor
from langchain.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import AgentAction, AgentFinish
from conversation_context import ConversationContextManager, QueryContext
import config

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents in the agriculture system"""
    
    def __init__(self, name: str, description: str, tools: List[BaseTool] = None):
        self.name = name
        self.description = description
        self.tools = tools or []
        
        # Initialize LangChain LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.1
        )
        
        # Agent executor will be set up by subclasses
        self.agent_executor = None
        
        logger.info(f"Initialized {name} agent with {len(self.tools)} tools")
    
    @abstractmethod
    def create_agent_prompt(self) -> ChatPromptTemplate:
        """Create the prompt template for this agent"""
        pass
    
    @abstractmethod
    def is_relevant_for_query(self, query: str, context: Dict[str, Any] = None) -> bool:
        """Determine if this agent should handle the query"""
        pass
    
    def setup_agent(self):
        """Setup the LangChain agent executor"""
        if not self.tools:
            logger.warning(f"No tools provided for {self.name} agent")
            return
        
        prompt = self.create_agent_prompt()
        
        # Create agent
        agent = (
            {
                "input": lambda x: x["input"],
                "agent_scratchpad": lambda x: format_to_openai_function_messages(
                    x["intermediate_steps"]
                ),
                "context": lambda x: x.get("context", ""),
            }
            | prompt
            | self.llm.bind_functions(self.tools)
            | OpenAIFunctionsAgentOutputParser()
        )
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=3,
            early_stopping_method="generate"
        )
        
        logger.info(f"Agent executor setup complete for {self.name}")
    
    def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a query using this agent"""
        if not self.agent_executor:
            self.setup_agent()
        
        if not self.agent_executor:
            return {
                'success': False,
                'response': "Agent not properly initialized",
                'agent_name': self.name,
                'tools_used': [],
                'metadata': {'error': 'Agent initialization failed'}
            }
        
        try:
            context_str = self._format_context(context) if context else ""
            
            result = self.agent_executor.invoke({
                "input": query,
                "context": context_str
            })
            
            return {
                'success': True,
                'response': result.get('output', 'No response generated'),
                'agent_name': self.name,
                'tools_used': self._extract_tools_used(result),
                'metadata': {
                    'intermediate_steps': result.get('intermediate_steps', []),
                    'context_used': context_str
                }
            }
            
        except Exception as e:
            logger.error(f"Error in {self.name} agent: {str(e)}")
            return {
                'success': False,
                'response': f"I encountered an error while processing your query: {str(e)}",
                'agent_name': self.name,
                'tools_used': [],
                'metadata': {'error': str(e)}
            }
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for the agent"""
        if not context:
            return ""
        
        formatted_context = []
        
        if context.get('conversation_summary'):
            formatted_context.append(f"Previous conversation:\n{context['conversation_summary']}")
        
        if context.get('user_profile'):
            profile = context['user_profile']
            if profile.location:
                formatted_context.append(f"User location: {profile.location}")
            if profile.crops_of_interest:
                formatted_context.append(f"User's crops of interest: {', '.join(profile.crops_of_interest)}")
        
        if context.get('relevant_entities'):
            entities = context['relevant_entities']
            if entities:
                formatted_context.append(f"Relevant entities: {entities}")
        
        if context.get('is_followup'):
            formatted_context.append("This appears to be a follow-up question to the previous conversation.")
        
        return "\n\n".join(formatted_context)
    
    def _extract_tools_used(self, result: Dict[str, Any]) -> List[str]:
        """Extract names of tools used from agent result"""
        tools_used = []
        
        intermediate_steps = result.get('intermediate_steps', [])
        for step in intermediate_steps:
            if isinstance(step, tuple) and len(step) >= 2:
                action = step[0]
                if isinstance(action, AgentAction):
                    tools_used.append(action.tool)
        
        return tools_used
    
    def add_tool(self, tool: BaseTool):
        """Add a new tool to this agent"""
        self.tools.append(tool)
        logger.info(f"Added tool {tool.name} to {self.name} agent")
        
        # Re-setup agent if it was already initialized
        if self.agent_executor:
            self.setup_agent()
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about this agent"""
        return {
            'name': self.name,
            'description': self.description,
            'tool_count': len(self.tools),
            'tools': [tool.name for tool in self.tools],
            'initialized': self.agent_executor is not None
        }


class AgentRegistry:
    """Registry to manage all agents in the system"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        logger.info("Agent registry initialized")
    
    def register_agent(self, agent: BaseAgent):
        """Register a new agent"""
        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name"""
        return self.agents.get(name)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents"""
        return [agent.get_info() for agent in self.agents.values()]
    
    def find_relevant_agents(self, query: str, context: Dict[str, Any] = None) -> List[BaseAgent]:
        """Find agents relevant for a given query"""
        relevant_agents = []
        
        for agent in self.agents.values():
            if agent.is_relevant_for_query(query, context):
                relevant_agents.append(agent)
        
        logger.info(f"Found {len(relevant_agents)} relevant agents for query")
        return relevant_agents
    
    def remove_agent(self, name: str):
        """Remove an agent from registry"""
        if name in self.agents:
            del self.agents[name]
            logger.info(f"Removed agent: {name}")
        else:
            logger.warning(f"Agent {name} not found for removal")


def main():
    """Test the base agent infrastructure"""
    from langchain.tools import Tool
    
    # Create a simple test tool
    def test_tool_func(query: str) -> str:
        return f"Test tool executed with: {query}"
    
    test_tool = Tool(
        name="test_tool",
        description="A simple test tool",
        func=test_tool_func
    )
    
    # This is just for testing - we'll implement actual agents separately
    class TestAgent(BaseAgent):
        def create_agent_prompt(self):
            return ChatPromptTemplate.from_messages([
                ("system", "You are a test agent."),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
        
        def is_relevant_for_query(self, query: str, context: Dict[str, Any] = None) -> bool:
            return "test" in query.lower()
    
    # Test the infrastructure
    registry = AgentRegistry()
    test_agent = TestAgent("test_agent", "A test agent", [test_tool])
    
    registry.register_agent(test_agent)
    
    print("Agent Registry Test:")
    for agent_info in registry.list_agents():
        print(f"- {agent_info['name']}: {agent_info['description']}")
        print(f"  Tools: {agent_info['tools']}")
        print(f"  Initialized: {agent_info['initialized']}")


if __name__ == "__main__":
    main()
