import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Optional
import uuid

class ContractorIngestion:
    """MVP contractor data ingestion pipeline with validation"""
    
    def __init__(self):
        self.required_fields = {
            'legal_name', 'uei', 'capability_summary', 
            'naics', 'sb_flags'
        }
        self.contractors = []
        self.validation_errors = []
    
    def validate_uei(self, uei: str) -> bool:
        """Validate UEI format (12 characters)"""
        if not uei or len(str(uei).strip()) != 12:
            return False
        return True
    
    def validate_cage(self, cage: str) -> bool:
        """Validate CAGE format (5 characters)"""
        if not cage:
            return True  # Optional field
        return len(str(cage).strip()) == 5
    
    def validate_naics(self, naics_codes: str) -> List[str]:
        """Validate and parse NAICS codes (6 digits each)"""
        if isinstance(naics_codes, str):
            codes = [c.strip() for c in naics_codes.split(';')]
        else:
            codes = naics_codes if isinstance(naics_codes, list) else []
        
        valid_codes = []
        for code in codes:
            if len(str(code)) == 6 and str(code).isdigit():
                valid_codes.append(str(code))
        return valid_codes
    
    def parse_json_field(self, field_value: str, field_name: str) -> Dict:
        """Parse JSON fields safely"""
        if pd.isna(field_value):
            return {}
        
        if isinstance(field_value, dict):
            return field_value
            
        try:
            # Handle both JSON and Python dict string formats
            if isinstance(field_value, str):
                # Replace Python boolean values with JSON format
                field_value = field_value.replace("True", "true").replace("False", "false")
                return json.loads(field_value)
        except:
            self.validation_errors.append(f"Invalid JSON in {field_name}: {field_value}")
            return {}
    
    def process_contractor_row(self, row: pd.Series, row_idx: int) -> Optional[Dict]:
        """Process and validate a single contractor row"""
        contractor = {
            'id': str(uuid.uuid4()),
            'created_at': datetime.now().isoformat()
        }
        
        errors = []
        
        # Basic identity validation
        if pd.notna(row.get('legal_name')):
            contractor['legal_name'] = str(row['legal_name']).strip()
        else:
            errors.append(f"Row {row_idx}: Missing legal_name")
        
        # UEI validation
        if pd.notna(row.get('uei')):
            uei = str(row['uei']).strip()
            if self.validate_uei(uei):
                contractor['uei'] = uei
            else:
                errors.append(f"Row {row_idx}: Invalid UEI format (must be 12 chars): {uei}")
        else:
            errors.append(f"Row {row_idx}: Missing UEI")
        
        # CAGE validation (optional)
        if pd.notna(row.get('cage')):
            cage = str(row['cage']).strip()
            if self.validate_cage(cage):
                contractor['cage'] = cage
            else:
                errors.append(f"Row {row_idx}: Invalid CAGE format (must be 5 chars): {cage}")
        
        # Contact information
        contractor['bd_lead_name'] = row.get('bd_lead_name', '')
        contractor['bd_lead_email'] = row.get('bd_lead_email', '')
        contractor['bd_lead_phone'] = row.get('bd_lead_phone', '')
        
        # Small business flags
        sb_flags = self.parse_json_field(row.get('sb_flags', '{}'), 'sb_flags')
        contractor['sb_flags'] = {
            '8a': sb_flags.get('8a', False),
            'SDVOSB': sb_flags.get('SDVOSB', False),
            'WOSB': sb_flags.get('WOSB', False),
            'EDWOSB': sb_flags.get('EDWOSB', False),
            'HUBZone': sb_flags.get('HUBZone', False),
            'VOSB': sb_flags.get('VOSB', False),
            'SmallBusiness': sb_flags.get('SmallBusiness', False)
        }
        
        # Capabilities
        contractor['capability_summary'] = row.get('capability_summary', '')
        
        # Keywords - handle as array
        keywords = row.get('capability_keywords', '')
        if isinstance(keywords, str):
            contractor['capability_keywords'] = [k.strip() for k in keywords.split(';') if k.strip()]
        else:
            contractor['capability_keywords'] = []
        
        # NAICS codes
        naics = self.validate_naics(row.get('naics', ''))
        if naics:
            contractor['naics'] = naics
            contractor['primary_naics'] = naics[0]  # First is primary
        else:
            errors.append(f"Row {row_idx}: Invalid or missing NAICS codes")
        
        # PSC codes
        pscs = row.get('pscs', '')
        if isinstance(pscs, str):
            contractor['pscs'] = [p.strip().upper() for p in pscs.split(';') 
                                 if p.strip() and len(p.strip()) == 4]
        else:
            contractor['pscs'] = []
        
        # Vehicles
        vehicles = row.get('vehicles', '')
        if isinstance(vehicles, str):
            contractor['vehicles'] = [v.strip() for v in vehicles.split(';') if v.strip()]
        else:
            contractor['vehicles'] = []
        
        # Vehicle roles
        contractor['vehicle_role'] = self.parse_json_field(
            row.get('vehicle_role', '{}'), 'vehicle_role'
        )
        
        # Security clearance
        contractor['facility_clearance'] = row.get('facility_clearance', 'None')
        contractor['cleared_headcount'] = int(row.get('cleared_headcount', 0)) if pd.notna(row.get('cleared_headcount')) else 0
        
        # Size standards
        if pd.notna(row.get('avg_annual_receipts_3yr')):
            contractor['avg_annual_receipts_3yr'] = float(row['avg_annual_receipts_3yr'])
        
        if pd.notna(row.get('avg_employees_12mo')):
            contractor['avg_employees_12mo'] = int(row['avg_employees_12mo'])
        
        # Operating constraints
        contractor['places_of_performance'] = self.parse_json_field(
            row.get('places_of_performance', '[]'), 'places_of_performance'
        )
        
        if pd.notna(row.get('internal_bid_cycle_days')):
            contractor['internal_bid_cycle_days'] = int(row['internal_bid_cycle_days'])
        
        # Strategic focus
        target_agencies = row.get('target_agencies', '')
        if isinstance(target_agencies, str):
            contractor['target_agencies'] = [a.strip() for a in target_agencies.split(';') if a.strip()]
        else:
            contractor['target_agencies'] = []
        
        if pd.notna(row.get('min_deal_value')):
            contractor['min_deal_value'] = float(row['min_deal_value'])
        
        if pd.notna(row.get('max_deal_value')):
            contractor['max_deal_value'] = float(row['max_deal_value'])
        
        # Store errors if any
        if errors:
            self.validation_errors.extend(errors)
            contractor['validation_errors'] = errors
        
        return contractor
    
    def ingest_csv(self, filepath: str) -> Dict:
        """Main ingestion method for CSV files"""
        try:
            df = pd.read_csv(filepath)
            print(f"Loading {len(df)} contractors from {filepath}")
            
            for idx, row in df.iterrows():
                contractor = self.process_contractor_row(row, idx + 2)  # +2 for header and 0-index
                if contractor:
                    self.contractors.append(contractor)
            
            return {
                'success': True,
                'contractors_loaded': len(self.contractors),
                'validation_errors': len(self.validation_errors),
                'errors': self.validation_errors[:10] if self.validation_errors else []
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'validation_errors': self.validation_errors
            }
    
    def ingest_past_performance_csv(self, filepath: str, contractor_uei: str) -> Dict:
        """Ingest past performance data for a specific contractor"""
        try:
            df = pd.read_csv(filepath)
            past_performances = []
            
            for idx, row in df.iterrows():
                pp = {
                    'contractor_uei': contractor_uei,
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
                past_performances.append(pp)
            
            return {
                'success': True,
                'past_performances_loaded': len(past_performances),
                'data': past_performances
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_to_json(self, output_file: str):
        """Export processed contractors to JSON for database import"""
        with open(output_file, 'w') as f:
            json.dump({
                'contractors': self.contractors,
                'metadata': {
                    'total_contractors': len(self.contractors),
                    'ingestion_timestamp': datetime.now().isoformat(),
                    'validation_errors': len(self.validation_errors)
                }
            }, f, indent=2)
        print(f"Exported {len(self.contractors)} contractors to {output_file}")
    
    def get_summary_stats(self) -> Dict:
        """Generate summary statistics of ingested contractors"""
        if not self.contractors:
            return {'message': 'No contractors loaded'}
        
        stats = {
            'total_contractors': len(self.contractors),
            'contractors_with_8a': sum(1 for c in self.contractors if c['sb_flags'].get('8a')),
            'contractors_with_hubzone': sum(1 for c in self.contractors if c['sb_flags'].get('HUBZone')),
            'contractors_with_clearance': sum(1 for c in self.contractors if c.get('facility_clearance') not in ['None', None, '']),
            'unique_naics': len(set(n for c in self.contractors for n in c.get('naics', []))),
            'contractors_with_vehicles': sum(1 for c in self.contractors if c.get('vehicles')),
            'validation_errors': len(self.validation_errors)
        }
        
        return stats


# Usage example
if __name__ == "__main__":
    # Initialize ingestion pipeline
    ingester = ContractorIngestion()
    
    # Ingest contractor profile data
    result = ingester.ingest_csv('contractor_profile.csv')
    print(f"Ingestion result: {result}")
    
    # Get summary statistics
    stats = ingester.get_summary_stats()
    print(f"\nSummary Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Export to JSON for database import
    ingester.export_to_json('contractors_processed.json')
    
    # Example: Ingest past performance for specific contractor
    # pp_result = ingester.ingest_past_performance_csv('past_performance.csv', 'ABCDEF123XYZ')
    # print(f"Past performance result: {pp_result}")
