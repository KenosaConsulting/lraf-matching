"""
Enhanced LRAF Pipeline for TSV Data
Handles Navy procurement data with proper column mapping
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List
import os

class SimplifiedLRAFPipeline:
    """Pipeline for TSV data with Navy procurement format"""
    
    def __init__(self):
        self.contractors = []
        self.opportunities = []
        self.matches = {}
        self.user_naics = []
        self.target_agency = ""
    
    def get_user_inputs(self):
        """Get NAICS codes and agency preference from user"""
        print("\n🎯 User Configuration")
        print("-" * 40)
        
        # Get NAICS codes
        print("\nEnter up to 5 primary NAICS codes (separated by commas)")
        print("Example: 541512, 541511, 518210")
        naics_input = input("Your NAICS codes: ").strip()
        
        if naics_input:
            self.user_naics = [n.strip() for n in naics_input.split(',')][:5]
            print(f"  ✓ Using NAICS codes: {', '.join(self.user_naics)}")
        else:
            print("  ⚠️  No NAICS codes provided - will use contractor's existing codes")
        
        # Get agency preference
        print("\nEnter target agency (or 'ALL' to process everything, or press Enter for 'Navy')")
        agency_input = input("Target agency [Navy]: ").strip()
        self.target_agency = agency_input if agency_input else "Navy"
        if self.target_agency.upper() == 'ALL':
            print(f"  ✓ Processing ALL opportunities (no filtering)")
        else:
            print(f"  ✓ Targeting agency: {self.target_agency}")
    
    def load_contractors_from_tsv(self, profile_filepath: str, capabilities_filepath: str = None) -> Dict:
        """Load contractors from TSV files"""
        from cip import SimplifiedContractorIngestion
        
        ingester = SimplifiedContractorIngestion()
        result = ingester.ingest_tsv_with_capabilities(profile_filepath, capabilities_filepath)
        
        if result['success']:
            self.contractors = ingester.contractors
            
            # Enhance with user NAICS codes if provided
            if self.user_naics:
                for contractor in self.contractors:
                    # Add user NAICS codes to contractor's existing ones
                    existing_naics = contractor.get('naics', [])
                    combined_naics = list(set(existing_naics + self.user_naics))
                    contractor['naics'] = combined_naics
                    print(f"  Enhanced {contractor['legal_name']} with user NAICS codes")
            
            print(f"✓ Loaded {len(self.contractors)} contractors")
        else:
            print(f"✗ Failed: {result.get('error')}")
        
        return result
    
    def load_opportunities_from_navy_tsv(self, filepath: str) -> int:
        """Load opportunities from Navy procurement TSV with proper column mapping"""
        try:
            print(f"Loading Navy procurement data from {filepath}")
            
            # Read TSV file
            df = pd.read_csv(filepath, sep='\t')
            print(f"  Found {len(df)} total opportunities")
            
            # Filter by agency if specified
            if self.target_agency and self.target_agency.lower() != 'all':
                # Navy-specific organization patterns
                if self.target_agency.lower() == 'navy':
                    # Include all Navy organizations
                    navy_orgs = ['NAVSUP', 'NAVFAC', 'NAVSEA', 'NAVAIR', 'SSP', 'ONR', 'NRL', 
                                'SPAWAR', 'NSWC', 'NUWC', 'MSC', 'NAVY', 'NAVAL', 'FLEET',
                                'NIWC', 'NAVWAR', 'NAVSOC', 'NAVPERS', 'BUMED', 'CNO']
                    
                    # Create mask for any Navy organization
                    agency_mask = pd.Series([False] * len(df))
                    for org in navy_orgs:
                        agency_mask |= df['Source_Organization'].str.contains(org, case=False, na=False)
                        agency_mask |= df['Associated Program or Requirement Office'].str.contains(org, case=False, na=False)
                else:
                    # For other agencies, use direct string matching
                    agency_mask = (
                        df['Source_Organization'].str.contains(self.target_agency, case=False, na=False) |
                        df['Associated Program or Requirement Office'].str.contains(self.target_agency, case=False, na=False)
                    )
                
                df_filtered = df[agency_mask]
                print(f"  Filtered to {len(df_filtered)} {self.target_agency} opportunities")
                df = df_filtered
            else:
                print(f"  Processing all {len(df)} opportunities (no filter applied)")
            
            # Map Navy columns to expected format
            for idx, row in df.iterrows():
                # Convert entire row to dictionary to preserve ALL columns
                opp = row.to_dict()
                
                # Override/clean specific fields needed for matching
                opp['id'] = str(row.get('record_id', f'opp_{idx}'))
                opp['title'] = str(row.get('Requirement Title', ''))
                opp['description'] = str(row.get('Requirement Description', ''))
                opp['work_type'] = str(row.get('Requirement Description', ''))
                opp['agency'] = str(row.get('Associated Program or Requirement Office', ''))
                opp['source_org'] = str(row.get('Source_Organization', ''))
                
                # Clean NAICS for matching
                naics_raw = row.get('Anticipated NAICS Code', '')
                opp['naics'] = str(naics_raw).split('-')[0].strip() if pd.notna(naics_raw) else ''
                
                # Clean PSC for matching
                psc_raw = row.get('Anticipated PSC', '')
                opp['psc'] = str(psc_raw).split('-')[0].strip().upper() if pd.notna(psc_raw) else ''
                
                opp['set_aside'] = str(row.get('Anticipated Procurement Method', ''))
                opp['required_clearance'] = str(row.get('Anticipated Personnel Clearance', 'None'))
                opp['rfp_fy'] = str(row.get('Anticipated Solicitation FY', ''))
                opp['rfp_quarter'] = str(row.get('Anticipated Solicitation Quarter', ''))
                opp['award_fy'] = str(row.get('Anticipated Award FY', ''))
                opp['award_quarter'] = str(row.get('Anticipated Award Quarter', ''))
                opp['place_of_performance'] = str(row.get('Anticipated Place of Performance', ''))
                opp['follow_on'] = str(row.get('Follow-on or New', ''))
                opp['incumbent'] = str(row.get('Incumbent Contractor', ''))
                opp['contracting_office'] = str(row.get('Contracting Office UIC', ''))
                
                # Parse value fields
                value_min = row.get('value_min_millions', 0)
                value_max = row.get('value_max_millions', 0)
                anticipated_value = row.get('Anticipated Total Value (Millions)', 0)
                
                # Handle various value formats
                try:
                    if pd.notna(value_min):
                        value_min = float(value_min)
                    else:
                        value_min = 0
                except:
                    value_min = 0
                
                try:
                    if pd.notna(value_max) and str(value_max) != 'inf':
                        value_max = float(value_max)
                    else:
                        value_max = value_min
                except:
                    value_max = value_min
                
                try:
                    if pd.notna(anticipated_value):
                        anticipated_value = float(anticipated_value)
                    else:
                        anticipated_value = value_min
                except:
                    anticipated_value = value_min
                
                opp['est_value_min'] = value_min
                opp['est_value_max'] = value_max
                opp['anticipated_value'] = anticipated_value
                
                # Only add if it has a title or description
                if opp['title'] or opp['description']:
                    self.opportunities.append(opp)
            
            print(f"✓ Loaded {len(self.opportunities)} valid opportunities")
            return len(self.opportunities)
            
        except Exception as e:
            print(f"✗ Failed to load opportunities: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0
    
    def run_matching(self, top_k: int = None) -> Dict:
        """Run matching with enhanced scoring"""
        from me import SimplifiedLRAFMatchingEngine
        
        matcher = SimplifiedLRAFMatchingEngine()
        all_matches = {}
        
        # If no limit specified, process all opportunities
        if top_k is None:
            top_k = len(self.opportunities)
        
        print(f"\n📄 Running matching for {len(self.contractors)} contractors...")
        print(f"    Against {len(self.opportunities)} {self.target_agency} opportunities")
        print(f"    Exporting top {top_k} matches per contractor")
        print("    Using 4-factor capability-based scoring\n")
        
        for contractor in self.contractors:
            contractor_id = contractor.get('id', contractor.get('uei', 'unknown'))
            
            # Match against opportunities
            matches = matcher.match_batch(contractor, self.opportunities, top_k)
            
            # Calculate tier distribution
            tier_dist = {'A': 0, 'B': 0, 'C': 0, 'Ignore': 0}
            for match in matches:
                tier_dist[match.tier] += 1
            
            # Store results
            all_matches[contractor_id] = {
                'contractor_name': contractor.get('legal_name', 'Unknown'),
                'matches': matches,
                'tier_distribution': tier_dist
            }
            
            # Print progress
            print(f"  {contractor.get('legal_name', 'Unknown')[:30]:30} → "
                  f"Tier A: {tier_dist['A']:3} | B: {tier_dist['B']:3} | C: {tier_dist['C']:3}")
        
        self.matches = all_matches
        return all_matches
    
    def export_results(self, output_dir: str = 'lraf_output'):
        """Export results with ALL Navy procurement fields plus matching scores"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Store original TSV data for merging
        self.opportunities_df = pd.DataFrame(self.opportunities)
        
        # 1. Summary file (unchanged)
        summary_data = []
        for contractor_id, data in self.matches.items():
            summary_data.append({
                'contractor_name': data['contractor_name'],
                'tier_a_count': data['tier_distribution']['A'],
                'tier_b_count': data['tier_distribution']['B'],
                'tier_c_count': data['tier_distribution']['C'],
                'total_qualified': data['tier_distribution']['A'] + data['tier_distribution']['B']
            })
        
        df_summary = pd.DataFrame(summary_data)
        df_summary = df_summary.sort_values('tier_a_count', ascending=False)
        df_summary.to_csv(f'{output_dir}/matching_summary.csv', index=False)
        print(f"✓ Exported summary to {output_dir}/matching_summary.csv")
        
        # 2. Detailed matches with ALL original fields
        for contractor_id, data in self.matches.items():
            match_data = []
            # Export ALL matches, not limited to 100
            for match in data['matches']:
                # Find full opportunity details
                opp = next((o for o in self.opportunities if o['id'] == match.opportunity_id), {})
                
                if opp:
                    # Start with ALL original opportunity fields
                    row_data = opp.copy()
                    
                    # Add matching analysis fields at the beginning for visibility
                    row_data['MATCH_SCORE'] = match.score_total
                    row_data['MATCH_TIER'] = match.tier
                    row_data['MATCH_CAPABILITY'] = match.breakdown.get('capability_text', 0)
                    row_data['MATCH_NAICS'] = match.breakdown.get('naics', 0)
                    row_data['MATCH_PSC'] = match.breakdown.get('psc', 0)
                    row_data['MATCH_CERT'] = match.breakdown.get('certifications', 0)
                    row_data['MATCH_REASONS'] = '; '.join(match.reasons)
                    row_data['MATCH_CAP'] = match.cap
                    
                    match_data.append(row_data)
            
            if match_data:
                df = pd.DataFrame(match_data)
                
                # Reorder columns to put matching scores first, then original data
                match_cols = ['MATCH_SCORE', 'MATCH_TIER', 'MATCH_CAPABILITY', 'MATCH_NAICS', 
                             'MATCH_PSC', 'MATCH_CERT', 'MATCH_REASONS', 'MATCH_CAP']
                
                # Get all original columns (everything that's not a MATCH_ column)
                original_cols = [c for c in df.columns if not c.startswith('MATCH_')]
                
                # Combine in the desired order
                ordered_cols = match_cols + original_cols
                
                # Only include columns that exist in the dataframe
                ordered_cols = [c for c in ordered_cols if c in df.columns]
                df = df[ordered_cols]
                
                # Export with contractor name
                filename = data['contractor_name'].replace(' ', '_').replace(',', '')[:30]
                df.to_csv(f'{output_dir}/{filename}_full_matches.csv', index=False)
        
        print(f"✓ Exported full match files with all procurement data")
        
        # 3. Tier A opportunities with ALL fields
        tier_a_full = []
        for contractor_id, data in self.matches.items():
            for match in data['matches']:
                if match.tier == 'A':
                    opp = next((o for o in self.opportunities if o['id'] == match.opportunity_id), {})
                    if opp:
                        # Include ALL opportunity fields
                        row_data = opp.copy()
                        
                        # Add matching fields
                        row_data['CONTRACTOR'] = data['contractor_name']
                        row_data['MATCH_SCORE'] = match.score_total
                        row_data['MATCH_CAPABILITY'] = match.breakdown.get('capability_text', 0)
                        row_data['MATCH_NAICS'] = match.breakdown.get('naics', 0)
                        row_data['MATCH_PSC'] = match.breakdown.get('psc', 0)
                        row_data['MATCH_REASONS'] = '; '.join(match.reasons)
                        row_data['ACTION'] = 'Review and pursue'
                        
                        tier_a_full.append(row_data)
        
        if tier_a_full:
            df = pd.DataFrame(tier_a_full)
            
            # Sort by score and export
            df = df.sort_values('MATCH_SCORE', ascending=False)
            df.to_csv(f'{output_dir}/tier_a_opportunities_full.csv', index=False)
            print(f"✓ Exported {len(tier_a_full)} Tier A opportunities with complete data")
    
    def print_summary(self):
        """Print executive summary"""
        print("\n" + "="*60)
        print(f"LRAF ANALYSIS - {self.target_agency.upper()} OPPORTUNITIES")
        print("="*60)
        
        total_tier_a = sum(d['tier_distribution']['A'] for d in self.matches.values())
        total_tier_b = sum(d['tier_distribution']['B'] for d in self.matches.values())
        
        print(f"\n📊 Results Summary:")
        print(f"  • Contractors Analyzed: {len(self.contractors)}")
        print(f"  • {self.target_agency} Opportunities: {len(self.opportunities)}")
        print(f"  • Tier A Matches (Pursue): {total_tier_a}")
        print(f"  • Tier B Matches (Monitor): {total_tier_b}")
        
        if self.user_naics:
            print(f"\n🎯 User NAICS Codes Applied:")
            for naics in self.user_naics:
                print(f"  • {naics}")
        
        print(f"\n🏆 Top 3 Contractors by Tier A Matches:")
        sorted_contractors = sorted(
            self.matches.items(), 
            key=lambda x: x[1]['tier_distribution']['A'], 
            reverse=True
        )
        
        for i, (contractor_id, data) in enumerate(sorted_contractors[:3], 1):
            print(f"  {i}. {data['contractor_name']}")
            print(f"     Tier A: {data['tier_distribution']['A']} | "
                  f"Tier B: {data['tier_distribution']['B']}")
        
        print("\n" + "="*60)


# Main execution
if __name__ == "__main__":
    print("🚀 Starting Enhanced LRAF Pipeline for Navy Procurement Data")
    print("-" * 60)
    
    # Initialize pipeline
    pipeline = SimplifiedLRAFPipeline()
    
    # Get user inputs
    pipeline.get_user_inputs()
    
    # Step 1: Load contractors
    print("\n📥 Loading Contractor Data...")
    contractor_result = pipeline.load_contractors_from_tsv(
        'data/contractors/navancio_contractor_profile.tsv',
        'data/contractors/navancio_capabilities_final.tsv'
    )
    
    if not contractor_result['success']:
        print("Failed to load contractors. Check your TSV files.")
        exit(1)
    
    # Step 2: Load Navy opportunities
    print("\n📥 Loading Navy Procurement Opportunities...")
    opp_count = pipeline.load_opportunities_from_navy_tsv(
        'data/forecasts/navy_procurement_consolidated.tsv'
    )
    
    if opp_count == 0:
        print("Failed to load opportunities. Check your TSV file.")
        exit(1)
    
    # Step 3: Run matching
    pipeline.run_matching(top_k=None)  # Process ALL opportunities, no limit
    
    # Step 4: Export results
    print("\n📤 Exporting Results...")
    pipeline.export_results('lraf_output')
    
    # Step 5: Print summary
    pipeline.print_summary()
    
    print("\n✅ Pipeline Complete!")
    print("📁 Check 'lraf_output' directory for detailed results")
