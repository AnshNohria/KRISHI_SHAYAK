"""
ChromaDB vector database operations for agriculture schemes
"""

import chromadb
import logging
from typing import List, Dict, Optional
from chromadb.config import Settings
import os
import json

import config

# Set up logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format=config.LOG_FORMAT)
logger = logging.getLogger(__name__)


class SchemesVectorDB:
    """Vector database operations for agriculture schemes using ChromaDB"""
    
    def __init__(self, db_path: str = None, collection_name: str = None):
        self.db_path = db_path or config.CHROMA_DB_PATH
        self.collection_name = collection_name or config.COLLECTION_NAME
        self.client = None
        self.collection = None
        
        self.setup_database()
    
    def setup_database(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Create the database directory if it doesn't exist
            os.makedirs(self.db_path, exist_ok=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(path=self.db_path)
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Agriculture schemes from myscheme.gov.in"}
            )
            
            logger.info(f"Successfully initialized ChromaDB at {self.db_path}")
            logger.info(f"Collection '{self.collection_name}' ready")
            
        except Exception as e:
            logger.error(f"Error setting up database: {str(e)}")
            raise
    
    def add_schemes(self, schemes: List[Dict]) -> bool:
        """Add schemes to the vector database"""
        try:
            if not schemes:
                logger.warning("No schemes to add")
                return False
            
            # Clear existing data first (for fresh import)
            try:
                self.collection.delete()
                logger.info("Cleared existing collection data")
            except:
                pass
            
            # Prepare data for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            for scheme in schemes:
                # Use the full_content for vectorization
                document = scheme.get('full_content', '')
                
                # If full_content is empty, create it from available fields
                if not document:
                    doc_parts = [
                        f"Title: {scheme.get('title', '')}",
                        f"Description: {scheme.get('detailed_description', '')}",
                        f"Benefits: {scheme.get('benefits', '')}",
                        f"Eligibility: {scheme.get('eligibility', '')}",
                        f"Application Process: {scheme.get('application_process', '')}",
                        f"Category: {scheme.get('category', '')}",
                        f"State: {scheme.get('state', '')}",
                        f"Ministry: {scheme.get('ministry', '')}"
                    ]
                    document = "\n".join([part for part in doc_parts if part.split(': ')[1].strip()])
                
                documents.append(document)
                
                # Prepare metadata (only basic types for ChromaDB)
                metadata = {
                    'title': str(scheme.get('title', ''))[:1000],  # Limit length
                    'category': str(scheme.get('category', ''))[:500],
                    'state': str(scheme.get('state', ''))[:200],
                    'ministry': str(scheme.get('ministry', ''))[:500],
                    'url': str(scheme.get('url', ''))[:1000],
                    'tags': str(', '.join(scheme.get('tags', [])))[:1000]
                }
                metadatas.append(metadata)
                
                # Use the provided ID or generate one
                scheme_id = scheme.get('id', f"scheme_{hash(scheme.get('title', ''))}")
                ids.append(scheme_id)
            
            # Add to collection in batches
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_metas = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                
                self.collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
                
                logger.info(f"Added batch {i//batch_size + 1}: {len(batch_docs)} schemes")
            
            logger.info(f"Successfully added {len(schemes)} schemes to the database")
            return True
            
        except Exception as e:
            logger.error(f"Error adding schemes to database: {str(e)}")
            return False
    
    def search_schemes(self, query: str, max_results: int = None, filters: Dict = None) -> List[Dict]:
        """Search for relevant schemes using semantic similarity"""
        try:
            max_results = max_results or config.MAX_SEARCH_RESULTS
            
            # Prepare query parameters
            query_params = {
                "query_texts": [query],
                "n_results": max_results,
                "include": ['documents', 'metadatas', 'distances']
            }
            
            # Add filters if provided
            if filters:
                # ChromaDB uses where clauses for filtering
                where_clause = {}
                if filters.get('state'):
                    where_clause['state'] = filters['state']
                if filters.get('category'):
                    where_clause['category'] = {"$contains": filters['category']}
                
                if where_clause:
                    query_params['where'] = where_clause
            
            results = self.collection.query(**query_params)
            
            # Format results
            formatted_results = []
            
            if results and results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    formatted_result = {
                        'rank': i + 1,
                        'title': metadata.get('title', 'Unknown Scheme'),
                        'content': doc,
                        'metadata': metadata,
                        'similarity_score': 1 - distance,  # Convert distance to similarity
                        'url': metadata.get('url', ''),
                        'state': metadata.get('state', ''),
                        'category': metadata.get('category', ''),
                        'ministry': metadata.get('ministry', '')
                    }
                    formatted_results.append(formatted_result)
            
            logger.info(f"Found {len(formatted_results)} relevant schemes for query: {query[:50]}...")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching schemes: {str(e)}")
            return []
    
    def get_scheme_by_title(self, title: str) -> Optional[Dict]:
        """Get a specific scheme by its title"""
        try:
            results = self.collection.query(
                query_texts=[title],
                n_results=1,
                include=['documents', 'metadatas', 'distances']
            )
            
            if results and results['documents'] and results['documents'][0]:
                doc = results['documents'][0][0]
                metadata = results['metadatas'][0][0]
                distance = results['distances'][0][0]
                
                return {
                    'title': metadata.get('title', 'Unknown Scheme'),
                    'content': doc,
                    'metadata': metadata,
                    'similarity_score': 1 - distance,
                    'url': metadata.get('url', ''),
                    'state': metadata.get('state', ''),
                    'category': metadata.get('category', ''),
                    'ministry': metadata.get('ministry', '')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting scheme by title: {str(e)}")
            return None
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection"""
        try:
            count = self.collection.count()
            
            # Get sample of metadata to analyze distribution
            sample_results = self.collection.query(
                query_texts=["agriculture"],
                n_results=min(100, count) if count > 0 else 1,
                include=['metadatas']
            )
            
            stats = {
                'total_schemes': count,
                'collection_name': self.collection_name,
                'database_path': self.db_path
            }
            
            if sample_results and sample_results['metadatas']:
                categories = {}
                states = {}
                ministries = {}
                
                for metadata in sample_results['metadatas'][0]:
                    # Count categories
                    cat = metadata.get('category', 'Unknown')
                    categories[cat] = categories.get(cat, 0) + 1
                    
                    # Count states
                    state = metadata.get('state', 'Unknown')
                    states[state] = states.get(state, 0) + 1
                    
                    # Count ministries
                    ministry = metadata.get('ministry', 'Unknown')
                    ministries[ministry] = ministries.get(ministry, 0) + 1
                
                stats.update({
                    'sample_categories': dict(list(categories.items())[:10]),
                    'sample_states': dict(list(states.items())[:10]),
                    'sample_ministries': dict(list(ministries.items())[:10])
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {'total_schemes': 0}
    
    def clear_collection(self) -> bool:
        """Clear all data from the collection"""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Agriculture schemes from myscheme.gov.in"}
            )
            logger.info(f"Successfully cleared collection '{self.collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Error clearing collection: {str(e)}")
            return False
    
    def export_schemes(self, output_file: str = "exported_schemes.json") -> bool:
        """Export all schemes to JSON file"""
        try:
            # Get all schemes
            count = self.collection.count()
            if count == 0:
                logger.warning("No schemes to export")
                return False
            
            # Query all documents
            results = self.collection.query(
                query_texts=[""],
                n_results=count,
                include=['documents', 'metadatas']
            )
            
            exported_schemes = []
            if results and results['documents'] and results['documents'][0]:
                for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                    scheme = {
                        'content': doc,
                        'metadata': metadata
                    }
                    exported_schemes.append(scheme)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(exported_schemes, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(exported_schemes)} schemes to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting schemes: {str(e)}")
            return False


def main():
    """Test the database operations"""
    # Initialize database
    db = SchemesVectorDB()
    
    # Load and process schemes from Excel
    from data_processor import SchemesDataProcessor
    
    processor = SchemesDataProcessor("myscheme-gov-in-2025-08-10.xlsx")
    
    if processor.load_data():
        schemes = processor.process_schemes()
        
        if schemes:
            print(f"✓ Processed {len(schemes)} schemes")
            
            # Add schemes to database
            success = db.add_schemes(schemes)
            
            if success:
                print("✓ Successfully added schemes to database")
                
                # Test search
                print("\n=== Testing Search Functionality ===")
                
                test_queries = [
                    "farmer financial assistance",
                    "crop insurance",
                    "irrigation support",
                    "PM-KISAN",
                    "credit card for farmers"
                ]
                
                for query in test_queries:
                    print(f"\nQuery: {query}")
                    results = db.search_schemes(query, max_results=3)
                    
                    for result in results:
                        print(f"  - {result['title']} (Score: {result['similarity_score']:.3f})")
                        print(f"    State: {result['state']}, Category: {result['category']}")
                
                # Print stats
                stats = db.get_collection_stats()
                print(f"\n=== Database Stats ===")
                print(f"Total schemes: {stats['total_schemes']}")
                print(f"Collection: {stats['collection_name']}")
                print(f"Path: {stats['database_path']}")
                
                if 'sample_categories' in stats:
                    print(f"Sample categories: {list(stats['sample_categories'].keys())}")
                    print(f"Sample states: {list(stats['sample_states'].keys())}")
            
            else:
                print("✗ Failed to add schemes to database")
        else:
            print("✗ Failed to process schemes")
    else:
        print("✗ Failed to load Excel data")


if __name__ == "__main__":
    main()
