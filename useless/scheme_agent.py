"""
Scheme Agent - Specialized agent for handling agriculture scheme queries using LangChain
"""
from typing import Dict, List, Any, Optional
import logging
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage

from base_agent import BaseAgent
from database import SchemesVectorDB
from conversation_context import ConversationContextManager

logger = logging.getLogger(__name__)


class SchemeSearchTool:
    """LangChain-compatible tool for searching agriculture schemes"""
    
    def __init__(self, db: SchemesVectorDB):
        self.db = db
        self.name = "search_agriculture_schemes"
        self.description = """
        Search for relevant agriculture schemes based on user query.
        Input should be a search query describing the type of scheme, assistance, or benefit needed.
        Examples: 'crop insurance schemes', 'financial assistance for small farmers', 'PM-KISAN details'
        """
    
    def _run(self, query: str) -> str:
        """Execute the scheme search"""
        try:
            # Search the database
            results = self.db.search_schemes(query, max_results=5)
            
            if not results:
                return "No relevant schemes found for your query. Please try different keywords or ask about general agriculture schemes."
            
            # Format results for the agent
            formatted_response = f"Found {len(results)} relevant agriculture schemes:\n\n"
            
            for i, result in enumerate(results, 1):
                title = result.get('title', 'Unknown Scheme')
                state = result.get('state', 'All States')
                category = result.get('category', 'General')
                ministry = result.get('ministry', 'Government')
                similarity = result.get('similarity_score', 0)
                url = result.get('url', '')
                
                # Extract key information from content
                content = result.get('content', '')
                benefits = self._extract_section(content, 'Benefits')
                eligibility = self._extract_section(content, 'Eligibility')
                application = self._extract_section(content, 'Application Process')
                
                formatted_response += f"**{i}. {title}**\n"
                formatted_response += f"📍 State: {state}\n"
                formatted_response += f"🏛️ Ministry: {ministry}\n"
                formatted_response += f"📂 Category: {category}\n"
                formatted_response += f"⭐ Relevance: {similarity:.1%}\n"
                
                if benefits:
                    formatted_response += f"💰 Benefits: {benefits[:200]}...\n"
                
                if eligibility:
                    formatted_response += f"✅ Eligibility: {eligibility[:150]}...\n"
                
                if application:
                    formatted_response += f"📝 Application: {application[:150]}...\n"
                
                if url:
                    formatted_response += f"🔗 More Info: {url}\n"
                
                formatted_response += "\n---\n\n"
            
            formatted_response += "💡 Need specific details about any scheme? Just ask!"
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error in scheme search tool: {str(e)}")
            return f"I encountered an error while searching for schemes: {str(e)}. Please try again."
    
    def _extract_section(self, content: str, section_name: str) -> str:
        """Extract a specific section from scheme content"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith(f'{section_name}:') and len(line) > len(section_name) + 5:
                return line.replace(f'{section_name}:', '').strip()
        return ""


class SchemeAgent(BaseAgent):
    """Specialized agent for handling agriculture scheme queries"""
    
    def __init__(self, db: SchemesVectorDB = None):
        # Initialize database
        self.db = db or SchemesVectorDB()
        
        # Create the scheme search tool
        scheme_search_tool = SchemeSearchTool(self.db)
        
        # Convert to LangChain tool
        langchain_tool = Tool(
            name=scheme_search_tool.name,
            description=scheme_search_tool.description,
            func=scheme_search_tool._run
        )
        
        # Initialize base agent
        super().__init__(
            name="scheme_agent",
            description="Expert agent for finding and explaining government agriculture schemes, subsidies, and benefits",
            tools=[langchain_tool]
        )
        
        # Scheme-specific keywords for relevance detection
        self.scheme_keywords = {
            'scheme', 'schemes', 'program', 'programs', 'yojana', 'benefit', 'benefits',
            'eligibility', 'apply', 'application', 'subsidy', 'subsidies', 'assistance',
            'insurance', 'loan', 'credit', 'financial', 'government', 'support',
            'farmer', 'agriculture', 'agricultural', 'crop', 'crops', 'kisan',
            'PM-KISAN', 'PMFBY', 'KCC', 'pradhan mantri', 'funding', 'grant',
            'compensation', 'relief', 'welfare', 'development', 'rural',
            'ministry', 'department', 'central', 'state'
        }
    
    def create_agent_prompt(self) -> ChatPromptTemplate:
        """Create the specialized prompt for the scheme agent"""
        system_message = """You are SchemeBot, an expert AI agent specialized in Indian government agriculture schemes and subsidies.

Your primary role is to help farmers and agricultural stakeholders find, understand, and access relevant government schemes.

**Core Capabilities:**
1. **Scheme Discovery**: Use the search_agriculture_schemes tool to find relevant schemes
2. **Detailed Explanation**: Provide comprehensive information about scheme benefits, eligibility, and application processes
3. **Personalized Guidance**: Consider user's location, crops, and farming type when recommending schemes
4. **Application Support**: Guide users through application processes and requirements

**Response Guidelines:**
- Always use the search tool when users ask about schemes, benefits, or assistance
- Provide clear, farmer-friendly explanations
- Structure responses with clear headings and bullet points
- Include specific scheme names, benefits amounts, and application procedures
- Mention contact information or official websites when available
- Be encouraging and supportive in tone

**Context Awareness:**
- Pay attention to user's location (state) to recommend state-specific schemes
- Consider previously discussed schemes in follow-up questions
- If user asks "what about eligibility?" after scheme search, provide eligibility details without new search

**Important:**
- Base responses on actual search results, not assumptions
- If no relevant schemes found, suggest broader categories or alternative keywords
- Always encourage farmers to verify latest information from official sources

{context}"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
    
    def is_relevant_for_query(self, query: str, context: Dict[str, Any] = None) -> bool:
        """Determine if this agent should handle the query"""
        if not query:
            return False
        
        query_lower = query.lower()
        
        # Check for scheme-related keywords
        for keyword in self.scheme_keywords:
            if keyword in query_lower:
                return True
        
        # Check for question patterns that typically require scheme information
        import re
        scheme_patterns = [
            r'\b(what|which|how)\s+.*\s+(scheme|program|benefit|subsidy|assistance)',
            r'\b(help|support|financial)\s+.*\s+(farmer|agriculture|farming)',
            r'\b(apply|eligible|qualify)\s+.*',
            r'\b(government|central|state)\s+.*\s+(scheme|program|support)',
            r'\b(crop|irrigation|soil|livestock|fisheries)\s+.*\s+(scheme|support|insurance)',
            r'\b(PM-KISAN|PMFBY|KCC|pradhan mantri)\b',
        ]
        
        for pattern in scheme_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # Context-based relevance
        if context:
            # If previous conversation mentioned schemes
            conv_summary = context.get('conversation_summary', '')
            if any(word in conv_summary.lower() for word in ['scheme', 'benefit', 'subsidy']):
                # Check if this could be a follow-up about schemes
                followup_indicators = [
                    'eligibility', 'how to apply', 'documents', 'benefits',
                    'application process', 'more details', 'tell me more'
                ]
                for indicator in followup_indicators:
                    if indicator in query_lower:
                        return True
            
            # If user explicitly asked for scheme search
            if context.get('force_scheme_search'):
                return True
            
            # If last agent was scheme agent and this looks like follow-up
            if context.get('last_agent') == 'scheme_agent' and context.get('is_followup'):
                return True
        
        return False
    
    def get_scheme_by_name(self, scheme_name: str) -> Optional[Dict]:
        """Get specific scheme details by name"""
        try:
            results = self.db.search_schemes(scheme_name, max_results=1)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error getting scheme by name: {str(e)}")
            return None
    
    def get_schemes_by_category(self, category: str, max_results: int = 5) -> List[Dict]:
        """Get schemes by category"""
        try:
            query = f"agriculture {category} schemes"
            return self.db.search_schemes(query, max_results)
        except Exception as e:
            logger.error(f"Error getting schemes by category: {str(e)}")
            return []
    
    def get_schemes_by_state(self, state: str, max_results: int = 5) -> List[Dict]:
        """Get schemes available in a specific state"""
        try:
            filters = {'state': state}
            return self.db.search_schemes("agriculture schemes", max_results, filters)
        except Exception as e:
            logger.error(f"Error getting schemes by state: {str(e)}")
            return []
    
    def handle_followup_query(self, query: str, context: Dict[str, Any]) -> str:
        """Handle follow-up queries without using tools"""
        query_lower = query.lower()
        
        # Common follow-up patterns
        if any(word in query_lower for word in ['eligibility', 'eligible', 'qualify', 'criteria']):
            return "To provide specific eligibility criteria, I would need to search for the scheme you're interested in. Please mention the scheme name or ask me to search for schemes in your area of interest."
        
        elif any(word in query_lower for word in ['apply', 'application', 'how to']):
            return "To guide you through the application process, please specify which scheme you're interested in, or let me search for relevant schemes based on your needs."
        
        elif any(word in query_lower for word in ['benefits', 'amount', 'money', 'subsidy amount']):
            return "To provide specific benefit amounts, please mention the scheme name or describe the type of assistance you're looking for."
        
        elif any(word in query_lower for word in ['documents', 'papers', 'requirements']):
            return "Document requirements vary by scheme. Please specify which scheme you're asking about, or let me search for schemes relevant to your farming needs."
        
        else:
            return "I'd be happy to help! Please ask me about specific schemes, or describe what type of agricultural assistance or support you're looking for."


def main():
    """Test the Scheme Agent"""
    from database import SchemesVectorDB
    from conversation_context import ConversationContextManager, QueryContext
    from datetime import datetime
    
    # Initialize components
    db = SchemesVectorDB()
    scheme_agent = SchemeAgent(db)
    context_mgr = ConversationContextManager()
    
    # Test queries
    test_queries = [
        "What schemes are available for small farmers?",
        "PM-KISAN scheme details",
        "I need crop insurance information",
        "What are the eligibility criteria?",  # Follow-up
        "How to apply for it?"  # Follow-up
    ]
    
    print("🌾 Testing Scheme Agent with LangChain")
    print("=" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        
        # Extract entities and classify intent
        entities = context_mgr.extract_entities(query)
        intent = context_mgr.classify_intent(query)
        is_followup = context_mgr.is_followup_query(query)
        
        print(f"   Intent: {intent}")
        print(f"   Follow-up: {is_followup}")
        print(f"   Entities: {entities}")
        
        # Check if agent is relevant
        context_dict = context_mgr.get_context_for_agent('scheme_agent')
        is_relevant = scheme_agent.is_relevant_for_query(query, context_dict)
        print(f"   Agent Relevant: {is_relevant}")
        
        if is_relevant:
            # Process with agent
            result = scheme_agent.process_query(query, context_dict)
            print(f"   Success: {result['success']}")
            print(f"   Tools Used: {result['tools_used']}")
            print(f"   Response: {result['response'][:200]}...")
            
            # Add to context
            query_context = QueryContext(
                query=query,
                timestamp=datetime.now(),
                intent=intent,
                entities=entities,
                agent_used='scheme_agent',
                tools_used=result['tools_used'],
                response_summary=result['response'][:100]
            )
            context_mgr.add_query(query_context)
            context_mgr.update_user_profile(entities)
        
        print("-" * 40)


if __name__ == "__main__":
    main()
