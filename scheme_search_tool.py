"""
Scheme search tool for the agriculture chatbot
"""
from tool_interface import BaseTool
from database import SchemesVectorDB
from typing import Dict, Any, List
import re
import logging

logger = logging.getLogger(__name__)


class SchemeSearchTool(BaseTool):
    """Tool for searching agriculture schemes in the vector database"""
    
    def __init__(self, db: SchemesVectorDB = None):
        super().__init__(
            name="scheme_search",
            description="Search for relevant agriculture schemes based on user query"
        )
        self.db = db or SchemesVectorDB()
        
        # Initialize LLM for relevance detection
        from langchain_google_genai import ChatGoogleGenerativeAI
        import config
        
        self.llm = ChatGoogleGenerativeAI(
            model=config.LLM_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=0.1,  # Low temperature for consistent decisions
            convert_system_message_to_human=config.CONVERT_SYSTEM_MESSAGE_TO_HUMAN
        )
    
    def is_relevant(self, query: str, context: Dict[str, Any] = None) -> bool:
        """Use LLM to determine if this tool is relevant for the given query"""
        if not query:
            return False
        
        from langchain.prompts import ChatPromptTemplate
        
        # Extract conversation context if available
        conversation_context = ""
        if context:
            if context.get('conversation_summary'):
                conversation_context = context['conversation_summary']
            elif context.get('previous_topics'):
                conversation_context = f"Previous topics: {context['previous_topics']}"
            if context.get('force_scheme_search'):
                return True  # Explicit request to use scheme search
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at determining if queries need agriculture scheme database search in conversation context.

This tool searches for Indian government agriculture schemes, subsidies, loans, benefits, and programs.

Analyze the query along with conversation context to determine if scheme database search is needed.

Return "TRUE" if the query needs scheme database search for:
- Information about specific agriculture schemes, programs, or benefits NOT covered in context
- Government financial assistance, subsidies, or support programs requiring fresh search
- Loan schemes (KCC, tractor loans, equipment financing) needing database lookup
- Insurance programs (PMFBY, crop insurance) not already discussed
- Application processes, eligibility criteria, or documentation for new schemes
- State-specific or location-based agriculture schemes not in previous conversation
- Scheme comparisons or recommendations requiring database search
- Questions about PM-KISAN, PMFBY, or other specific schemes needing current info
- General requests for agriculture support when no relevant schemes discussed before
- User provided specific details (location, farm size) requiring personalized scheme search

Return "FALSE" if the query:
- Is purely conversational or greeting-like
- Asks for general farming advice without scheme context  
- Is about weather, prices, or market information
- Can be answered using schemes/information already discussed in context
- Is asking to choose between schemes already mentioned
- Is a casual acknowledgment or thank you
- Can be handled with previous conversation information

Consider the full conversation context when making this decision.

Respond with only "TRUE" or "FALSE"."""),
            ("user", f"Previous conversation context:\n{conversation_context if conversation_context else 'No previous conversation'}\n\nCurrent query: {query}\n\nConsidering the context, does this query need agriculture scheme database search?")
        ])
        
        try:
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            decision = response.content.strip().upper()
            
            logger.info(f"LLM relevance decision for query '{query[:50]}...': {decision}")
            return decision == "TRUE"
            
        except Exception as e:
            logger.error(f"Error in LLM relevance detection: {str(e)}")
            # Conservative fallback - return True for agriculture-related queries
            query_lower = query.lower()
            fallback_keywords = ['scheme', 'loan', 'subsidy', 'benefit', 'government', 'agriculture', 'farmer']
            return any(keyword in query_lower for keyword in fallback_keywords)
    
    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute the scheme search"""
        try:
            max_results = kwargs.get('max_results', 5)
            filters = kwargs.get('filters', {})
            
            logger.info(f"Executing scheme search for query: {query[:50]}...")
            
            # Intelligently optimize query for better search results
            optimized_query = self._intelligently_optimize_query(query)
            logger.info(f"Optimized query: {optimized_query[:100]}...")
            
            # Search the database
            results = self.db.search_schemes(
                query=optimized_query, 
                max_results=max_results,
                filters=filters
            )
            
            if not results:
                # Try a broader search if no results found
                broader_query = self._create_broader_query(query)
                logger.info(f"Trying broader query: {broader_query[:100]}...")
                results = self.db.search_schemes(
                    query=broader_query,
                    max_results=max_results,
                    filters=filters
                )
            
            # Format results for the chatbot
            formatted_results = self._format_results(results, query)
            
            return {
                'success': True,
                'result': formatted_results,
                'message': f"Found {len(results)} relevant agriculture schemes",
                'metadata': {
                    'query': query,
                    'optimized_query': optimized_query,
                    'total_results': len(results),
                    'search_type': 'semantic_search'
                }
            }
            
        except Exception as e:
            logger.error(f"Error in scheme search: {str(e)}")
            return {
                'success': False,
                'result': None,
                'message': f"Error searching schemes: {str(e)}",
                'metadata': {'error': str(e)}
            }
    
    def _intelligently_optimize_query(self, query: str) -> str:
        """Use LLM to intelligently optimize the search query based on context and intent"""
        query_lower = query.lower()
        
        # Extract the actual user query from context if present
        actual_user_query = self._extract_actual_user_query(query_lower)
        
        logger.info(f"Optimizing query with LLM. Actual user query: '{actual_user_query}'")
        
        # Use LLM to optimize the query
        try:
            from langchain.prompts import ChatPromptTemplate
            
            # Extract conversation context if available
            conversation_context = ""
            if "previous conversation context:" in query_lower:
                context_parts = query.split("Previous conversation context:")
                if len(context_parts) > 1:
                    context_section = context_parts[1].split("User's current input:")[0]
                    conversation_context = context_section.strip()
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert at optimizing search queries for agriculture scheme databases.

Your task is to create the BEST search query to find relevant government agriculture schemes.

Guidelines:
1. Focus PRIMARILY on the user's current query, not conversation history
2. Preserve specific scheme names exactly (PM Fasal Bima Yojana, PM-KISAN, PMFBY, KCC, etc.)
3. Include relevant agriculture keywords that help find schemes
4. Include location terms (state names) if mentioned
5. Include farming category terms (irrigation, loans, machinery, etc.) from current query
6. Keep the optimized query focused and under 15 words
7. Do NOT add unrelated terms from conversation history
8. Use terms that are likely to appear in agriculture scheme documents

Examples:
- User query: "PM Fasal Bima Yojana details" → "PM Fasal Bima Yojana PMFBY crop insurance scheme"
- User query: "irrigation schemes for Punjab" → "irrigation schemes Punjab water drip micro sprinkler"
- User query: "tractor loans" → "tractor loan KCC machinery equipment subsidy"
- User query: "schemes for Meghalaya farmers" → "schemes Meghalaya farmers agriculture subsidy benefit"

Return ONLY the optimized search query, nothing else."""),
                ("user", f"""Conversation Context (reference only, don't focus on this):
{conversation_context if conversation_context else 'No previous conversation'}

User's Current Query (MAIN FOCUS): {actual_user_query}

Generate the best search query to find relevant agriculture schemes for this user's current request.""")
            ])
            
            messages = prompt.format_messages()
            response = self.llm.invoke(messages)
            optimized_query = response.content.strip()
            
            logger.info(f"LLM optimized query: '{optimized_query}'")
            
            # Fallback if LLM returns empty or very short response
            if len(optimized_query) < 5:
                logger.warning("LLM optimization too short, using fallback")
                optimized_query = self._fallback_optimize(actual_user_query)
            
            return optimized_query
            
        except Exception as e:
            logger.error(f"Error in LLM query optimization: {str(e)}")
            # Fallback to rule-based optimization
            return self._fallback_optimize_focused(actual_user_query)
    
    def _fallback_optimize_focused(self, actual_query: str) -> str:
        """Focused fallback optimization using only the actual user query"""
        query_lower = actual_query.lower()
        
        # Key agriculture terms to preserve
        agriculture_terms = []
        
        # Preserve scheme names
        scheme_names = ['pm fasal bima', 'pmfby', 'pm-kisan', 'kcc', 'kisan credit card', 
                       'nabard', 'pmksy', 'krishi sinchai']
        for scheme in scheme_names:
            if scheme in query_lower:
                agriculture_terms.append(scheme)
        
        # Category terms
        if 'irrigation' in query_lower:
            agriculture_terms.extend(['irrigation', 'water', 'drip', 'micro'])
        elif 'loan' in query_lower:
            agriculture_terms.extend(['loan', 'credit', 'financing'])
        elif 'insurance' in query_lower:
            agriculture_terms.extend(['insurance', 'crop', 'protection'])
        elif 'tractor' in query_lower or 'machinery' in query_lower:
            agriculture_terms.extend(['tractor', 'machinery', 'equipment'])
        elif 'subsidy' in query_lower:
            agriculture_terms.extend(['subsidy', 'benefit', 'assistance'])
        
        # Location terms
        states = ['punjab', 'gujarat', 'haryana', 'rajasthan', 'maharashtra', 'karnataka',
                 'tamil nadu', 'andhra pradesh', 'telangana', 'odisha', 'west bengal',
                 'bihar', 'uttar pradesh', 'madhya pradesh', 'chhattisgarh',
                 'meghalaya', 'assam', 'kerala', 'goa', 'sikkim', 'himachal pradesh']
        
        for state in states:
            if state in query_lower:
                agriculture_terms.append(state)
        
        # Add general terms
        agriculture_terms.extend(['agriculture', 'scheme', 'farmer'])
        
        # Remove duplicates and combine
        unique_terms = []
        seen = set()
        for term in agriculture_terms:
            if term.lower() not in seen:
                unique_terms.append(term)
                seen.add(term.lower())
        
        return ' '.join(unique_terms[:12])  # Limit to 12 terms
    
    def _determine_scheme_intent_from_actual_query(self, actual_query: str) -> str:
        """Determine scheme intent from the actual user query only"""
        search_text = actual_query.lower()
        
        # STEP 1: Check for specific scheme names first and preserve them
        specific_schemes = []
        
        # Major scheme name patterns with variations
        scheme_patterns = {
            'PM Fasal Bima Yojana': ['pm fasal bima', 'pmfby', 'fasal bima', 'crop insurance pradhan mantri'],
            'PM-KISAN': ['pm kisan', 'pm-kisan', 'pradhan mantri kisan samman nidhi', 'kisan samman nidhi'],
            'Kisan Credit Card': ['kisan credit card', 'kcc', 'kisan credit'],
            'NABARD': ['nabard', 'national bank agriculture', 'rural development'],
            'Pradhan Mantri Krishi Sinchai Yojana': ['pmksy', 'krishi sinchai', 'irrigation pradhan mantri', 'micro irrigation'],
            'PM Kisan Maan Dhan Yojana': ['kisan maan dhan', 'pension scheme farmer'],
            'Paramparagat Krishi Vikas Yojana': ['pkvy', 'paramparagat krishi', 'organic farming cluster'],
            'National Mission for Sustainable Agriculture': ['nmsa', 'sustainable agriculture mission'],
            'Sub-Mission on Agricultural Mechanization': ['smam', 'mechanization', 'agricultural machinery'],
            'Rashtriya Krishi Vikas Yojana': ['rkvy', 'rashtriya krishi vikas', 'state agriculture development'],
            'National Food Security Mission': ['nfsm', 'food security mission'],
            'PM Annadata Aay SanraksHan Abhiyan': ['pm aasha', 'annadata aay', 'price support scheme'],
            'Soil Health Card': ['soil health card', 'soil testing'],
            'e-NAM': ['e-nam', 'national agriculture market', 'electronic market'],
            'Formation and Promotion of FPOs': ['fpo', 'farmer producer organization', 'farmer collective'],
            'National Beekeeping and Honey Mission': ['honey mission', 'beekeeping', 'sweet revolution'],
            'National Bamboo Mission': ['bamboo mission', 'bamboo cultivation']
        }
        
        # Check for specific scheme names in actual query
        for scheme_name, patterns in scheme_patterns.items():
            for pattern in patterns:
                if pattern in search_text:
                    specific_schemes.append(scheme_name)
                    logger.info(f"Found specific scheme in actual query: {scheme_name}")
                    break
        
        # STEP 2: Determine general category while preserving specific scheme names
        category_terms = []
        
        # If we found specific schemes, start with them
        if specific_schemes:
            category_terms.extend(specific_schemes)
        
        # Add category-based terms only if relevant and not already covered by specific schemes
        # Tractor and machinery related
        if any(word in search_text for word in ['tractor', 'machinery', 'equipment', 'implement', 'harvestor', 'thresher']):
            category_terms.extend(['tractor', 'machinery', 'equipment', 'agricultural mechanization', 'subsidy'])
        
        # Credit and loan related
        elif any(word in search_text for word in ['loan', 'credit', 'kcc', 'kisan credit card', 'financing']):
            category_terms.extend(['loan', 'credit', 'KCC', 'kisan credit card', 'agricultural financing'])
        
        # Insurance related - only add if no specific insurance scheme already found
        elif any(word in search_text for word in ['insurance', 'crop insurance', 'pmfby', 'protection', 'risk']):
            category_terms.extend(['crop insurance', 'PMFBY', 'protection', 'risk coverage'])
        
        # Irrigation related  
        elif any(word in search_text for word in ['irrigation', 'water', 'drip', 'sprinkler', 'micro irrigation', 'sinchai']):
            category_terms.extend(['irrigation', 'water', 'drip', 'sprinkler', 'micro irrigation', 'krishi sinchai'])
        
        # Income support related - only if no PM-KISAN already found
        elif any(word in search_text for word in ['income', 'direct benefit', 'transfer', 'payment']) and not any('kisan' in scheme.lower() for scheme in specific_schemes):
            category_terms.extend(['income support', 'direct benefit transfer', 'payment'])
        
        # Seed and fertilizer related
        elif any(word in search_text for word in ['seed', 'fertilizer', 'input', 'quality seed']):
            category_terms.extend(['seed', 'fertilizer', 'quality input', 'distribution', 'subsidy'])
        
        # Organic farming related
        elif any(word in search_text for word in ['organic', 'natural', 'sustainable', 'certification']):
            category_terms.extend(['organic farming', 'sustainable', 'natural', 'certification'])
        
        # Storage and infrastructure
        elif any(word in search_text for word in ['storage', 'warehouse', 'godown', 'infrastructure']):
            category_terms.extend(['storage', 'warehouse', 'godown', 'infrastructure', 'cold chain'])
        
        # Marketing and FPO
        elif any(word in search_text for word in ['market', 'marketing', 'fpo', 'cooperative', 'selling']):
            category_terms.extend(['marketing', 'FPO', 'farmer producer organization', 'cooperative'])
        
        # Only add general terms if we don't have specific schemes
        elif not specific_schemes:
            category_terms.extend(['agriculture', 'farming', 'scheme', 'subsidy', 'benefit'])
        
        # STEP 3: Combine specific schemes with category terms
        result = ' '.join(category_terms)
        
        # Ensure we have some content
        if not result.strip():
            result = 'agriculture farming scheme subsidy benefit'
        
        return result
    
    def _extract_actual_user_query(self, query_lower: str) -> str:
        """Extract the actual user query from context-enhanced queries"""
        if "user's current input:" in query_lower:
            parts = query_lower.split("user's current input:")
            if len(parts) > 1:
                user_part = parts[1]
                if "please provide" in user_part:
                    return user_part.split("please provide")[0].strip()
                else:
                    return user_part.strip().split('\n')[0].strip()
        elif "current query:" in query_lower:
            parts = query_lower.split("current query:")
            if len(parts) > 1:
                return parts[1].split("\n")[0].strip()
        
        return query_lower
    
    def _preserve_important_terms(self, query: str) -> str:
        """Preserve important terms like specific scheme names from the CURRENT query only"""
        important_terms = []
        query_lower = query.lower()
        
        # Preserve specific scheme name patterns exactly as they appear
        important_patterns = [
            # Exact scheme names to preserve
            'pm fasal bima yojana', 'pradhan mantri fasal bima yojana',
            'pm-kisan', 'pm kisan', 'pradhan mantri kisan samman nidhi',
            'kisan credit card', 'kcc',
            'pmfby', 'pm fasal bima', 'fasal bima',
            'pm krishi sinchai yojana', 'pmksy', 'krishi sinchai',
            'paramparagat krishi vikas yojana', 'pkvy',
            'rashtriya krishi vikas yojana', 'rkvy',
            'national food security mission', 'nfsm',
            'soil health card', 'e-nam',
            'nabard', 'farmer producer organization', 'fpo',
            # Important category terms - only preserve if they appear in ACTUAL query
            'tractor', 'machinery', 'equipment', 'loan', 'credit',
            'insurance', 'crop insurance', 'irrigation', 'subsidy',
            'organic farming', 'storage', 'warehouse'
        ]
        
        # Find and preserve these terms ONLY if they appear in the current user query
        # (not in conversation context)
        for pattern in important_patterns:
            if pattern in query_lower:
                # Check if this term is from the actual user query, not context
                if self._is_term_from_actual_query(pattern, query_lower):
                    important_terms.append(pattern)
                    logger.info(f"Preserving important term from current query: {pattern}")
        
        return ' '.join(important_terms)
    
    def _is_term_from_actual_query(self, term: str, full_query: str) -> bool:
        """Check if a term is from the actual user query, not conversation context"""
        # Extract the actual user input section
        if "user's current input:" in full_query:
            parts = full_query.split("user's current input:")
            if len(parts) > 1:
                user_section = parts[1].split('\n')[0].lower()
                return term in user_section
        elif "current query:" in full_query:
            parts = full_query.split("current query:")
            if len(parts) > 1:
                user_section = parts[1].split('\n')[0].lower()
                return term in user_section
        else:
            # If no context markers, assume the whole query is from user
            return True
        
        return False
    
    def _extract_context_info(self, query: str) -> str:
        """Extract MINIMAL context information from query - only what's truly relevant"""
        context_terms = []
        query_lower = query.lower()
        
        # Only add context terms if they are EXPLICITLY mentioned in conversation history
        # AND are relevant to the current query
        if 'previous conversation' in query_lower or 'context:' in query_lower:
            # Get the actual current query
            actual_query = self._extract_actual_user_query(query_lower)
            
            # Only add context terms that are DIRECTLY relevant to the current query
            if 'tractor' in actual_query and 'tractor' in query_lower:
                context_terms.append('tractor machinery')
            elif 'loan' in actual_query and 'loan' in query_lower:
                context_terms.append('loan credit')
            elif 'insurance' in actual_query and 'insurance' in query_lower:
                context_terms.append('insurance protection')
            elif 'irrigation' in actual_query and 'irrigation' in query_lower:
                context_terms.append('irrigation water')
        
        return ' '.join(context_terms)
    
    def _determine_scheme_intent(self, query: str) -> str:
        """Determine the primary scheme intent from the query while preserving specific scheme names"""
        query_lower = query.lower()
        
        # If it's a context-enhanced query, extract the actual user query
        actual_query = query_lower
        if "user's current input:" in query_lower:
            # Extract the actual user query from context-enhanced format
            parts = query_lower.split("user's current input:")
            if len(parts) > 1:
                # Get the part after "user's current input:" and before "please provide"
                user_part = parts[1]
                if "please provide" in user_part:
                    actual_query = user_part.split("please provide")[0].strip()
                else:
                    # Take everything after "user's current input:"
                    actual_query = user_part.strip()
                
                # Further clean by removing newlines and extra text
                actual_query = actual_query.split('\n')[0].strip()
                
        elif "current query:" in query_lower:
            # Alternative context format
            parts = query_lower.split("current query:")
            if len(parts) > 1:
                actual_query = parts[1].split("\n")[0].strip()
        
        # Debug logging
        if actual_query != query_lower:
            logger.info(f"Extracted actual query: '{actual_query}' from context query")
        
        # Use the extracted actual query for intent detection
        search_text = actual_query
        
        # STEP 1: Check for specific scheme names first and preserve them
        specific_schemes = []
        
        # Major scheme name patterns with variations
        scheme_patterns = {
            'PM Fasal Bima Yojana': ['pm fasal bima', 'pmfby', 'fasal bima', 'crop insurance pradhan mantri'],
            'PM-KISAN': ['pm kisan', 'pm-kisan', 'pradhan mantri kisan samman nidhi', 'kisan samman nidhi'],
            'Kisan Credit Card': ['kisan credit card', 'kcc', 'kisan credit'],
            'NABARD': ['nabard', 'national bank agriculture', 'rural development'],
            'Pradhan Mantri Krishi Sinchai Yojana': ['pmksy', 'krishi sinchai', 'irrigation pradhan mantri', 'micro irrigation'],
            'PM Kisan Maan Dhan Yojana': ['kisan maan dhan', 'pension scheme farmer'],
            'Paramparagat Krishi Vikas Yojana': ['pkvy', 'paramparagat krishi', 'organic farming cluster'],
            'National Mission for Sustainable Agriculture': ['nmsa', 'sustainable agriculture mission'],
            'Sub-Mission on Agricultural Mechanization': ['smam', 'mechanization', 'agricultural machinery'],
            'Rashtriya Krishi Vikas Yojana': ['rkvy', 'rashtriya krishi vikas', 'state agriculture development'],
            'National Food Security Mission': ['nfsm', 'food security mission'],
            'PM Annadata Aay SanraksHan Abhiyan': ['pm aasha', 'annadata aay', 'price support scheme'],
            'Soil Health Card': ['soil health card', 'soil testing'],
            'e-NAM': ['e-nam', 'national agriculture market', 'electronic market'],
            'Formation and Promotion of FPOs': ['fpo', 'farmer producer organization', 'farmer collective'],
            'National Beekeeping and Honey Mission': ['honey mission', 'beekeeping', 'sweet revolution'],
            'National Bamboo Mission': ['bamboo mission', 'bamboo cultivation']
        }
        
        # Check for specific scheme names
        for scheme_name, patterns in scheme_patterns.items():
            for pattern in patterns:
                if pattern in search_text:
                    specific_schemes.append(scheme_name)
                    logger.info(f"Found specific scheme: {scheme_name}")
                    break
        
        # STEP 2: Determine general category while preserving specific scheme names
        category_terms = []
        
        # If we found specific schemes, start with them
        if specific_schemes:
            category_terms.extend(specific_schemes)
        
        # Add category-based terms only if relevant and not already covered by specific schemes
        # Tractor and machinery related
        if any(word in search_text for word in ['tractor', 'machinery', 'equipment', 'implement', 'harvestor', 'thresher']):
            category_terms.extend(['tractor', 'machinery', 'equipment', 'agricultural mechanization', 'subsidy'])
        
        # Credit and loan related
        elif any(word in search_text for word in ['loan', 'credit', 'kcc', 'kisan credit card', 'financing']):
            category_terms.extend(['loan', 'credit', 'KCC', 'kisan credit card', 'agricultural financing'])
        
        # Insurance related - only add if no specific insurance scheme already found
        elif any(word in search_text for word in ['insurance', 'crop insurance', 'pmfby', 'protection', 'risk']):
            category_terms.extend(['crop insurance', 'PMFBY', 'protection', 'risk coverage'])
        
        # Income support related - only if no PM-KISAN already found
        elif any(word in search_text for word in ['income', 'direct benefit', 'transfer', 'payment']) and not any('kisan' in scheme.lower() for scheme in specific_schemes):
            category_terms.extend(['income support', 'direct benefit transfer', 'payment'])
        
        # Seed and fertilizer related
        elif any(word in search_text for word in ['seed', 'fertilizer', 'input', 'quality seed']):
            category_terms.extend(['seed', 'fertilizer', 'quality input', 'distribution', 'subsidy'])
        
        # Irrigation related  
        elif any(word in search_text for word in ['irrigation', 'water', 'drip', 'sprinkler', 'micro irrigation']):
            category_terms.extend(['irrigation', 'water', 'drip', 'sprinkler', 'micro irrigation'])
        
        # Organic farming related
        elif any(word in search_text for word in ['organic', 'natural', 'sustainable', 'certification']):
            category_terms.extend(['organic farming', 'sustainable', 'natural', 'certification'])
        
        # Storage and infrastructure
        elif any(word in search_text for word in ['storage', 'warehouse', 'godown', 'infrastructure']):
            category_terms.extend(['storage', 'warehouse', 'godown', 'infrastructure', 'cold chain'])
        
        # Marketing and FPO
        elif any(word in search_text for word in ['market', 'marketing', 'fpo', 'cooperative', 'selling']):
            category_terms.extend(['marketing', 'FPO', 'farmer producer organization', 'cooperative'])
        
        # Only add general terms if we don't have specific schemes
        elif not specific_schemes:
            category_terms.extend(['agriculture', 'farming', 'scheme', 'subsidy', 'benefit'])
        
        # STEP 3: Combine specific schemes with category terms
        result = ' '.join(category_terms)
        
        # Ensure we have some content
        if not result.strip():
            result = 'agriculture farming scheme subsidy benefit'
        
        return result
    
    def _extract_location_info(self, query: str) -> str:
        """Extract location information for state-specific schemes"""
        query_lower = query.lower()
        
        # Indian states mapping
        states = {
            'andhra pradesh': 'andhra pradesh state specific',
            'arunachal pradesh': 'arunachal pradesh northeast state',
            'assam': 'assam northeast tea state',
            'bihar': 'bihar state specific',
            'chhattisgarh': 'chhattisgarh state specific',
            'goa': 'goa state specific',
            'gujarat': 'gujarat state specific mechanization',
            'haryana': 'haryana punjab wheat rice state',
            'himachal pradesh': 'himachal pradesh hill state horticulture',
            'jharkhand': 'jharkhand state specific',
            'karnataka': 'karnataka state specific',
            'kerala': 'kerala state coconut spices',
            'madhya pradesh': 'madhya pradesh state specific',
            'maharashtra': 'maharashtra state specific',
            'manipur': 'manipur northeast state',
            'meghalaya': 'meghalaya northeast hill state',
            'mizoram': 'mizoram northeast state',
            'nagaland': 'nagaland northeast state',
            'odisha': 'odisha orissa state specific',
            'punjab': 'punjab haryana wheat rice mechanization',
            'rajasthan': 'rajasthan krishi yantra desert state',
            'sikkim': 'sikkim organic hill state',
            'tamil nadu': 'tamil nadu cooperative bank state',
            'telangana': 'telangana state specific',
            'tripura': 'tripura northeast state',
            'uttar pradesh': 'uttar pradesh UP state specific',
            'uttarakhand': 'uttarakhand hill state',
            'west bengal': 'west bengal state specific'
        }
        
        for state, terms in states.items():
            if state in query_lower:
                return terms
        
        # Union territories
        if 'delhi' in query_lower:
            return 'delhi NCR'
        elif 'chandigarh' in query_lower:
            return 'chandigarh punjab haryana'
        elif 'puducherry' in query_lower:
            return 'puducherry union territory'
        
        return ''
    
    def _extract_farmer_details(self, query: str) -> str:
        """Extract farmer category and details from the current query only"""
        query_lower = query.lower()
        farmer_terms = []
        
        # Only extract explicit farmer details mentioned in the query
        # Land size categories
        if any(size in query_lower for size in ['small farmer', 'marginal farmer']):
            farmer_terms.append('small marginal farmer')
        elif any(size in query_lower for size in ['large farmer', 'big farmer']):
            farmer_terms.append('large farmer')
        
        # Specific land sizes
        if 'hectare' in query_lower or 'acre' in query_lower:
            farmer_terms.append('landholding size')
        
        # Caste categories - only if explicitly mentioned
        if any(category in query_lower for category in ['sc farmer', 'st farmer', 'scheduled caste farmer', 'scheduled tribe farmer']):
            farmer_terms.append('SC ST scheduled caste tribe')
        elif 'obc farmer' in query_lower:
            farmer_terms.append('OBC other backward class')
        
        # Gender - only if explicitly mentioned  
        if any(gender in query_lower for gender in ['woman farmer', 'women farmer', 'female farmer']):
            farmer_terms.append('women farmer female')
        
        # Farming type - only if explicitly mentioned
        if any(farming in query_lower for farming in ['dairy farmer', 'livestock farmer', 'animal husbandry']):
            farmer_terms.append('dairy livestock animal husbandry')
        elif any(farming in query_lower for farming in ['horticulture farmer', 'fruit farmer', 'vegetable farmer']):
            farmer_terms.append('horticulture fruits vegetables')
        elif 'organic farmer' in query_lower:
            farmer_terms.append('organic natural farming')
        
        return ' '.join(farmer_terms)
    
    def _fallback_optimize(self, query: str) -> str:
        """Enhanced fallback optimization method"""
        # Extract actual user query if in context format
        actual_query = self._extract_actual_user_query(query.lower())
        
        # Use the focused fallback method
        return self._fallback_optimize_focused(actual_query)
    
    def _create_broader_query(self, original_query: str) -> str:
        """Create a broader query if original search yields no results"""
        query_lower = original_query.lower()
        
        # Map specific terms to broader categories
        broader_terms = {
            'insurance': 'crop insurance protection PMFBY risk coverage',
            'loan': 'credit financial assistance KCC kisan credit',
            'subsidy': 'financial support assistance benefit',
            'irrigation': 'water management drip sprinkler micro irrigation',
            'organic': 'sustainable farming organic certification',
            'equipment': 'machinery tools implements subsidy',
            'storage': 'warehouse godown storage infrastructure',
            'marketing': 'market linkage FPO farmer producer organization'
        }
        
        broader_query = "agriculture farmer scheme"
        
        for term, broader_term in broader_terms.items():
            if term in query_lower:
                broader_query += f" {broader_term}"
        
        return broader_query
    
    def _format_results(self, results: List[Dict], query: str) -> str:
        """Format search results for display"""
        if not results:
            return "I couldn't find any specific schemes matching your query. Please try with different keywords or ask about general agriculture schemes."
        
        formatted = f"🔍 **Found {len(results)} relevant agriculture schemes:**\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Unknown Scheme')
            state = result.get('state', 'All States')
            category = result.get('category', 'General')
            ministry = result.get('ministry', 'Government')
            similarity = result.get('similarity_score', 0)
            
            # Extract key information from content
            content = result.get('content', '')
            benefits = self._extract_benefits(content)
            eligibility = self._extract_eligibility(content)
            
            formatted += f"**{i}. {title}**\n"
            formatted += f"📍 **State:** {state}\n"
            formatted += f"🏛️ **Ministry:** {ministry}\n"
            formatted += f"📂 **Category:** {category}\n"
            formatted += f"⭐ **Relevance:** {similarity:.1%}\n"
            
            if benefits:
                formatted += f"💰 **Key Benefits:** {benefits[:200]}...\n"
            
            if eligibility:
                formatted += f"✅ **Eligibility:** {eligibility[:150]}...\n"
            
            if result.get('url'):
                formatted += f"🔗 **More Info:** {result['url']}\n"
            
            formatted += "\n"
            formatted += "---\n\n"
        
        # Add helpful footer
        formatted += "💡 **Need more specific information?** Ask me about eligibility, benefits, or application process for any of these schemes!"
        
        return formatted
    
    def _extract_benefits(self, content: str) -> str:
        """Extract benefits information from scheme content"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('Benefits:') and len(line) > 10:
                return line.replace('Benefits:', '').strip()
        return ""
    
    def _extract_eligibility(self, content: str) -> str:
        """Extract eligibility information from scheme content"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('Eligibility:') and len(line) > 15:
                return line.replace('Eligibility:', '').strip()
        return ""
    
    def search_by_category(self, category: str, max_results: int = 10) -> Dict[str, Any]:
        """Search schemes by category"""
        return self.execute(f"agriculture {category}", max_results=max_results)
    
    def search_by_state(self, state: str, max_results: int = 10) -> Dict[str, Any]:
        """Search schemes by state"""
        filters = {'state': state}
        return self.execute("agriculture schemes", max_results=max_results, filters=filters)
    
    def get_scheme_categories(self) -> List[str]:
        """Get list of available scheme categories"""
        try:
            stats = self.db.get_collection_stats()
            if 'sample_categories' in stats:
                return list(stats['sample_categories'].keys())
            return []
        except:
            return []


def main():
    """Test the scheme search tool"""
    # Initialize database first
    from data_processor import SchemesDataProcessor
    from database import SchemesVectorDB
    
    # Load data
    processor = SchemesDataProcessor("myscheme-gov-in-2025-08-10.xlsx")
    if processor.load_data():
        schemes = processor.process_schemes()
        
        # Initialize database
        db = SchemesVectorDB()
        db.add_schemes(schemes)
        
        # Initialize tool
        tool = SchemeSearchTool(db)
        
        # Test queries
        test_queries = [
            "I need financial assistance for my farm",
            "What crop insurance schemes are available?",
            "How can I get a loan for irrigation?",
            "PM-KISAN scheme details",
            "Subsidy for organic farming"
        ]
        
        print("=== Testing Scheme Search Tool ===\n")
        
        for query in test_queries:
            print(f"Query: {query}")
            print(f"Relevant: {tool.is_relevant(query)}")
            
            if tool.is_relevant(query):
                result = tool.execute(query, max_results=2)
                print(f"Success: {result['success']}")
                print(f"Message: {result['message']}")
                print(f"Results preview: {result['result'][:200]}...\n")
            
            print("---\n")


if __name__ == "__main__":
    main()
