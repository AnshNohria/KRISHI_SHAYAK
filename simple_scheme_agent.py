"""
Simple Scheme Agent for Agriculture Schemes Search and Information
"""
from typing import Dict, List, Any, Optional
import logging
from simple_base_agent import SimpleBaseAgent
from scheme_search_tool import SchemeSearchTool
from database import SchemesVectorDB

logger = logging.getLogger(__name__)


class SimpleSchemeAgent(SimpleBaseAgent):
    """Agent specialized in government agriculture schemes"""
    
    def __init__(self, db: SchemesVectorDB):
        # Initialize tools
        tools = [SchemeSearchTool(db)]
        
        super().__init__(
            name="scheme_agent",
            description="government agriculture schemes, subsidies, loans, and benefits",
            tools=tools
        )
        
        self.db = db
        logger.info("Simple Scheme Agent initialized")
    
    def should_use_tools(self, query: str, conversation_context: str = "") -> bool:
        """Use LLM to determine if tools are needed for scheme-related queries"""
        from langchain.prompts import ChatPromptTemplate
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing queries in conversation context to determine if they need database/tool assistance.

Analyze the user query along with conversation context to determine if it requires SEARCHING the agriculture schemes database.

Return "TRUE" if the query needs database search for:
- Specific scheme information, details, benefits, or eligibility NOT already covered in context
- Lists of schemes for particular purposes, locations, or categories beyond what's discussed  
- Current/latest scheme information not in previous conversation
- Application processes, documents, or procedures not already explained
- Scheme comparisons or recommendations requiring fresh database search
- Financial details, loan amounts, subsidy amounts not previously covered
- State-specific or location-based scheme information not in context
- Equipment, machinery, or specific agriculture-related schemes needing database lookup
- User provided new details requiring personalized scheme search

Return "FALSE" if the query:
- Is purely conversational or general
- Can be answered using information from the conversation context
- Is asking for clarification about schemes already discussed
- Is asking to choose between schemes already mentioned in context
- Is a greeting, thank you, or casual response
- Can be handled with schemes/information already provided in conversation

Consider both the conversation context and whether new database search is actually needed.

Respond with only "TRUE" or "FALSE"."""),
            ("user", f"Previous conversation context:\n{conversation_context if conversation_context else 'No previous conversation'}\n\nCurrent query: {query}\n\nConsidering the context, does this query need database/tool search for agriculture schemes?")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            decision = response.content.strip().upper()
            
            logger.info(f"LLM tool decision for query '{query[:50]}...': {decision}")
            return decision == "TRUE"
            
        except Exception as e:
            logger.error(f"Error in LLM tool decision: {str(e)}")
            # Conservative fallback - use tools when in doubt for scheme agent
            return True
    
    def generate_response_with_tool_result(self, query: str, tool_result: Dict[str, Any]) -> str:
        """Generate specialized response for scheme information"""
        from langchain.prompts import ChatPromptTemplate
        
        # Extract the actual result from the tool response
        actual_result = tool_result['result']
        if isinstance(actual_result, dict) and 'result' in actual_result:
            actual_result = actual_result['result']
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert agricultural advisor specializing in Indian government schemes and subsidies.

CRITICAL INSTRUCTION: You must ONLY use information from the search results provided below. Do NOT add any scheme details, benefits, eligibility criteria, application procedures, or other information from your training data or general knowledge.

RESPONSE STRUCTURE - Follow this format USING ONLY THE PROVIDED SEARCH RESULTS:

1. **Brief Summary (2-3 sentences)**: Give a concise overview of what schemes are available for the user's query BASED ONLY on the search results.

2. **Key Schemes Found**: List 3-4 most relevant schemes from the search results with:
   - Scheme name (exactly as mentioned in search results)
   - Brief benefit (ONLY as described in search results)
   - Basic eligibility (ONLY as mentioned in search results)

3. **Targeted Questions**: Ask 2-3 specific questions to help narrow down to the most relevant scheme:
   - Location/state (if not mentioned)
   - Land size or farming scale
   - Specific needs (loan amount, crop type, etc.)
   - Farmer category (if relevant)

4. **Next Step Promise**: End with "Once you provide these details, I can give you specific information about the most suitable scheme(s) for your situation, including exact benefits, eligibility criteria, application process, and required documents."

STRICT RULES:
- If search results are empty or insufficient, acknowledge this limitation
- Do not add scheme information that is not in the search results
- Do not mention specific amounts, procedures, or details not provided in results
- Keep the response CONCISE and FOCUSED on what was actually found

Remember: Base your entire response ONLY on the search results provided."""),
            ("user", f"User Query: {query}\n\nSearch Results: {actual_result}")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Error generating scheme response: {str(e)}")
            # Enhanced fallback response
            return self._format_raw_results(actual_result)
    
    def _format_raw_results(self, raw_result: Any) -> str:
        """Format raw search results into a readable response"""
        # Handle different result types
        if isinstance(raw_result, dict) and 'result' in raw_result:
            raw_result = raw_result['result']
        
        result_str = str(raw_result) if raw_result else ""
        
        if not result_str or result_str.strip() == "No relevant schemes found.":
            return """**Brief Summary:** I found some general agriculture schemes that might be relevant to your needs.

**Key Schemes Available:**
• **PM-KISAN Samman Nidhi** - Direct income support (₹6,000/year)
• **Kisan Credit Card (KCC)** - Low-interest agriculture credit
• **PMFBY Crop Insurance** - Protection against crop losses
• **State Agriculture Schemes** - Vary by location

**To Help You Better:**
1. **Which state are you from?**
2. **What's your land size?** (in hectares/acres)
3. **What specific support do you need?** (loan, subsidy, insurance, equipment)

Once you provide these details, I can give you specific information about the most suitable scheme(s) for your situation, including exact benefits, eligibility criteria, application process, and required documents."""
        
        # Try to format the raw result better
        return f"""**Brief Summary:** I found several relevant agriculture schemes based on your query.

**Search Results:**
{result_str}

**To Help You Better:**
1. **Which state are you from?**
2. **What's your land size and crop type?**
3. **Any specific requirements?** (loan amount, subsidy type, etc.)

Once you provide these details, I can give you specific information about the most suitable scheme(s) for your situation, including exact benefits, eligibility criteria, application process, and required documents."""
