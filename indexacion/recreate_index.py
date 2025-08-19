#!/usr/bin/env python3
"""
Script to recreate the Azure Search index with filterable title field
and re-index all documents.
"""

import os
import sys
from pathlib import Path

# Add the project directories to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "indexacion"))
sys.path.insert(0, str(current_dir))

def recreate_index():
    """Recreate the index and re-index all documents"""
    try:
        # Import after setting path
        from indexacion.create_index import create_or_replace
        from indexacion.ingest_excel import process_file
        
        print("🔄 Step 1: Recreating index with filterable title field...")
        create_or_replace()
        print("✅ Index recreated successfully!")
        
        print("\n🔄 Step 2: Re-indexing documents...")
        
        # Look for Excel files to re-index
        excel_files = list(current_dir.glob("*.xlsx")) + list(current_dir.glob("*.xls"))
        
        if not excel_files:
            print("⚠️ No Excel files found in current directory")
            print("Please run this script from the directory containing your Excel files")
            return False
            
        for excel_file in excel_files:
            print(f"📁 Processing: {excel_file.name}")
            try:
                process_file(str(excel_file))
                print(f"✅ Indexed: {excel_file.name}")
            except Exception as e:
                print(f"❌ Error indexing {excel_file.name}: {str(e)}")
                
        print("\n🎉 Index recreation complete!")
        print("The title field is now filterable and you can use proper filtering in your searches.")
        return True
        
    except Exception as e:
        print(f"❌ Error during index recreation: {str(e)}")
        return False

if __name__ == "__main__":
    print("Azure Search Index Recreation Tool")
    print("=" * 50)
    print("This will:")
    print("1. Delete and recreate the search index")
    print("2. Make the title field filterable")
    print("3. Re-index all Excel documents found in current directory")
    print()
    
    confirm = input("Do you want to continue? (y/N): ").lower().strip()
    if confirm in ['y', 'yes']:
        success = recreate_index()
        if success:
            print("\n✅ All done! Your providence search should now work with proper filtering.")
        else:
            print("\n❌ Recreation failed. Check the error messages above.")
    else:
        print("Operation cancelled.")
