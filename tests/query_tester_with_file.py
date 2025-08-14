"""
ChromaDB Query Tester with File Output - Test and inspect ChromaDB search results
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
    """Interactive tool to test and inspect ChromaDB queries with file output"""
    
    def __init__(self):
        self.db = SchemesVectorDB()
        self.search_tool = SchemeSearchTool(self.db)
        self.output_file = "query_results.txt"
        
    def save_results_to_file(self, query: str, results: List[Dict], max_results: int):
        """Save detailed query results to text file"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"CHROMADB QUERY RESULTS\n")
                f.write("="*80 + "\n")
                f.write(f"Query: {query}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Max Results Requested: {max_results}\n")
                f.write(f"Results Found: {len(results)}\n")
                f.write("="*80 + "\n\n")
                
                if not results:
                    f.write("❌ NO RESULTS FOUND\n")
                    f.write("Try:\n")
                    f.write("- Using different keywords\n")
                    f.write("- Broader search terms\n")
                    f.write("- Checking spelling\n")
                    return
                
                for i, result in enumerate(results, 1):
                    f.write(f"RESULT #{i}\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"Title: {result.get('title', 'N/A')}\n")
                    f.write(f"State: {result.get('state', 'N/A')}\n")
                    f.write(f"Ministry: {result.get('ministry', 'N/A')}\n")
                    f.write(f"Category: {result.get('category', 'N/A')}\n")
                    f.write(f"Similarity Score: {result.get('similarity_score', 0):.4f}\n")
                    f.write(f"URL: {result.get('url', 'N/A')}\n")
                    f.write(f"\nFULL CONTENT:\n{'-'*20}\n")
                    f.write(result.get('content', 'No content available'))
                    f.write(f"\n{'-'*20}\n")
                    
                    # Add metadata if available
                    metadata = result.get('metadata', {})
                    if metadata:
                        f.write(f"\nMETADATA:\n")
                        for key, value in metadata.items():
                            f.write(f"  {key}: {value}\n")
                    
                    f.write("\n" + "="*60 + "\n\n")
            
            print(f"✅ Results saved to: {self.output_file}")
            
        except Exception as e:
            print(f"❌ Error saving to file: {str(e)}")
    
    def save_error_to_file(self, query: str, error: str):
        """Save error information to text file"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"CHROMADB QUERY ERROR\n")
                f.write("="*80 + "\n")
                f.write(f"Query: {query}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Error: {error}\n")
                f.write("="*80 + "\n")
            
            print(f"❌ Error details saved to: {self.output_file}")
            
        except Exception as e:
            print(f"❌ Could not save error to file: {str(e)}")
    
    def test_query(self, query: str, max_results: int = 5) -> List[Dict]:
        """Test a query and save results to file"""
        print(f"\n{'='*60}")
        print(f"🔍 TESTING QUERY: '{query}'")
        print(f"📊 Max Results: {max_results}")
        print(f"💾 Output File: {self.output_file}")
        print(f"{'='*60}")
        
        try:
            # Search the database
            results = self.db.search_schemes(query, max_results)
            
            if not results:
                print("❌ No results found for this query")
                self.save_results_to_file(query, [], max_results)
                return []
            
            print(f"✅ Found {len(results)} results")
            print(f"💾 Full details saved to {self.output_file}")
            
            # Display brief summary in terminal
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.get('title', 'N/A')} (Score: {result.get('similarity_score', 0):.3f})")
            
            # Save detailed results to file
            self.save_results_to_file(query, results, max_results)
            
            return results
            
        except Exception as e:
            print(f"❌ Error testing query: {str(e)}")
            self.save_error_to_file(query, str(e))
            return []
    
    def test_tool_query(self, query: str, max_results: int = 5):
        """Test query through the scheme search tool and save to file"""
        print(f"\n{'='*60}")
        print(f"🛠️ TESTING TOOL QUERY: '{query}'")
        print(f"💾 Output File: {self.output_file}")
        print(f"{'='*60}")
        
        try:
            # Check if tool considers query relevant
            is_relevant = self.search_tool.is_relevant(query)
            print(f"🤔 Tool Relevance: {'✅ Yes' if is_relevant else '❌ No'}")
            
            # Save tool results to file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"SCHEME SEARCH TOOL RESULTS\n")
                f.write("="*80 + "\n")
                f.write(f"Query: {query}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Tool Relevance: {'Yes' if is_relevant else 'No'}\n")
                f.write("="*80 + "\n\n")
                
                if is_relevant:
                    # Execute through tool
                    result = self.search_tool.execute(query, max_results=max_results)
                    
                    f.write(f"Tool Execution Success: {'Yes' if result['success'] else 'No'}\n")
                    f.write(f"Message: {result.get('message', 'N/A')}\n\n")
                    
                    if result['success']:
                        f.write("FORMATTED TOOL RESPONSE:\n")
                        f.write("-" * 40 + "\n")
                        f.write(result.get('result', 'No formatted result available'))
                        f.write("\n" + "-" * 40 + "\n\n")
                        
                        # Show metadata
                        metadata = result.get('metadata', {})
                        if metadata:
                            f.write("QUERY METADATA:\n")
                            f.write("-" * 20 + "\n")
                            f.write(f"Original Query: {metadata.get('query', 'N/A')}\n")
                            f.write(f"Optimized Query: {metadata.get('optimized_query', 'N/A')}\n")
                            f.write(f"Total Results: {metadata.get('total_results', 'N/A')}\n")
                            f.write(f"Search Type: {metadata.get('search_type', 'N/A')}\n")
                    
                    print(f"✅ Tool execution completed")
                else:
                    f.write("🚫 Tool determined query is not relevant for scheme search.\n")
                    print("❌ Query not relevant for tool")
            
            print(f"💾 Tool results saved to {self.output_file}")
                
        except Exception as e:
            print(f"❌ Error executing tool query: {str(e)}")
            self.save_error_to_file(f"TOOL: {query}", str(e))
    
    def compare_queries(self, query1: str, query2: str, max_results: int = 3):
        """Compare results from two different queries and save to file"""
        print(f"\n{'='*60}")
        print(f"⚖️ COMPARING QUERIES")
        print(f"Query 1: '{query1}'")
        print(f"Query 2: '{query2}'")
        print(f"💾 Output File: {self.output_file}")
        print(f"{'='*60}")
        
        try:
            results1 = self.db.search_schemes(query1, max_results)
            results2 = self.db.search_schemes(query2, max_results)
            
            print(f"📊 Query 1 Results: {len(results1)}")
            print(f"📊 Query 2 Results: {len(results2)}")
            
            # Save comparison to file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"QUERY COMPARISON RESULTS\n")
                f.write("="*80 + "\n")
                f.write(f"Query 1: {query1}\n")
                f.write(f"Query 2: {query2}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Max Results Each: {max_results}\n")
                f.write(f"Query 1 Results: {len(results1)}\n")
                f.write(f"Query 2 Results: {len(results2)}\n")
                f.write("="*80 + "\n\n")
                
                # Show results side by side
                max_compare = max(len(results1), len(results2))
                
                for i in range(max_compare):
                    f.write(f"POSITION #{i+1}\n")
                    f.write("-" * 30 + "\n")
                    
                    if i < len(results1):
                        r1 = results1[i]
                        f.write(f"QUERY 1 RESULT:\n")
                        f.write(f"  Title: {r1.get('title', 'N/A')}\n")
                        f.write(f"  Score: {r1.get('similarity_score', 0):.4f}\n")
                        f.write(f"  State: {r1.get('state', 'N/A')}\n")
                        f.write(f"  Category: {r1.get('category', 'N/A')}\n")
                    else:
                        f.write(f"QUERY 1 RESULT: No result at this position\n")
                    
                    f.write("\n")
                    
                    if i < len(results2):
                        r2 = results2[i]
                        f.write(f"QUERY 2 RESULT:\n")
                        f.write(f"  Title: {r2.get('title', 'N/A')}\n")
                        f.write(f"  Score: {r2.get('similarity_score', 0):.4f}\n")
                        f.write(f"  State: {r2.get('state', 'N/A')}\n")
                        f.write(f"  Category: {r2.get('category', 'N/A')}\n")
                    else:
                        f.write(f"QUERY 2 RESULT: No result at this position\n")
                    
                    f.write("\n" + "="*50 + "\n\n")
            
            print(f"✅ Comparison saved to {self.output_file}")
            
        except Exception as e:
            print(f"❌ Error comparing queries: {str(e)}")
            self.save_error_to_file(f"COMPARE: {query1} vs {query2}", str(e))
    
    def interactive_mode(self):
        """Interactive testing mode with file output"""
        print(f"\n🔍 **ChromaDB Query Tester - Interactive Mode**")
        print(f"💾 All results will be saved to: {self.output_file}")
        print("Commands:")
        print("  - Type a query to search (saves to file)")
        print("  - 'tool <query>' - Test through tool interface")
        print("  - 'compare <query1> | <query2>' - Compare two queries")
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
                    print("  • 'tool query' - Test via tool interface")
                    print("  • 'compare query1 | query2' - Compare two queries")
                    print("  • 'quit' - Exit")
                    print(f"  • All results are saved to: {self.output_file}")
                
                elif user_input.lower().startswith('compare '):
                    query_part = user_input[8:]  # Remove 'compare '
                    if ' | ' in query_part:
                        q1, q2 = query_part.split(' | ', 1)
                        self.compare_queries(q1.strip(), q2.strip())
                    else:
                        print("❌ Format: compare query1 | query2")
                
                elif user_input.lower().startswith('tool '):
                    query = user_input[5:]  # Remove 'tool '
                    self.test_tool_query(query)
                
                else:
                    # Default: test raw query
                    self.test_query(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")


def main():
    """Main function"""
    print("🔍 ChromaDB Query Tester with File Output")
    print("=" * 50)
    
    try:
        tester = ChromaDBQueryTester()
        
        # Show database stats
        stats = tester.db.get_collection_stats()
        print(f"📊 Database: {stats.get('total_schemes', 0)} schemes available")
        print(f"💾 Results will be saved to: {tester.output_file}")
        
        # Example queries
        example_queries = [
            "crop insurance",
            "farmer financial assistance", 
            "PM-KISAN scheme",
            "irrigation support",
            "tractor loan"
        ]
        
        print("\n🎯 **Quick Test Options:**")
        for i, query in enumerate(example_queries, 1):
            print(f"  {i}. {query}")
        
        choice = input(f"\nSelect example (1-{len(example_queries)}), 'i' for interactive, or Enter to quit: ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(example_queries):
            selected_query = example_queries[int(choice) - 1]
            print(f"\n🔍 Testing: '{selected_query}'")
            tester.test_query(selected_query)
        elif choice.lower() == 'i':
            tester.interactive_mode()
        else:
            print("👋 Goodbye!")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
