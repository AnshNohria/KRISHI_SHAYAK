"""
Conversation Context Manager for Multi-Agent Agriculture Chatbot
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class QueryContext:
    """Context information for a single query"""
    query: str
    timestamp: datetime
    intent: str
    entities: Dict[str, Any]
    agent_used: Optional[str] = None
    tools_used: List[str] = None
    response_summary: str = ""


@dataclass
class UserProfile:
    """User profile to maintain farming context"""
    location: Optional[str] = None
    crops_of_interest: List[str] = None
    farming_type: Optional[str] = None  # small, large, organic, etc.
    schemes_applied: List[str] = None
    preferences: Dict[str, Any] = None


class ConversationContextManager:
    """Manages conversation context across multiple agents and queries"""
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.query_history: List[QueryContext] = []
        self.user_profile = UserProfile(
            crops_of_interest=[],
            schemes_applied=[],
            preferences={}
        )
        self.current_session_entities = {}
        self.last_agent_used = None
        self.last_tool_results = {}
    
    def add_query(self, query_context: QueryContext):
        """Add a new query to the conversation history"""
        self.query_history.append(query_context)
        
        # Keep only recent history
        if len(self.query_history) > self.max_history:
            self.query_history = self.query_history[-self.max_history:]
        
        # Update session entities
        self.current_session_entities.update(query_context.entities)
        
        # Track last agent used
        if query_context.agent_used:
            self.last_agent_used = query_context.agent_used
        
        logger.info(f"Added query to context: {query_context.query[:50]}...")
    
    def get_conversation_summary(self, last_n: int = 3) -> str:
        """Get a summary of recent conversation for context"""
        if not self.query_history:
            return "No previous conversation."
        
        recent_queries = self.query_history[-last_n:] if last_n else self.query_history
        
        summary = "Recent conversation:\n"
        for i, context in enumerate(recent_queries, 1):
            summary += f"{i}. User: {context.query}\n"
            if context.agent_used:
                summary += f"   Agent: {context.agent_used}\n"
            if context.response_summary:
                summary += f"   Response: {context.response_summary}\n"  # Full response without truncation
            summary += "\n"
        
        return summary
    
    def is_followup_query(self, query: str) -> bool:
        """Determine if the current query is a follow-up to previous conversation"""
        if not self.query_history:
            return False
        
        query_lower = query.lower()
        
        # Direct reference indicators
        followup_indicators = [
            'tell me more', 'more details', 'more information', 'elaborate',
            'what about', 'how about', 'and what', 'also tell',
            'the first one', 'the second one', 'that scheme', 'this scheme',
            'it', 'that', 'those', 'these', 'them',
            'eligibility', 'how to apply', 'documents required', 'benefits',
            'application process', 'contact details'
        ]
        
        # Check for direct indicators
        for indicator in followup_indicators:
            if indicator in query_lower:
                return True
        
        # Check for pronouns that likely refer to previous content
        pronouns = ['it', 'that', 'this', 'those', 'these', 'them', 'they']
        query_words = query_lower.split()
        
        for pronoun in pronouns:
            if pronoun in query_words:
                return True
        
        # Check if query is asking for specific details about something mentioned earlier
        last_query = self.query_history[-1]
        if last_query.agent_used == 'scheme_agent':
            # If last query was about schemes, check for detail requests
            detail_requests = [
                'eligibility', 'apply', 'documents', 'benefits', 'process',
                'requirements', 'form', 'office', 'contact', 'deadline'
            ]
            
            for detail in detail_requests:
                if detail in query_lower:
                    return True
        
        return False
    
    def get_relevant_entities(self) -> Dict[str, Any]:
        """Get entities relevant to current conversation"""
        entities = {}
        
        # Merge entities from recent queries
        for query_context in self.query_history[-3:]:  # Last 3 queries
            entities.update(query_context.entities)
        
        # Add user profile information
        if self.user_profile.location:
            entities['location'] = self.user_profile.location
        
        if self.user_profile.crops_of_interest:
            entities['crops'] = self.user_profile.crops_of_interest
        
        return entities
    
    def extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities from a query (basic implementation)"""
        entities = {}
        query_lower = query.lower()
        
        # Common Indian states (for agriculture context)
        indian_states = [
            'punjab', 'haryana', 'uttar pradesh', 'up', 'bihar', 'west bengal',
            'maharashtra', 'karnataka', 'tamil nadu', 'andhra pradesh',
            'telangana', 'gujarat', 'rajasthan', 'madhya pradesh', 'mp',
            'odisha', 'jharkhand', 'chhattisgarh', 'himachal pradesh',
            'uttarakhand', 'assam', 'kerala', 'goa', 'meghalaya'
        ]
        
        # Common crops
        crops = [
            'rice', 'wheat', 'cotton', 'sugarcane', 'maize', 'corn',
            'soybean', 'groundnut', 'mustard', 'bajra', 'jowar',
            'gram', 'tur', 'arhar', 'urad', 'moong', 'lentil',
            'onion', 'potato', 'tomato', 'chili', 'turmeric'
        ]
        
        # Common scheme keywords
        schemes = [
            'pm-kisan', 'pmkisan', 'pradhan mantri kisan samman nidhi',
            'pmfby', 'fasal bima', 'crop insurance', 'kisan credit card',
            'kcc', 'soil health card', 'pmksy', 'irrigation'
        ]
        
        # Extract states
        for state in indian_states:
            if state in query_lower:
                entities['state'] = state.title()
                break
        
        # Extract crops
        found_crops = []
        for crop in crops:
            if crop in query_lower:
                found_crops.append(crop.title())
        if found_crops:
            entities['crops'] = found_crops
        
        # Extract schemes
        found_schemes = []
        for scheme in schemes:
            if scheme in query_lower:
                found_schemes.append(scheme.upper())
        if found_schemes:
            entities['schemes'] = found_schemes
        
        # Extract monetary amounts (basic)
        import re
        money_pattern = r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)|(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rupees?|rs\.?|lakh|crore)'
        money_matches = re.findall(money_pattern, query_lower)
        if money_matches:
            entities['monetary_amounts'] = [match[0] or match[1] for match in money_matches]
        
        return entities
    
    def classify_intent(self, query: str) -> str:
        """Use LLM to classify the intent of the query"""
        # Import here to avoid circular imports
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain.prompts import ChatPromptTemplate
        import config
        
        try:
            llm = ChatGoogleGenerativeAI(
                model=config.LLM_MODEL,
                google_api_key=config.GEMINI_API_KEY,
                temperature=0.1,  # Low temperature for consistent classification
                convert_system_message_to_human=config.CONVERT_SYSTEM_MESSAGE_TO_HUMAN
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert at classifying user queries related to agriculture and government schemes.

Classify the user query into one of these intent categories:

1. **scheme_search** - Looking for schemes, programs, or general scheme information
2. **scheme_application** - How to apply, application process, forms, procedures
3. **scheme_eligibility** - Eligibility criteria, who can apply, qualification requirements
4. **scheme_benefits** - Benefits, amounts, financial details of schemes
5. **price_query** - Market prices, crop prices, selling rates
6. **price_trend** - Price trends, forecasts, predictions
7. **weather_query** - Weather information, climate, rainfall
8. **farming_advice** - Cultivation techniques, crop guidance, farming practices
9. **information_request** - General questions seeking information (what, how, when, where)
10. **followup** - Follow-up questions building on previous conversation
11. **general** - Casual conversation, greetings, or unclear intent

Respond with only the intent category name (e.g., "scheme_search")."""),
                ("user", f"Query: {query}\n\nWhat is the intent of this query?")
            ])
            
            messages = prompt.format_messages()
            response = llm.invoke(messages)
            intent = response.content.strip().lower()
            
            # Validate the intent is one of the expected categories
            valid_intents = [
                'scheme_search', 'scheme_application', 'scheme_eligibility', 'scheme_benefits',
                'price_query', 'price_trend', 'weather_query', 'farming_advice', 
                'information_request', 'followup', 'general'
            ]
            
            if intent in valid_intents:
                return intent
            else:
                # Default fallback
                return 'general'
                
        except Exception as e:
            logger.error(f"Error in LLM intent classification: {str(e)}")
            # Fallback to simple keyword-based classification
            return self._fallback_classify_intent(query)
    
    def _fallback_classify_intent(self, query: str) -> str:
        """Fallback keyword-based intent classification"""
        query_lower = query.lower()
        
        # Scheme-related intents
        if any(word in query_lower for word in ['scheme', 'subsidy', 'benefit', 'assistance', 'yojana', 'pm-kisan', 'insurance']):
            if any(word in query_lower for word in ['apply', 'application', 'how to', 'process']):
                return 'scheme_application'
            elif any(word in query_lower for word in ['eligibility', 'eligible', 'qualify', 'criteria']):
                return 'scheme_eligibility'
            elif any(word in query_lower for word in ['benefit', 'amount', 'money', 'financial']):
                return 'scheme_benefits'
            else:
                return 'scheme_search'
        
        # Price-related intents
        elif any(word in query_lower for word in ['price', 'cost', 'rate', 'market', 'selling']):
            if any(word in query_lower for word in ['trend', 'forecast', 'prediction', 'future']):
                return 'price_trend'
            else:
                return 'price_query'
        
        # Weather-related intents
        elif any(word in query_lower for word in ['weather', 'rain', 'temperature', 'climate']):
            return 'weather_query'
        
        # Farming advice
        elif any(word in query_lower for word in ['crop', 'farming', 'cultivation', 'fertilizer', 'pesticide']):
            return 'farming_advice'
        
        # General information
        elif any(word in query_lower for word in ['what', 'how', 'when', 'where', 'why']):
            return 'information_request'
        
        # Follow-up or clarification
        elif self.is_followup_query(query):
            return 'followup'
        
        else:
            return 'general'
    
    def should_route_to_agent(self, query: str, intent: str) -> bool:
        """Determine if query should be routed to an agent or handled as follow-up"""
        # If it's a clear follow-up, don't route to new agent
        if intent == 'followup' and self.last_agent_used:
            return False
        
        # If it's a new query with clear intent, route to agent
        if intent in ['scheme_search', 'scheme_application', 'scheme_eligibility', 'scheme_benefits']:
            return True
        
        # For other intents, check if we have relevant context
        if intent in ['price_query', 'price_trend', 'weather_query', 'farming_advice']:
            return True  # Will route to appropriate agent when implemented
        
        return True  # Default to routing
    
    def update_user_profile(self, entities: Dict[str, Any]):
        """Update user profile based on extracted entities"""
        if 'state' in entities and not self.user_profile.location:
            self.user_profile.location = entities['state']
        
        if 'crops' in entities:
            for crop in entities['crops']:
                if crop not in self.user_profile.crops_of_interest:
                    self.user_profile.crops_of_interest.append(crop)
        
        if 'schemes' in entities:
            for scheme in entities['schemes']:
                if scheme not in self.user_profile.schemes_applied:
                    self.user_profile.schemes_applied.append(scheme)
    
    def get_context_for_agent(self, agent_name: str) -> Dict[str, Any]:
        """Get relevant context for a specific agent"""
        context = {
            'conversation_summary': self.get_conversation_summary(3),
            'user_profile': self.user_profile,
            'relevant_entities': self.get_relevant_entities(),
            'is_followup': len(self.query_history) > 0 and self.is_followup_query(self.query_history[-1].query if self.query_history else ""),
            'last_agent': self.last_agent_used,
            'session_entities': self.current_session_entities
        }
        
        # Agent-specific context
        if agent_name == 'scheme_agent':
            context['last_schemes_discussed'] = []
            for query_ctx in self.query_history[-3:]:
                if query_ctx.agent_used == 'scheme_agent' and query_ctx.tools_used:
                    context['last_schemes_discussed'].extend(query_ctx.tools_used)
        
        return context
    
    def clear_session(self):
        """Clear current session while keeping user profile"""
        self.query_history.clear()
        self.current_session_entities.clear()
        self.last_agent_used = None
        self.last_tool_results.clear()
        logger.info("Conversation context cleared")


def main():
    """Test the context manager"""
    context_mgr = ConversationContextManager()
    
    # Test queries
    test_queries = [
        "What schemes are available for small farmers?",
        "Tell me more about PM-KISAN",
        "What are the eligibility criteria?",
        "How to apply for it?",
        "What about crop insurance schemes?",
    ]
    
    for query in test_queries:
        entities = context_mgr.extract_entities(query)
        intent = context_mgr.classify_intent(query)
        is_followup = context_mgr.is_followup_query(query)
        should_route = context_mgr.should_route_to_agent(query, intent)
        
        print(f"\nQuery: {query}")
        print(f"Intent: {intent}")
        print(f"Entities: {entities}")
        print(f"Is Follow-up: {is_followup}")
        print(f"Should Route: {should_route}")
        
        # Add to context
        query_context = QueryContext(
            query=query,
            timestamp=datetime.now(),
            intent=intent,
            entities=entities,
            agent_used='scheme_agent' if 'scheme' in intent else None
        )
        context_mgr.add_query(query_context)
        context_mgr.update_user_profile(entities)


if __name__ == "__main__":
    main()
