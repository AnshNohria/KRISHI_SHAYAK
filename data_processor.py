"""
Data processor for agriculture schemes Excel data
"""
import pandas as pd
import logging
from typing import List, Dict, Optional
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class SchemesDataProcessor:
    """Process and clean agriculture schemes data from Excel file"""
    
    def __init__(self, excel_file_path: str):
        self.excel_file_path = excel_file_path
        self.raw_data = None
        self.processed_schemes = []
    
    def load_data(self) -> bool:
        """Load data from Excel file"""
        try:
            self.raw_data = pd.read_excel(self.excel_file_path)
            logger.info(f"Loaded {len(self.raw_data)} schemes from Excel file")
            return True
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            return False
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if pd.isna(text) or not text:
            return ""
        
        # Convert to string and clean
        text = str(text).strip()
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\-.,;:()\[\]]+', '', text)
        
        return text
    
    def extract_scheme_info(self, row) -> Dict:
        """Extract and structure scheme information from a row"""
        scheme = {
            'title': self.clean_text(row.get('en-basicDetails-schemeName-0', '')),
            'url': self.clean_text(row.get('data-page-selector-href', '')),
            'state': self.clean_text(row.get('pageProps-statesData-stateName-0', '')),
            'ministry': self.clean_text(row.get('en-basicDetails-nodalDepartmentName-label-0', '')),
            'slug': self.clean_text(row.get('slug-0', ''))
        }
        
        # Extract tags/categories
        tags = []
        for i in range(7):  # en-basicDetails-tags-0 to en-basicDetails-tags-6
            tag = self.clean_text(row.get(f'en-basicDetails-tags-{i}', ''))
            if tag:
                tags.append(tag)
        scheme['tags'] = tags
        scheme['category'] = ', '.join(tags) if tags else 'General'
        
        # Extract detailed description
        detailed_desc = self.clean_text(row.get('en-schemeContent-detailedDescription_md-0', ''))
        if not detailed_desc:
            detailed_desc = self.clean_text(row.get('en-schemeContent-detailedDescription-children-children-text-0', ''))
        scheme['detailed_description'] = detailed_desc
        
        # Extract benefits
        benefits = self.clean_text(row.get('en-schemeContent-benefits_md-0', ''))
        if not benefits:
            # Try to combine benefits from multiple fields
            benefit_parts = []
            for i in range(3):
                benefit = self.clean_text(row.get(f'en-schemeContent-benefits-children-children-text-{i}', ''))
                if benefit:
                    benefit_parts.append(benefit)
            benefits = ' '.join(benefit_parts)
        scheme['benefits'] = benefits
        
        # Extract brief description
        scheme['brief_description'] = self.clean_text(row.get('en-schemeContent-briefDescription-0', ''))
        
        # Extract application process
        app_process = []
        app_mode = self.clean_text(row.get('en-applicationProcess-mode-0', ''))
        if app_mode:
            app_process.append(f"Mode: {app_mode}")
        
        # Combine application process steps
        for i in range(19):  # Based on the columns we saw
            step = self.clean_text(row.get(f'en-applicationProcess-process-children-children-text-{i}', ''))
            if step and step not in ['NaN', 'nan']:
                app_process.append(step)
        
        scheme['application_process'] = ' '.join(app_process)
        
        # Extract eligibility criteria
        eligibility = []
        for i in range(4):
            criteria = self.clean_text(row.get(f'en-eligibilityCriteria-eligibilityDescription-children-children-text-{i}', ''))
            if criteria:
                eligibility.append(criteria)
        scheme['eligibility'] = ' '.join(eligibility)
        
        # Extract documents required
        documents = []
        for i in range(9):
            doc = self.clean_text(row.get(f'Document Required-{i}', ''))
            if doc:
                documents.append(doc)
        scheme['documents_required'] = ', '.join(documents)
        
        # Extract FAQ information
        faqs = []
        for i in range(8):
            faq = self.clean_text(row.get(f'FAQ Answer-{i}', ''))
            if faq:
                faqs.append(faq)
        scheme['faqs'] = ' '.join(faqs)
        
        # Extract references
        references = []
        for i in range(3):
            ref = self.clean_text(row.get(f'en-schemeContent-references-title-{i}', ''))
            if ref:
                references.append(ref)
        scheme['references'] = ', '.join(references)
        
        return scheme
    
    def process_schemes(self) -> List[Dict]:
        """Process all schemes and return structured data"""
        if self.raw_data is None:
            logger.error("No data loaded. Call load_data() first.")
            return []
        
        processed_schemes = []
        
        for idx, row in self.raw_data.iterrows():
            try:
                scheme = self.extract_scheme_info(row)
                
                # Skip if title is empty or invalid
                if not scheme['title'] or scheme['title'].lower() in ['nan', 'page not found']:
                    continue
                
                # Create full content for vector search
                content_parts = [
                    f"Title: {scheme['title']}",
                    f"Category: {scheme['category']}",
                    f"State: {scheme['state']}",
                    f"Ministry: {scheme['ministry']}",
                    f"Description: {scheme['detailed_description']}",
                    f"Benefits: {scheme['benefits']}",
                    f"Eligibility: {scheme['eligibility']}",
                    f"Application Process: {scheme['application_process']}",
                    f"Documents Required: {scheme['documents_required']}",
                    f"FAQs: {scheme['faqs']}"
                ]
                
                scheme['full_content'] = '\n'.join([part for part in content_parts if part.split(': ')[1].strip()])
                scheme['id'] = f"scheme_{idx}_{hash(scheme['title'])}"
                
                processed_schemes.append(scheme)
                
            except Exception as e:
                logger.warning(f"Error processing scheme at row {idx}: {e}")
                continue
        
        self.processed_schemes = processed_schemes
        logger.info(f"Successfully processed {len(processed_schemes)} schemes")
        
        return processed_schemes
    
    def save_processed_data(self, output_file: str = "processed_schemes.json") -> bool:
        """Save processed data to JSON file"""
        try:
            import json
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_schemes, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved processed schemes to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving processed data: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Get statistics about the processed data"""
        if not self.processed_schemes:
            return {}
        
        categories = {}
        states = {}
        ministries = {}
        
        for scheme in self.processed_schemes:
            # Count categories
            cat = scheme.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
            
            # Count states
            state = scheme.get('state', 'Unknown')
            states[state] = states.get(state, 0) + 1
            
            # Count ministries
            ministry = scheme.get('ministry', 'Unknown')
            ministries[ministry] = ministries.get(ministry, 0) + 1
        
        return {
            'total_schemes': len(self.processed_schemes),
            'categories': dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]),
            'states': dict(sorted(states.items(), key=lambda x: x[1], reverse=True)[:10]),
            'ministries': dict(sorted(ministries.items(), key=lambda x: x[1], reverse=True)[:10])
        }


def main():
    """Test the data processor"""
    processor = SchemesDataProcessor("myscheme-gov-in-2025-08-10.xlsx")
    
    if processor.load_data():
        schemes = processor.process_schemes()
        
        if schemes:
            print(f"✓ Processed {len(schemes)} schemes")
            
            # Show sample scheme
            print("\n=== Sample Scheme ===")
            sample = schemes[0]
            for key, value in sample.items():
                if key != 'full_content':  # Skip full content as it's too long
                    print(f"{key}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")
            
            # Show statistics
            stats = processor.get_statistics()
            print(f"\n=== Statistics ===")
            print(f"Total schemes: {stats['total_schemes']}")
            print(f"Top categories: {list(stats['categories'].keys())[:5]}")
            print(f"Top states: {list(stats['states'].keys())[:5]}")
            
            # Save processed data
            processor.save_processed_data()
        else:
            print("✗ Failed to process schemes")
    else:
        print("✗ Failed to load data")


if __name__ == "__main__":
    main()
