#!/usr/bin/env python3
"""
Navy LRAF Execution Script
Handles TSV data files with proper directory structure
"""

import os
import sys
import pandas as pd

def check_environment():
    """Check that all required files and modules are present"""
    print("🔍 Checking environment...")
    
    # Check for required Python files
    required_files = {
        'cip.py': 'Contractor ingestion module',
        'me.py': 'Matching engine module',
        'lraf-pi.py': 'Main pipeline module'
    }
    
    missing = []
    for file, desc in required_files.items():
        if os.path.exists(file):
            print(f"  ✓ {file}: {desc}")
        else:
            print(f"  ✗ {file}: MISSING - {desc}")
            missing.append(file)
    
    if missing:
        print("\n❌ Missing required files. Please ensure all modules are present.")
        return False
    
    # Check for data directories
    data_dirs = {
        'data/contractors': 'Contractor data directory',
        'data/forecasts': 'Forecast/opportunities directory'
    }
    
    for dir_path, desc in data_dirs.items():
        if os.path.exists(dir_path):
            print(f"  ✓ {dir_path}: {desc}")
            # List TSV files in directory
            tsv_files = [f for f in os.listdir(dir_path) if f.endswith('.tsv')]
            for tsv in tsv_files:
                print(f"    • {tsv}")
        else:
            print(f"  ⚠️  {dir_path}: Not found - will check alternate locations")
    
    return True

def find_data_files():
    """Find the TSV data files in various possible locations"""
    print("\n📁 Locating data files...")
    
    # Possible locations for contractor files
    contractor_paths = [
        'data/contractors/navancio_contractor_profile.tsv',
        '../data/contractors/navancio_contractor_profile.tsv',
        'navancio_contractor_profile.tsv',
        'contractors/navancio_contractor_profile.tsv'
    ]
    
    capabilities_paths = [
        'data/contractors/navancio_capabilities_final.tsv',
        '../data/contractors/navancio_capabilities_final.tsv',
        'navancio_capabilities_final.tsv',
        'contractors/navancio_capabilities_final.tsv'
    ]
    
    navy_paths = [
        'data/forecasts/navy_procurement_consolidated.tsv',
        '../data/forecasts/navy_procurement_consolidated.tsv',
        'navy_procurement_consolidated.tsv',
        'forecasts/navy_procurement_consolidated.tsv'
    ]
    
    # Find contractor profile
    contractor_file = None
    for path in contractor_paths:
        if os.path.exists(path):
            contractor_file = path
            print(f"  ✓ Found contractor profile: {path}")
            break
    
    # Find capabilities
    capabilities_file = None
    for path in capabilities_paths:
        if os.path.exists(path):
            capabilities_file = path
            print(f"  ✓ Found capabilities: {path}")
            break
    
    # Find Navy procurement
    navy_file = None
    for path in navy_paths:
        if os.path.exists(path):
            navy_file = path
            print(f"  ✓ Found Navy procurement: {path}")
            # Quick stats
            try:
                df = pd.read_csv(path, sep='\t', nrows=5)
                total_rows = sum(1 for _ in open(path)) - 1  # Subtract header
                print(f"    • {total_rows} opportunities, {len(df.columns)} columns")
            except:
                pass
            break
    
    return contractor_file, capabilities_file, navy_file

def run_pipeline():
    """Execute the main pipeline"""
    # Import the pipeline
    import sys
    import importlib.util
    
    # Import required modules
    spec_cip = importlib.util.spec_from_file_location("cip", "cip.py")
    cip = importlib.util.module_from_spec(spec_cip)
    spec_cip.loader.exec_module(cip)
    
    spec_me = importlib.util.spec_from_file_location("me", "me.py")
    me = importlib.util.module_from_spec(spec_me)
    spec_me.loader.exec_module(me)
    
    spec_pipeline = importlib.util.spec_from_file_location("lraf_pipeline", "lraf-pi.py")
    pipeline_module = importlib.util.module_from_spec(spec_pipeline)
    spec_pipeline.loader.exec_module(pipeline_module)
    
    # Create pipeline instance
    pipeline = pipeline_module.SimplifiedLRAFPipeline()
    
    # Get user inputs
    pipeline.get_user_inputs()
    
    # Find data files
    contractor_file, capabilities_file, navy_file = find_data_files()
    
    if not all([contractor_file, navy_file]):
        print("\n❌ Could not find required data files")
        print("\nExpected file structure:")
        print("  data/")
        print("    contractors/")
        print("      navancio_contractor_profile.tsv")
        print("      navancio_capabilities_final.tsv")
        print("    forecasts/")
        print("      navy_procurement_consolidated.tsv")
        return False
    
    # Load contractors
    print("\n📥 Loading Contractor Data...")
    contractor_result = pipeline.load_contractors_from_tsv(
        contractor_file,
        capabilities_file  # May be None if not found
    )
    
    if not contractor_result['success']:
        print("Failed to load contractors.")
        return False
    
    # Load Navy opportunities
    print("\n📥 Loading Navy Procurement Opportunities...")
    opp_count = pipeline.load_opportunities_from_navy_tsv(navy_file)
    
    if opp_count == 0:
        print("Failed to load opportunities.")
        return False
    
    # Run matching
    print("\n🔄 Running Matching Algorithm...")
    pipeline.run_matching(top_k=None)  # Process ALL opportunities, no limit
    
    # Export results
    print("\n📤 Exporting Results...")
    pipeline.export_results('lraf_output')
    
    # Print summary
    pipeline.print_summary()
    
    return True

def main():
    """Main execution"""
    print("="*70)
    print("   NAVY LRAF MATCHING SYSTEM")
    print("   TSV Data Processing Pipeline")
    print("="*70)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check for required packages
    print("\n📦 Checking Python packages...")
    try:
        import pandas
        print("  ✓ pandas installed")
    except ImportError:
        print("  ✗ pandas missing - run: pip install pandas")
        sys.exit(1)
    
    try:
        import numpy
        print("  ✓ numpy installed")
    except ImportError:
        print("  ✗ numpy missing - run: pip install numpy")
        sys.exit(1)
    
    # Run the pipeline
    print("\n" + "="*70)
    print("STARTING ANALYSIS")
    print("="*70)
    
    success = run_pipeline()
    
    if success:
        print("\n" + "="*70)
        print("✅ ANALYSIS COMPLETE!")
        print("\n📊 Results saved to 'lraf_output/' directory:")
        print("  • matching_summary.csv - Overall contractor performance")
        print("  • tier_a_opportunities.csv - High-priority opportunities")
        print("  • [contractor]_matches.csv - Detailed scoring breakdowns")
        print("\n💡 Next Steps:")
        print("  1. Review Tier A opportunities for immediate BD action")
        print("  2. Analyze capability match scores for validation")
        print("  3. Check incumbent information for competitive positioning")
        print("="*70)
    else:
        print("\n❌ Pipeline failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
