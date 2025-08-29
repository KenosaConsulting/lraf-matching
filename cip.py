import pandas as pd
import json
from typing import Dict, List, Optional

class SimplifiedContractorIngestion:
    """Contractor ingestion for TSV files with capability merging"""
    
    def __init__(self):
        self.required_fields = {
            'legal_name', 'uei', 'capability_summary', 'naics'
        }
        self.contractors = []
        self.validation_errors = []
    
    def parse_json_field(self, field_value: str) -> Dict:
        """Parse JSON fields safely"""
        if pd.isna(field_value) or field_value == '':
            return {}
        
        if isinstance(field_value, dict):
            return field_value
            
        try:
            if isinstance(field_value, str):
                field_value = field_value.replace("True", "true").replace("False", "false")
                return json.loads(field_value)
        except:
            return {}
    
    def process_contractor_row(self, row: pd.Series, row_idx: int, capabilities_df: pd.DataFrame = None) -> Optional[Dict]:
        """Process contractor data with optional capabilities enhancement"""
        contractor = {}
        
        # Essential identity
        contractor['legal_name'] = str(row.get('legal_name', 'Unknown')).strip()
        contractor['uei'] = str(row.get('uei', '')).strip()[:12]
        contractor['id'] = contractor['uei']
        
        # Capability statement - combine from multiple sources
        base_capability = str(row.get('capability_summary', '')).strip()
        
        # If we have capabilities data, enhance the capability statement
        if capabilities_df is not None and len(capabilities_df) > 0:
            # Combine all capability-related fields from capabilities file
            capability_parts = [base_capability]
            
            for _, cap_row in capabilities_df.iterrows():
                # Add background summaries
                if pd.notna(cap_row.get('background_summary')):
                    capability_parts.append(str(cap_row['background_summary']))
                
                # Add expertise areas
                if pd.notna(cap_row.get('expertise_areas')):
                    capability_parts.append(str(cap_row['expertise_areas']))
                
                # Add key capabilities
                if pd.notna(cap_row.get('key_capabilities')):
                    capability_parts.append(str(cap_row['key_capabilities']))
            
            # Combine all parts into comprehensive capability statement
            contractor['capability_summary'] = ' '.join(filter(None, capability_parts))
        else:
            contractor['capability_summary'] = base_capability
        
        # Add capability keywords if available
        if pd.notna(row.get('capability_keywords')):
            keywords = str(row.get('capability_keywords', '')).strip()
            contractor['capability_summary'] += f" Keywords: {keywords}"
        
        # NAICS codes
        naics_field = row.get('naics', '')
        if pd.notna(naics_field):
            if isinstance(naics_field, str):
                contractor['naics'] = [c.strip() for c in naics_field.split(';') if c.strip()]
            else:
                contractor['naics'] = [str(naics_field)]
        else:
            contractor['naics'] = []
        
        # PSC codes
        psc_field = row.get('pscs', '')
        if pd.notna(psc_field):
            if isinstance(psc_field, str):
                contractor['pscs'] = [c.strip().upper() for c in psc_field.split(';') if c.strip()]
            else:
                contractor['pscs'] = [str(psc_field).upper()]
        else:
            contractor['pscs'] = []
        
        # Small business flags
        sb_flags = self.parse_json_field(row.get('sb_flags', '{}'))
        contractor['sb_flags'] = {
            '8a': sb_flags.get('8a', False),
            'SDVOSB': sb_flags.get('SDVOSB', False),
            'WOSB': sb_flags.get('WOSB', False),
            'EDWOSB': sb_flags.get('EDWOSB', False),
            'HUBZone': sb_flags.get('HUBZone', False),
            'SDB': sb_flags.get('SDB', False),
            'ISBEE': sb_flags.get('ISBEE', False)
        }
        
        # Security clearance
        contractor['facility_clearance'] = str(row.get('facility_clearance', 'None')).strip()
        
        # Additional fields for better matching
        contractor['website'] = str(row.get('website', '')).strip()
        contractor['target_agencies'] = str(row.get('target_agencies', '')).strip()
        
        return contractor
    
    def ingest_tsv_with_capabilities(self, profile_filepath: str, capabilities_filepath: str = None) -> Dict:
        """Load contractor from TSV profile and optionally merge with capabilities"""
        try:
            # Load the contractor profile (TSV format)
            print(f"Loading contractor profile from {profile_filepath}")
            profile_df = pd.read_csv(profile_filepath, sep='\t')
            print(f"  Found {len(profile_df)} contractor(s) in profile")
            
            # Load capabilities if provided
            capabilities_df = None
            if capabilities_filepath:
                print(f"Loading capabilities from {capabilities_filepath}")
                capabilities_df = pd.read_csv(capabilities_filepath, sep='\t')
                print(f"  Found {len(capabilities_df)} capability records")
            
            # Process each contractor
            for idx, row in profile_df.iterrows():
                contractor = self.process_contractor_row(row, idx + 2, capabilities_df)
                if contractor:
                    self.contractors.append(contractor)
            
            # Validation
            valid_contractors = []
            for c in self.contractors:
                if c.get('capability_summary') and len(c.get('capability_summary', '')) > 20:
                    valid_contractors.append(c)
                    print(f"  ✓ Loaded {c.get('legal_name')}")
                else:
                    print(f"  ⚠️  Skipping {c.get('legal_name')} - insufficient capability description")
            
            self.contractors = valid_contractors
            
            return {
                'success': True,
                'contractors_loaded': len(self.contractors)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
