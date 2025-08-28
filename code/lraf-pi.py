"""
LRAF Pipeline Integration
Combines contractor ingestion with opportunity matching
"""

import pandas as pd
import json
from datetime import datetime
from typing import Dict, List
import os

class LRAFPipeline:
    """Main pipeline for LRAF matching system"""
    
    def __init__(self):
        self.contractors = []
        self.opportunities = []
        self.matches = {}
        
    def load_contractors_from_csv(self, filepath: str) -> Dict:
        """Load contractors using the ingestion module"""
        from contractor_ingestion import ContractorIngestion
        
        ingester = ContractorIngestion()
        result = ingester.ingest_csv(filepath)
        
        if result['success']:
            self.contractors = ingester.contractors
            print(f"✓ Loaded {len(self.contractors)} contractors")
            
            # Load past performance if available
            pp_file = filepath.replace('contractor_profile', 'past_performance')
            if os.path.exists(pp_file):
                self._load_past_performance(pp_file)
        else:
            print(f"✗ Failed to load contractors: {result.get('error')}")
        
        return result
    
    def _load_past_performance(self, filepath: str):
        """Attach past performance to contractors"""
        df = pd.read_csv(filepath)
        
        # Group by UEI (or another identifier)
        for contractor in self.contractors:
            uei = contractor.get('uei')
            if uei:
                contractor['past_performance'] = []
                
                # Find matching past performances
                for _, row in df.iterrows():
                    # You might need to adjust this matching logic
                    pp = {
                        'title': row.get('title', ''),
                        'agency_parent': row.get('agency_parent', ''),
                        'agency_bureau': row.get('agency_bureau', ''),
                        'naics': str(row.get('naics', '')),
                        'psc': str(row.get('psc', '')).upper() if pd.notna(row.get('psc')) else '',
                        'role': row.get('role', 'prime'),
                        'vehicle': row.get('vehicle', ''),
                        'contract_type': row.get('contract_type', ''),
                        'obligated_value': float(row.get('obligated_value', 0)) if pd.notna(row.get('obligated_value')) else 0,
                        'pop_start': row.get('pop_start', ''),
                        'pop_end': row.get('pop_end', ''),
                        'piid': row.get('piid', ''),
                        'short_description': row.get('short_description', '')
                    }
                    contractor['past_performance'].append(pp)
        
        print(f"✓ Loaded past performance data")
    
    def load_opportunities_from_csv(self, filepath: str) -> int:
        """Load standardized forecast opportunities"""
        try:
            df = pd.read_csv(filepath)
            
            for idx, row in df.iterrows():
                # Parse opportunity from standardized format
                opp = {
                    'id': f"opp-{idx:04d}",
                    'source': row.get('source', ''),
                    'source_url': row.get('source_url', ''),
                    'agency_parent': row.get('agency', ''),
                    'agency_bureau': row.get('bureau', ''),
                    'office': row.get('office', ''),
                    'title': row.get('title', ''),
                    'description': row.get('description', ''),
                    'keywords': row.get('keywords', '').split(';') if pd.notna(row.get('keywords')) else [],
                    'naics': row.get('naics', '').split(';') if pd.notna(row.get('naics')) else [],
                    'pscs': row.get('pscs', '').split(';') if pd.notna(row.get('pscs')) else [],
                    'set_aside': row.get('set_aside', ''),
                    'vehicle': row.get('vehicle', ''),
                    'contract_type': row.get('contract_type', '').split(';') if pd.notna(row.get('contract_type')) else [],
                    'est_value_min': float(row.get('est_value_min', 0)) if pd.notna(row.get('est_value_min')) else 0,
                    'est_value_max': float(row.get('est_value_max', 0)) if pd.notna(row.get('est_value_max')) else 0,
                    'place_of_performance': {
                        'city': row.get('place_city', ''),
                        'state': row.get('place_state', ''),
                        'remote_ok': bool(row.get('remote_ok', False))
                    },
                    'pop_est_start': row.get('pop_est_start', ''),
                    'rfi_date': row.get('rfi_date', ''),
                    'draft_rfp_date': row.get('draft_rfp_date', ''),
                    'final_rfp_date': row.get('final_rfp_date', ''),
                    'required_clearance': row.get('required_clearance', 'None'),
                    'co_name': row.get('co_name', ''),
                    'co_email': row.get('co_email', ''),
                    'co_phone': row.get('co_phone', ''),
                }
                
                # Calculate mid-value for matching
                if opp['est_value_min'] and opp['est_value_max']:
                    opp['est_value_mid'] = (opp['est_value_min'] + opp['est_value_max']) / 2
                
                self.opportunities.append(opp)
            
            print(f"✓ Loaded {len(self.opportunities)} opportunities")
            return len(self.opportunities)
            
        except Exception as e:
            print(f"✗ Failed to load opportunities: {str(e)}")
            return 0
    
    def run_matching(self, top_k: int = 50) -> Dict:
        """Run matching for all contractors against all opportunities"""
        from matching_engine import LRAFMatchingEngine
        
        matcher = LRAFMatchingEngine()
        all_matches = {}
        
        print(f"\n🔄 Running matching for {len(self.contractors)} contractors...")
        
        for contractor in self.contractors:
            contractor_id = contractor.get('id', contractor.get('uei', 'unknown'))
            
            # Match against all opportunities
            matches = matcher.match_batch(contractor, self.opportunities, top_k)
            
            # Store results
            all_matches[contractor_id] = {
                'contractor_name': contractor.get('legal_name', 'Unknown'),
                'matches': matches,
                'tier_distribution': self._calculate_tier_distribution(matches),
                'top_agencies': self._get_top_agencies(matches)
            }
            
            # Print summary for this contractor
            tier_dist = all_matches[contractor_id]['tier_distribution']
            print(f"  {contractor.get('legal_name', 'Unknown')}: "
                  f"A:{tier_dist['A']} B:{tier_dist['B']} C:{tier_dist['C']}")
        
        self.matches = all_matches
        return all_matches
    
    def _calculate_tier_distribution(self, matches: List) -> Dict:
        """Calculate distribution of matches by tier"""
        tiers = {'A': 0, 'B': 0, 'C': 0, 'Ignore': 0}
        for match in matches:
            tiers[match.tier] = tiers.get(match.tier, 0) + 1
        return tiers
    
    def _get_top_agencies(self, matches: List) -> List[str]:
        """Get top agencies from matched opportunities"""
        agencies = {}
        for match in matches[:20]:  # Top 20 matches
            if match.tier in ['A', 'B']:
                # Get the opportunity
                opp = next((o for o in self.opportunities 
                           if o['id'] == match.opportunity_id), None)
                if opp:
                    agency = opp.get('agency_parent', 'Unknown')
                    agencies[agency] = agencies.get(agency, 0) + 1
        
        # Sort by count
        sorted_agencies = sorted(agencies.items(), key=lambda x: x[1], reverse=True)
        return [agency for agency, _ in sorted_agencies[:5]]
    
    def export_results(self, output_dir: str = 'lraf_output'):
        """Export all results to files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Export summary report
        summary = []
        for contractor_id, data in self.matches.items():
            tier_dist = data['tier_distribution']
            summary.append({
                'contractor_id': contractor_id,
                'contractor_name': data['contractor_name'],
                'tier_a_count': tier_dist['A'],
                'tier_b_count': tier_dist['B'],
                'tier_c_count': tier_dist['C'],
                'total_qualified': tier_dist['A'] + tier_dist['B'],
                'top_agencies': ', '.join(data['top_agencies'])
            })
        
        summary_df = pd.DataFrame(summary)
        summary_df.to_csv(f'{output_dir}/matching_summary.csv', index=False)
        print(f"✓ Exported summary to {output_dir}/matching_summary.csv")
        
        # Export detailed matches for each contractor
        for contractor_id, data in self.matches.items():
            matches_data = []
            for match in data['matches'][:100]:  # Top 100 per contractor
                # Find the opportunity
                opp = next((o for o in self.opportunities 
                           if o['id'] == match.opportunity_id), None)
                if opp:
                    matches_data.append({
                        'opportunity_id': match.opportunity_id,
                        'title': opp.get('title', ''),
                        'agency': opp.get('agency_parent', ''),
                        'score': match.score_total,
                        'tier': match.tier,
                        'naics_score': match.breakdown.get('naics', 0),
                        'text_score': match.breakdown.get('text', 0),
                        'agency_score': match.breakdown.get('agency', 0),
                        'top_reason': match.reasons_positive[0] if match.reasons_positive else '',
                        'top_blocker': match.reasons_negative[0] if match.reasons_negative else '',
                        'teaming_needed': ', '.join(match.teaming_suggestions),
                        'set_aside': opp.get('set_aside', ''),
                        'vehicle': opp.get('vehicle', ''),
                        'est_value': opp.get('est_value_mid', 0),
                        'rfp_date': opp.get('final_rfp_date', '')
                    })
            
            if matches_data:
                contractor_name = data['contractor_name'].replace(' ', '_').replace(',', '')
                df = pd.DataFrame(matches_data)
                df.to_csv(f'{output_dir}/{contractor_name}_matches.csv', index=False)
        
        print(f"✓ Exported individual match files to {output_dir}/")
        
        # Export capture plans for Tier A opportunities
        self._export_capture_plans(output_dir)
    
    def _export_capture_plans(self, output_dir: str):
        """Export capture plan templates for Tier A opportunities"""
        capture_plans = []
        
        for contractor_id, data in self.matches.items():
            contractor_name = data['contractor_name']
            
            for match in data['matches']:
                if match.tier == 'A':
                    opp = next((o for o in self.opportunities 
                               if o['id'] == match.opportunity_id), None)
                    if opp:
                        capture_plans.append({
                            'contractor': contractor_name,
                            'opportunity_title': opp.get('title', ''),
                            'agency': opp.get('agency_parent', ''),
                            'score': match.score_total,
                            'strengths': ' | '.join(match.reasons_positive),
                            'gaps': ' | '.join(match.reasons_negative),
                            'teaming_strategy': ' | '.join(match.teaming_suggestions) or 'Prime standalone',
                            'capture_phase': 'Pre-RFP',
                            'next_actions': 'Schedule strategy session | Identify incumbent | Draft capability statement',
                            'rfp_date': opp.get('final_rfp_date', ''),
                            'est_value': opp.get('est_value_mid', 0)
                        })
        
        if capture_plans:
            df = pd.DataFrame(capture_plans)
            df.to_csv(f'{output_dir}/capture_plans_tier_a.csv', index=False)
            print(f"✓ Exported {len(capture_plans)} Tier A capture plans")
    
    def print_summary(self):
        """Print executive summary of matching results"""
        print("\n" + "="*60)
        print("LRAF MATCHING EXECUTIVE SUMMARY")
        print("="*60)
        
        total_tier_a = sum(d['tier_distribution']['A'] for d in self.matches.values())
        total_tier_b = sum(d['tier_distribution']['B'] for d in self.matches.values())
        total_qualified = total_tier_a + total_tier_b
        
        print(f"\n📊 Overall Statistics:")
        print(f"  • Contractors Processed: {len(self.contractors)}")
        print(f"  • Opportunities Analyzed: {len(self.opportunities)}")
        print(f"  • Total Qualified Matches: {total_qualified}")
        print(f"    - Tier A (Pursue Now): {total_tier_a}")
        print(f"    - Tier B (Monitor): {total_tier_b}")
        
        print(f"\n🎯 Top Performers:")
        # Sort contractors by Tier A count
        sorted_contractors = sorted(
            self.matches.items(), 
            key=lambda x: x[1]['tier_distribution']['A'], 
            reverse=True
        )
        
        for contractor_id, data in sorted_contractors[:3]:
            tier_dist = data['tier_distribution']
            print(f"  • {data['contractor_name']}:")
            print(f"    - Tier A: {tier_dist['A']}, Tier B: {tier_dist['B']}")
            print(f"    - Top Agencies: {', '.join(data['top_agencies'][:3])}")
        
        print("\n" + "="*60)


# Main execution script
if __name__ == "__main__":
    print("🚀 Starting LRAF Pipeline")
    print("-" * 60)
    
    # Initialize pipeline
    pipeline = LRAFPipeline()
    
    # Step 1: Load contractors
    print("\n📥 Loading Contractor Data...")
    contractor_result = pipeline.load_contractors_from_csv('contractor_profile.csv')
    
    if not contractor_result['success']:
        print("Failed to load contractors. Exiting.")
        exit(1)
    
    # Step 2: Load opportunities
    print("\n📥 Loading Opportunity Data...")
    opp_count = pipeline.load_opportunities_from_csv('opportunities.csv')
    
    if opp_count == 0:
        print("Failed to load opportunities. Exiting.")
        exit(1)
    
    # Step 3: Run matching
    pipeline.run_matching(top_k=100)
    
    # Step 4: Export results
    print("\n📤 Exporting Results...")
    pipeline.export_results('lraf_output')
    
    # Step 5: Print summary
    pipeline.print_summary()
    
    print("\n✅ LRAF Pipeline Complete!")
    print("Check the 'lraf_output' directory for detailed results.")
