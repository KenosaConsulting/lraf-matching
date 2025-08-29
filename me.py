import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re

@dataclass
class MatchResult:
    """Simplified match result structure"""
    opportunity_id: str
    contractor_id: str
    score_total: float
    tier: str
    cap: float
    breakdown: Dict[str, float]
    reasons: List[str]

class SimplifiedLRAFMatchingEngine:
    """Simplified 4-factor matching engine for demo"""
    
    def __init__(self):
        # Simplified 4-factor weights
        self.weights = {
            'capability_text': 0.60,  # Primary focus on capabilities
            'naics': 0.25,           # Industry alignment
            'psc': 0.10,             # Product/service codes
            'certifications': 0.05   # Basic compliance
        }
        
        # Simplified tier thresholds
        self.tier_thresholds = {
            'A': 0.70,  # Lowered for demo
            'B': 0.50,
            'C': 0.35
        }
    
    def enhanced_text_similarity(self, contractor_text: str, opp_text: str) -> float:
        """Enhanced text matching with keyword extraction"""
        if not contractor_text or not opp_text:
            return 0.0
        
        # Convert to lowercase for matching
        contractor_text = contractor_text.lower()
        opp_text = opp_text.lower()
        
        # Extract key technical terms (simple approach for demo)
        tech_keywords = ['cloud', 'aws', 'azure', 'devops', 'devsecops', 'kubernetes', 
                        'docker', 'ai', 'ml', 'data', 'cyber', 'security', 'network',
                        'software', 'hardware', 'engineering', 'support', 'maintenance',
                        'gis', 'geospatial', 'salesforce', 'servicenow', 'oracle',
                        'appian', 'records', 'management', 'digital', 'transformation',
                        'modernization', 'integration', 'automation', 'rpa', 'robotic',
                        'process', 'grant', 'compliance', 'fedramp', 'fisma', 'nist']
        
        # Count matching keywords
        contractor_keywords = set(word for word in tech_keywords if word in contractor_text)
        opp_keywords = set(word for word in tech_keywords if word in opp_text)
        
        keyword_overlap = len(contractor_keywords & opp_keywords) / max(len(opp_keywords), 1)
        
        # Simple word overlap
        contractor_words = set(contractor_text.split())
        opp_words = set(opp_text.split())
        word_overlap = len(contractor_words & opp_words) / max(len(opp_words), 1)
        
        # Weighted combination
        return min(1.0, (keyword_overlap * 0.7) + (word_overlap * 0.3))
    
    def naics_match(self, contractor_naics: List[str], opp_naics: str) -> float:
        """Simplified NAICS matching"""
        if not contractor_naics or not opp_naics:
            return 0.0
        
        opp_naics = str(opp_naics).strip()
        
        # Clean the opportunity NAICS (remove descriptions after dash)
        if '-' in opp_naics:
            opp_naics = opp_naics.split('-')[0].strip()
        
        # Exact match
        if opp_naics in contractor_naics:
            return 1.0
        
        # 4-digit match
        for c_naics in contractor_naics:
            if len(c_naics) >= 4 and len(opp_naics) >= 4:
                if c_naics[:4] == opp_naics[:4]:
                    return 0.75
        
        # 3-digit match
        for c_naics in contractor_naics:
            if len(c_naics) >= 3 and len(opp_naics) >= 3:
                if c_naics[:3] == opp_naics[:3]:
                    return 0.50
        
        # 2-digit match (same major category)
        for c_naics in contractor_naics:
            if len(c_naics) >= 2 and len(opp_naics) >= 2:
                if c_naics[:2] == opp_naics[:2]:
                    return 0.25
        
        return 0.0
    
    def psc_match(self, contractor_pscs: List[str], opp_psc: str) -> float:
        """Simplified PSC matching"""
        if not contractor_pscs or not opp_psc:
            return 0.0
        
        opp_psc = str(opp_psc).strip().upper()
        
        # Clean the opportunity PSC (remove descriptions after dash)
        if '-' in opp_psc:
            opp_psc = opp_psc.split('-')[0].strip()
        
        contractor_pscs = [p.upper() for p in contractor_pscs]
        
        # Exact match
        if opp_psc in contractor_pscs:
            return 1.0
        
        # Category match (first character for letters, first 2 for numbers)
        for c_psc in contractor_pscs:
            if c_psc and opp_psc:
                # Letter-based PSCs (R, D, etc.)
                if c_psc[0].isalpha() and opp_psc[0].isalpha():
                    if c_psc[0] == opp_psc[0]:
                        return 0.5
                # Number-based PSCs (70XX, 58XX, etc.)
                elif c_psc[0].isdigit() and opp_psc[0].isdigit():
                    if len(c_psc) >= 2 and len(opp_psc) >= 2:
                        if c_psc[:2] == opp_psc[:2]:
                            return 0.5
        
        return 0.0
    
    def certification_check(self, contractor: Dict, opportunity: Dict) -> float:
        """Simple certification compliance check"""
        set_aside = opportunity.get('set_aside', '')
        
        if not set_aside or set_aside in ['', 'TBD', 'Full and Open', 'Full and Open Competition', 
                                           'Small Business', 'To Be Determined']:
            return 1.0
        
        sb_flags = contractor.get('sb_flags', {})
        
        # Map various set-aside formats to flags
        set_aside_lower = set_aside.lower()
        
        # 8(a) variations
        if any(term in set_aside_lower for term in ['8(a)', '8a', 'eight(a)', 'eight a']):
            return 1.0 if sb_flags.get('8a', False) else 0.0
        
        # SDVOSB variations
        if any(term in set_aside_lower for term in ['sdvosb', 'service-disabled', 'service disabled', 
                                                     'veteran-owned', 'veteran owned']):
            return 1.0 if sb_flags.get('SDVOSB', False) else 0.0
        
        # WOSB variations
        if any(term in set_aside_lower for term in ['wosb', 'women-owned', 'women owned', 
                                                     'edwosb', 'economically disadvantaged']):
            return 1.0 if (sb_flags.get('WOSB', False) or sb_flags.get('EDWOSB', False)) else 0.0
        
        # HUBZone
        if 'hubzone' in set_aside_lower:
            return 1.0 if sb_flags.get('HUBZone', False) else 0.0
        
        # SDB
        if any(term in set_aside_lower for term in ['sdb', 'small disadvantaged']):
            return 1.0 if sb_flags.get('SDB', False) else 0.0
        
        # ISBEE
        if 'isbee' in set_aside_lower:
            return 1.0 if sb_flags.get('ISBEE', False) else 0.0
        
        # If it's a specific set-aside we don't recognize, be conservative
        if any(term in set_aside_lower for term in ['sole source', 'limited', 'restricted']):
            # Check if contractor has any small business certification
            if any(sb_flags.values()):
                return 0.5  # Partial credit
            else:
                return 0.0
        
        return 1.0
    
    def compute_gates(self, contractor: Dict, opportunity: Dict) -> float:
        """Simplified gates - only 2 gates"""
        cap = 1.0
        
        # Gate 1: Set-aside eligibility
        set_aside = opportunity.get('set_aside', '')
        if set_aside and set_aside not in ['', 'TBD', 'Full and Open', 'Full and Open Competition', 
                                           'Small Business', 'To Be Determined']:
            sb_flags = contractor.get('sb_flags', {})
            
            # Check if it's a specific set-aside
            set_aside_lower = set_aside.lower()
            specific_setaside = any(term in set_aside_lower for term in 
                                  ['8(a)', '8a', 'sdvosb', 'wosb', 'hubzone', 'sole source'])
            
            if specific_setaside and not any(sb_flags.values()):
                cap = min(cap, 0.50)
        
        # Gate 2: Security clearance
        required_clearance = opportunity.get('required_clearance', 'None')
        if required_clearance and required_clearance not in ['None', '', 'TBD', 'Unclassified', 
                                                             'Public Trust', 'To Be Determined']:
            contractor_clearance = contractor.get('facility_clearance', 'None')
            
            clearance_levels = {
                'None': 0, 
                'Unclassified': 0,
                'Public Trust': 1, 
                'Confidential': 2,
                'Secret': 3, 
                'Top Secret': 4,
                'TS/SCI': 5
            }
            
            contractor_level = clearance_levels.get(contractor_clearance, 0)
            required_level = clearance_levels.get(required_clearance, 0)
            
            if contractor_level < required_level:
                cap = min(cap, 0.30)
        
        return cap
    
    def score_opportunity(self, contractor: Dict, opportunity: Dict) -> MatchResult:
        """Main scoring function - simplified version"""
        
        # Compute features
        features = {}
        
        # 1. Capability text matching (60%)
        contractor_capability = contractor.get('capability_summary', '')
        opp_description = ' '.join([
            opportunity.get('title', ''),
            opportunity.get('description', ''),
            opportunity.get('work_type', '')
        ])
        features['capability_text'] = self.enhanced_text_similarity(
            contractor_capability, opp_description
        )
        
        # 2. NAICS matching (25%)
        features['naics'] = self.naics_match(
            contractor.get('naics', []),
            opportunity.get('naics', '')
        )
        
        # 3. PSC matching (10%)
        features['psc'] = self.psc_match(
            contractor.get('pscs', []),
            opportunity.get('psc', '')
        )
        
        # 4. Certification check (5%)
        features['certifications'] = self.certification_check(contractor, opportunity)
        
        # Calculate raw score
        raw_score = sum(self.weights[name] * features[name] for name in features)
        
        # Apply gates
        cap = self.compute_gates(contractor, opportunity)
        score_total = raw_score * cap
        
        # Determine tier
        if score_total >= self.tier_thresholds['A']:
            tier = 'A'
        elif score_total >= self.tier_thresholds['B']:
            tier = 'B'
        elif score_total >= self.tier_thresholds['C']:
            tier = 'C'
        else:
            tier = 'Ignore'
        
        # Generate simple reasons
        reasons = []
        if features['capability_text'] > 0.6:
            reasons.append(f"Strong capability match ({features['capability_text']:.0%})")
        if features['naics'] > 0.7:
            reasons.append(f"NAICS alignment ({features['naics']:.0%})")
        if features['psc'] > 0.5:
            reasons.append(f"PSC match ({features['psc']:.0%})")
        if cap < 1.0:
            reasons.append(f"Score capped at {cap:.0%}")
        if features['certifications'] == 0:
            reasons.append("Missing required certification")
        
        return MatchResult(
            opportunity_id=opportunity.get('id', ''),
            contractor_id=contractor.get('id', contractor.get('uei', '')),
            score_total=round(score_total, 3),
            tier=tier,
            cap=cap,
            breakdown={k: round(v, 3) for k, v in features.items()},
            reasons=reasons
        )
    
    def match_batch(self, contractor: Dict, opportunities: List[Dict], 
                    top_k: int = None) -> List[MatchResult]:
        """Match contractor against multiple opportunities"""
        results = []
        
        for opp in opportunities:
            match = self.score_opportunity(contractor, opp)
            results.append(match)
        
        # Sort by score
        results.sort(key=lambda x: x.score_total, reverse=True)
        
        # Return top K if specified, otherwise return all
        if top_k is not None:
            return results[:top_k]
        else:
            return results
