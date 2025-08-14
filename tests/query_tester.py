"""
ChromaDB Query Tester - Test and inspect ChromaDB search results
"""
import json
from typing import List, Dict, Optional
from datetime import datetime
from database import SchemesVectorDB
from scheme_search_tool import SchemeSearchTool
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ChromaDBQueryTester:
    """Interactive tool to test and inspect ChromaDB queries"""
    
    def __init__(self):
        self.db = SchemesVectorDB()
        self.search_tool = SchemeSearchTool(self.db)
        
    def test_raw_query(self, query: str, max_results: int = 5) -> Dict:
        """Test raw ChromaDB query and return detailed results"""
        print(f"\n{'='*60}")
        print(f"🔍 RAW CHROMADB QUERY: '{query}'")
        print(f"{'='*60}")
        
        try:
            # Get raw ChromaDB results
            results = self.db.search_schemes(query, max_results)
            
            print(f"📊 **Query Statistics:**")
            print(f"   - Query: {query}")
            print(f"   - Max Results: {max_results}")
            print(f"   - Results Found: {len(results)}")
            print()
            
            # Display each result in detail
            for i, result in enumerate(results, 1):
                print(f"🎯 **Result #{i}**")
                print(f"   📝 Title: {result.get('title', 'N/A')}")
                print(f"   📍 State: {result.get('state', 'N/A')}")
                print(f"   🏛️ Ministry: {result.get('ministry', 'N/A')}")
                print(f"   📂 Category: {result.get('category', 'N/A')}")
                print(f"   ⭐ Similarity Score: {result.get('similarity_score', 0):.4f}")
                print(f"   🔗 URL: {result.get('url', 'N/A')}")
                
                # Show content preview
                content = result.get('content', '')
                if content:
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"   📄 Content Preview: {content_preview}")
                
                print(f"   {'─' * 50}")
                print()
            
            return {
                'query': query,
                'total_results': len(results),
                'results': results
            }
            
        except Exception as e:
            print(f"❌ Error executing query: {str(e)}")
            return {'error': str(e)}
    
    def test_tool_query(self, query: str, max_results: int = 5) -> Dict:
        """Test query through the scheme search tool"""
        print(f"\n{'='*60}")
        print(f"🛠️ TOOL-BASED QUERY: '{query}'")
        print(f"{'='*60}")
        
        try:
            # Check if tool considers query relevant
            is_relevant = self.search_tool.is_relevant(query)
            print(f"🤔 **Tool Relevance Check:**")
            print(f"   - Query: {query}")
            print(f"   - Is Relevant: {'✅ Yes' if is_relevant else '❌ No'}")
            print()
            
            if is_relevant:
                # Execute through tool
                result = self.search_tool.execute(query, max_results=max_results)
                
                print(f"📊 **Tool Execution Results:**")
                print(f"   - Success: {'✅ Yes' if result['success'] else '❌ No'}")
                print(f"   - Message: {result.get('message', 'N/A')}")
                print()
                
                if result['success']:
                    print(f"📝 **Formatted Response:**")
                    print(result.get('result', 'No formatted result available'))
                    print()
                    
                    # Show metadata
                    metadata = result.get('metadata', {})
                    if metadata:
                        print(f"🔍 **Query Metadata:**")
                        print(f"   - Original Query: {metadata.get('query', 'N/A')}")
                        print(f"   - Optimized Query: {metadata.get('optimized_query', 'N/A')}")
                        print(f"   - Total Results: {metadata.get('total_results', 'N/A')}")
                        print(f"   - Search Type: {metadata.get('search_type', 'N/A')}")
                        print()
                
                return result
            else:
                print("🚫 Tool determined query is not relevant for scheme search.")
                return {'relevant': False}
                
        except Exception as e:
            print(f"❌ Error executing tool query: {str(e)}")
            return {'error': str(e)}
    
    def compare_queries(self, query1: str, query2: str, max_results: int = 3):
        """Compare results from two different queries"""
        print(f"\n{'='*60}")
        print(f"⚖️ QUERY COMPARISON")
        print(f"{'='*60}")
        
        print(f"🔍 Query 1: '{query1}'")
        print(f"🔍 Query 2: '{query2}'")
        print()
        
        try:
            results1 = self.db.search_schemes(query1, max_results)
            results2 = self.db.search_schemes(query2, max_results)
            
            print(f"📊 **Comparison Summary:**")
            print(f"   Query 1 Results: {len(results1)}")
            print(f"   Query 2 Results: {len(results2)}")
            print()
            
            # Show top results side by side
            max_compare = min(len(results1), len(results2), max_results)
            
            for i in range(max_compare):
                r1 = results1[i]
                r2 = results2[i]
                
                print(f"🎯 **Position #{i+1}**")
                print(f"   Query 1: {r1.get('title', 'N/A')} (Score: {r1.get('similarity_score', 0):.4f})")
                print(f"   Query 2: {r2.get('title', 'N/A')} (Score: {r2.get('similarity_score', 0):.4f})")
                print()
            
        except Exception as e:
            print(f"❌ Error comparing queries: {str(e)}")
    
    def inspect_database_stats(self):
        """Show detailed database statistics"""
        print(f"\n{'='*60}")
        print(f"📊 DATABASE STATISTICS")
        print(f"{'='*60}")
        
        try:
            stats = self.db.get_collection_stats()
            
            print(f"🗄️ **General Info:**")
            print(f"   - Total Schemes: {stats.get('total_schemes', 0)}")
            print(f"   - Database Path: {stats.get('database_path', 'N/A')}")
            print(f"   - Collection Name: {stats.get('collection_name', 'N/A')}")
            print()
            
            if 'sample_categories' in stats:
                print(f"📂 **Sample Categories:**")
                categories = stats['sample_categories']
                for cat, count in list(categories.items())[:10]:
                    print(f"   - {cat}: {count} schemes")
                print()
            
            if 'sample_states' in stats:
                print(f"📍 **Sample States:**")
                states = stats['sample_states']
                for state, count in list(states.items())[:10]:
                    print(f"   - {state}: {count} schemes")
                print()
            
            if 'sample_ministries' in stats:
                print(f"🏛️ **Sample Ministries:**")
                ministries = stats['sample_ministries']
                for ministry, count in list(ministries.items())[:5]:
                    print(f"   - {ministry}: {count} schemes")
                print()
                
        except Exception as e:
            print(f"❌ Error getting database stats: {str(e)}")
    
    def save_query_results(self, query: str, filename: str = None, max_results: int = 10):
        """Save query results to JSON file"""
        try:
            results = self.db.search_schemes(query, max_results)
            
            output_data = {
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'total_results': len(results),
                'results': results
            }
            
            filename = filename or f"query_results_{query.replace(' ', '_')[:20]}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Results saved to: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error saving results: {str(e)}")
            return None
    
    def interactive_mode(self):
        """Interactive testing mode"""
        print("\n🔍 **ChromaDB Query Tester - Interactive Mode**")
        print("Commands:")
        print("  - Type a query to search")
        print("  - 'stats' - Show database statistics") 
        print("  - 'compare <query1> | <query2>' - Compare two queries")
        print("  - 'save <query>' - Save query results to JSON")
        print("  - 'tool <query>' - Test through tool interface")
        print("  - 'raw <query>' - Test raw ChromaDB query")
        print("  - 'help' - Show this help")
        print("  - 'quit' - Exit")
        print()
        
        while True:
            try:
                user_input = input("🔍 Query> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 Goodbye!")
                    break
                
                elif user_input.lower() == 'help':
                    print("\n📖 **Available Commands:**")
                    print("  • Just type a query to search (e.g., 'crop insurance')")
                    print("  • 'stats' - Database statistics")
                    print("  • 'compare query1 | query2' - Compare two queries")
                    print("  • 'save query' - Save results to JSON")
                    print("  • 'tool query' - Test via tool interface")
                    print("  • 'raw query' - Raw ChromaDB search")
                    print("  • 'quit' - Exit")
                
                elif user_input.lower() == 'stats':
                    self.inspect_database_stats()
                
                elif user_input.lower().startswith('compare '):
                    query_part = user_input[8:]  # Remove 'compare '
                    if ' | ' in query_part:
                        q1, q2 = query_part.split(' | ', 1)
                        self.compare_queries(q1.strip(), q2.strip())
                    else:
                        print("❌ Format: compare query1 | query2")
                
                elif user_input.lower().startswith('save '):
                    query = user_input[5:]  # Remove 'save '
                    self.save_query_results(query)
                
                elif user_input.lower().startswith('tool '):
                    query = user_input[5:]  # Remove 'tool '
                    self.test_tool_query(query)
                
                elif user_input.lower().startswith('raw '):
                    query = user_input[4:]  # Remove 'raw '
                    self.test_raw_query(query)
                
                else:
                    # Default: test both raw and tool
                    self.test_raw_query(user_input)
                    self.test_tool_query(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")


def main():
    """Main function"""
    print("🔍 ChromaDB Query Tester")
    print("=" * 40)
    
    try:
        tester = ChromaDBQueryTester()
        
        # Show database stats first
        tester.inspect_database_stats()
        
        # Example queries for demonstration
        example_queries = [
            "crop insurance",
            "farmer financial assistance", 
            "PM-KISAN scheme",
            "irrigation support",
            "tractor loan"
        ]
        
        print("\n🎯 **Example Queries:**")
        for i, query in enumerate(example_queries, 1):
            print(f"  {i}. {query}")
        
        choice = input(f"\nSelect example (1-{len(example_queries)}) or press Enter for interactive mode: ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(example_queries):
            selected_query = example_queries[int(choice) - 1]
            print(f"\n🔍 Testing selected query: '{selected_query}'")
            tester.test_raw_query(selected_query)
            tester.test_tool_query(selected_query)
        else:
            # Interactive mode
            tester.interactive_mode()
            
    except Exception as e:
        print(f"❌ Error initializing tester: {str(e)}")
        print("Make sure the database is initialized and contains data.")


if __name__ == "__main__":
    main()
