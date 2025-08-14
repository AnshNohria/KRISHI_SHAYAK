"""
Examine the structure of the schemes Excel file
"""
import pandas as pd

# Load the Excel file
file_path = "myscheme-gov-in-2025-08-10.xlsx"

try:
    # Read the Excel file
    df = pd.read_excel(file_path)
    
    print("=== Excel File Structure ===")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print("\n=== Sample Data ===")
    print(df.head(2).to_string())
    
    print("\n=== Column Info ===")
    for col in df.columns:
        non_null_count = df[col].notna().sum()
        print(f"{col}: {non_null_count} non-null values")
    
    # Check for any specific schemes data
    if 'title' in df.columns or 'scheme_name' in df.columns:
        title_col = 'title' if 'title' in df.columns else 'scheme_name'
        print(f"\n=== Sample Scheme Titles ===")
        print(df[title_col].head(5).tolist())
        
except Exception as e:
    print(f"Error reading Excel file: {e}")
