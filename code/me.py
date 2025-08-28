import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math
from datetime import datetime, timedelta

@dataclass
class MatchResult:
    """Structure for match results with explanations"""
    opportunity_id: str
    contractor_id: str
    score_total: float
    tier: str
    cap: float
    breakdown: Dict[str, float]
    reasons_positive: List[str]
    reasons_negative: List[str]
    teaming_suggestions: List[str]

class LRAFMatchingEngine:
    """Core matching engine for contractor-opportunity alignment"""
    
    def __init__(self):
        # Default weights (sum to 1.0)
        self.weights = {
            'text': 0.28,
            'naics': 0.20,
            'psc': 0.08,
            'agency': 0.16,
            'role_vehicle': 0.06,
            'value_fit': 0.06,
            'timing': 0.08,
            'geo': 0.04,
            'certs': 0.04
        }
        
        # Tier thresholds
        self.tier_thresholds = {
            'A': 0.75,
            'B': 0.55,
            'C': 0.40
        }
    
    def compute_gates(self, contractor: Dict, opportunity: Dict) -> Tuple[float, List[str]]:
        """
        Compute multiplicative gates/caps that limit max score
        Returns: (cap_total, list_of_active_gates)
        """
        gates = []
        gate_messages = []
        
        # Vehicle gate (0.60 if missing required vehicle)
        if opportunity.get('vehicle') and opportunity['vehicle'] != '':
            contractor_vehicles = contractor.get('vehicles', [])
            if opportunity['vehicle'] not in contractor_vehicles:
                gates.append(0.60)
                gate_messages.append(f"Missing vehicle: {opportunity['vehicle']} (cap at 0.60)")
        
        # Set-aside eligibility gate (0.50 if missing required cert)
        set_aside = opportunity.get('set_aside', '')
        if set_aside and set_aside not in ['', 'Small Business', 'Full and Open']:
            sb_flags = contractor.get('sb_flags', {})
            # Map common set-aside names to flag keys
            set_aside_map = {
                '8(a)': '8a',
                '8a': '8a',
                'SDVOSB': 'SDVOSB',
                'WOSB': 'WOSB',
                'EDWOSB': 'EDWOSB',
                'HUBZone': 'HUBZone',
                'VOSB': 'VOSB'
            }
            
            flag_key = set_aside_map.get(set_aside, set_aside)
            if not sb_flags.get(flag_key, False):
                gates.append(0.50)
                gate_messages.append(f"Missing set-aside: {set_aside} (cap at 0.50)")
        
        # Clearance gate (0.50 if insufficient clearance)
        required_clearance = opportunity.get('required_clearance', 'None')
        contractor_clearance = contractor.get('facility_clearance', 'None')
        
        clearance_levels = {
            'None': 0, 'Public': 1, 'Secret': 2, 
            'Top Secret': 3, 'TS': 3, 'TS-SCI': 4
        }
        
        if clearance_levels.get(required_clearance, 0) > clearance_levels.get(contractor_clearance, 0):
            gates.append(0.50)
            gate_messages.append(f"Insufficient clearance: need {required_clearance} (cap at 0.50)")
        
        # Size standard gate (0.70 if exceeds size for primary NAICS)
        # Simplified check - in production, would check against actual SBA size standards
        if opportunity.get('naics') and contractor.get('avg_annual_receipts_3yr'):
            primary_naics = opportunity['naics'][0] if isinstance(opportunity['naics'], list) else opportunity['naics']
            # Simplified: assume $34M threshold for IT services NAICS
            if primary_naics and primary_naics.startswith('54'):
                if contractor.get('avg_annual_receipts_3yr', 0) > 34000000:
                    gates.append(0.70)
                    gate_messages.append(f"Exceeds size standard for NAICS {primary_naics} (cap at 0.70)")
        
        # Calculate total cap
        cap_total = min(gates) if gates else 1.0
        
        return cap_total, gate_messages
    
    def naics_similarity(self, contractor_naics: List[str], opp_naics: List[str]) -> float:
        """
        Compute NAICS similarity with hierarchical matching
        Exact match: 1.0, Same 4-digit: 0.7, Same 3-digit: 0.5
        """
        if not contractor_naics or not opp_naics:
            return 0.0
        
        # Ensure we're working with lists
        if isinstance(contractor_naics, str):
            contractor_naics = [contractor_naics]
        if isinstance(opp_naics, str):
            opp_naics = [opp_naics]
        
        scores = []
        for opp_code in opp_naics:
            best_score = 0.0
            for cont_code in contractor_naics:
                if cont_code == opp_code:
                    best_score = 1.0
                elif cont_code[:4] == opp_code[:4]:
                    best_score = max(best_score, 0.7)
                elif cont_code[:3] == opp_code[:3]:
                    best_score = max(best_score, 0.5)
            scores.append(best_score)
        
        return np.mean(scores) if scores else 0.0
    
    def psc_similarity(self, contractor_pscs: List[str], opp_pscs: List[str]) -> float:
        """
        Compute PSC similarity
        Exact match: 1.0, Same category (first char): 0.6
        """
        if not contractor_pscs or not opp_pscs:
            return 0.0
        
        # Ensure lists
        if isinstance(contractor_pscs, str):
            contractor_pscs = [contractor_pscs]
        if isinstance(opp_pscs, str):
            opp_pscs = [opp_pscs]
        
        scores = []
        for opp_psc in opp_pscs:
            best_score = 0.0
            for cont_psc in contractor_pscs:
                if cont_psc == opp_psc:
                    best_score = 1.0
                elif cont_psc and opp_psc and cont_psc[0] == opp_psc[0]:
                    best_score = max(best_score, 0.6)
            scores.append(best_score)
        
        return np.mean(scores) if scores else 0.0
    
    def text_similarity(self, contractor_text: str, opp_text: str) -> float:
        """
        Simplified text similarity using keyword overlap
        In production, would use embeddings and cosine similarity
        """
        if not contractor_text or not opp_text:
            return 0.0
        
        # Simple keyword extraction and overlap
        cont_words = set(contractor_text.lower().split())
        opp_words = set(opp_text.lower().split())
        
        if not cont_words or not opp_words:
            return 0.0
        
        intersection = cont_words & opp_words
        union = cont_words | opp_words
        
        return len(intersection) / len(union) if union else 0.0
    
    def agency_affinity(self, contractor: Dict, opportunity: Dict) -> float:
        """
        Compute agency affinity based on past performance
        Uses Laplace smoothing: 1 - exp(-(n/k))
        """
        past_perf = contractor.get('past_performance', [])
        opp_agency = opportunity.get('agency_parent', '')
        
        if not past_perf or not opp_agency:
            return 0.0
        
        # Count past performances at this agency
        agency_count = sum(1 for pp in past_perf 
                         if pp.get('agency_parent', '').lower() == opp_agency.lower())
        
        # Laplace smoothing with k=3
        k = 3.0
        return 1 - math.exp(-(agency_count / k))
    
    def role_vehicle_experience(self, contractor: Dict, opportunity: Dict) -> float:
        """
        Check for prime/sub experience on same vehicle
        """
        opp_vehicle = opportunity.get('vehicle', '')
        if not opp_vehicle:
            return 0.3  # Neutral if no vehicle specified
        
        vehicle_role = contractor.get('vehicle_role', {})
        
        if opp_vehicle in vehicle_role:
            role = vehicle_role[opp_vehicle]
            if role == 'prime':
                return 0.8
            elif role == 'sub':
                return 0.5
        
        # Check if they have the vehicle at all
        if opp_vehicle in contractor.get('vehicles', []):
            return 0.4
        
        return 0.0
    
    def value_fit(self, contractor: Dict, opportunity: Dict) -> float:
        """
        Compute value fit using log-ratio
        Score = exp(-abs(ln(ratio)) / tau)
        """
        opp_value = opportunity.get('est_value_mid')
        if not opp_value:
            # Try to compute from min/max
            val_min = opportunity.get('est_value_min', 0)
            val_max = opportunity.get('est_value_max', 0)
            if val_min and val_max:
                opp_value = (val_min + val_max) / 2
            else:
                return 0.5  # Neutral if no value info
        
        # Get contractor's median past performance value
        past_perf = contractor.get('past_performance', [])
        if past_perf:
            values = [pp.get('obligated_value', 0) for pp in past_perf if pp.get('obligated_value')]
            if values:
                median_value = np.median(values)
            else:
                median_value = 500000  # Default fallback
        else:
            median_value = 500000  # Default fallback
        
        # Compute ratio and score
        ratio = opp_value / median_value if median_value > 0 else 1.0
        tau = 0.7  # Controls decay rate
        
        return math.exp(-abs(math.log(ratio)) / tau) if ratio > 0 else 0.0
    
    def timing_readiness(self, contractor: Dict, opportunity: Dict) -> float:
        """
        Compute timing readiness using logistic function
        Score = 1 / (1 + exp(-(days - d0)/k))
        """
        # Get days until RFP
        rfp_date = opportunity.get('final_rfp_date') or opportunity.get('draft_rfp_date')
        if not rfp_date:
            return 0.5  # Neutral if no date info
        
        try:
            if isinstance(rfp_date, str):
                rfp_date = datetime.strptime(rfp_date[:10], '%Y-%m-%d')
            days_until = (rfp_date - datetime.now()).days
        except:
            return 0.5
        
        # Get contractor's internal cycle time
        internal_cycle = contractor.get('internal_bid_cycle_days', 45)
        
        # Logistic parameters
        d0 = internal_cycle  # Center point
        k = 10  # Steepness
        
        return 1 / (1 + math.exp(-(days_until - d0) / k))
    
    def geo_feasibility(self, contractor: Dict, opportunity: Dict) -> float:
        """
        Check geographic feasibility
        """
        opp_location = opportunity.get('place_of_performance', {})
        
        # Check if remote is allowed
        if opp_location.get('remote_ok'):
            return 1.0
        
        contractor_locations = contractor.get('places_of_performance', [])
        if not contractor_locations:
            return 0.3  # Low score if no locations specified
        
        # Check for location match (simplified)
        opp_state = opp_location.get('state', '')
        if opp_state:
            for loc in contractor_locations:
                if loc.get('state') == opp_state:
                    return 1.0
                if loc.get('remote_ok'):
                    return 0.8
        
        return 0.3
    
    def certs_alignment(self, contractor: Dict, opportunity: Dict) -> float:
        """
        Check certification alignment (CMMC, NIST, ISO, etc.)
        """
        required_certs = opportunity.get('required_certs', [])
        if not required_certs:
            return 0.5  # Neutral if no certs required
        
        contractor_certs = set()
        
        # Gather all contractor certifications
        if contractor.get('cmmc_level'):
            contractor_certs.add(f"CMMC-{contractor['cmmc_level']}")
        if contractor.get('iso_certs'):
            contractor_certs.update(contractor['iso_certs'])
        if contractor.get('nist_800_171') == 'compliant':
            contractor_certs.add('NIST-800-171')
        
        # Check overlap
        if not contractor_certs:
            return 0.0
        
        matches = sum(1 for cert in required_certs if cert in contractor_certs)
        return matches / len(required_certs) if required_certs else 0.5
    
    def compute_features(self, contractor: Dict, opportunity: Dict) -> Dict[str, float]:
        """Compute all feature scores"""
        features = {
            'text': self.text_similarity(
                contractor.get('capability_summary', ''),
                opportunity.get('description', '')
            ),
            'naics': self.naics_similarity(
                contractor.get('naics', []),
                opportunity.get('naics', [])
            ),
            'psc': self.psc_similarity(
                contractor.get('pscs', []),
                opportunity.get('pscs', [])
            ),
            'agency': self.agency_affinity(contractor, opportunity),
            'role_vehicle': self.role_vehicle_experience(contractor, opportunity),
            'value_fit': self.value_fit(contractor, opportunity),
            'timing': self.timing_readiness(contractor, opportunity),
            'geo': self.geo_feasibility(contractor, opportunity),
            'certs': self.certs_alignment(contractor, opportunity)
        }
        return features
    
    def explain_match(self, features: Dict[str, float], cap: float, gate_messages: List[str]) -> Tuple[List[str], List[str], List[str]]:
        """Generate human-readable explanations"""
        
        # Calculate weighted contributions
        contributions = [(name, self.weights[name] * score) 
                        for name, score in features.items()]
        contributions.sort(key=lambda x: x[1], reverse=True)
        
        # Top positive reasons
        reasons_positive = []
        for name, contrib in contributions[:3]:
            if contrib > 0.1:
                score = features[name]
                if name == 'naics' and score > 0.7:
                    reasons_positive.append(f"Strong NAICS alignment (score: {score:.2f})")
                elif name == 'text' and score > 0.6:
                    reasons_positive.append(f"High capability match (score: {score:.2f})")
                elif name == 'agency' and score > 0.5:
                    reasons_positive.append(f"Past performance with agency (score: {score:.2f})")
                elif contrib > 0.15:
                    reasons_positive.append(f"Strong {name} fit (score: {score:.2f})")
        
        # Negative reasons (low scores or gates)
        reasons_negative = gate_messages.copy()
        
        # Add low-scoring features
        for name, score in features.items():
            if score < 0.3:
                weight = self.weights[name]
                if weight > 0.1:  # Only mention important features
                    if name == 'naics':
                        reasons_negative.append(f"Weak NAICS match (score: {score:.2f})")
                    elif name == 'value_fit':
                        reasons_negative.append(f"Value mismatch (score: {score:.2f})")
                    elif name == 'timing':
                        reasons_negative.append(f"Timing concerns (score: {score:.2f})")
        
        # Teaming suggestions based on gates
        teaming_suggestions = []
        for msg in gate_messages:
            if "Missing vehicle" in msg:
                teaming_suggestions.append("Partner with vehicle holder")
            elif "Missing set-aside" in msg:
                cert = msg.split(':')[1].split('(')[0].strip()
                teaming_suggestions.append(f"Team with {cert}-certified firm")
            elif "Insufficient clearance" in msg:
                teaming_suggestions.append("Partner with cleared contractor")
        
        return reasons_positive[:3], reasons_negative[:3], teaming_suggestions
    
    def score_opportunity(self, contractor: Dict, opportunity: Dict) -> MatchResult:
        """
        Main scoring function - computes match score and tier
        """
        # Compute gates
        cap, gate_messages = self.compute_gates(contractor, opportunity)
        
        # Compute features
        features = self.compute_features(contractor, opportunity)
        
        # Calculate raw score
        raw_score = sum(self.weights[name] * features[name] 
                       for name in features)
        
        # Apply cap
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
        
        # Generate explanations
        reasons_pos, reasons_neg, teaming = self.explain_match(
            features, cap, gate_messages
        )
        
        return MatchResult(
            opportunity_id=opportunity.get('id', ''),
            contractor_id=contractor.get('id', ''),
            score_total=round(score_total, 3),
            tier=tier,
            cap=cap,
            breakdown={k: round(v, 3) for k, v in features.items()},
            reasons_positive=reasons_pos,
            reasons_negative=reasons_neg,
            teaming_suggestions=teaming
        )
    
    def match_batch(self, contractor: Dict, opportunities: List[Dict], 
                    top_k: int = 50) -> List[MatchResult]:
        """
        Match a contractor against multiple opportunities
        Returns top K matches sorted by score
        """
        results = []
        
        for opp in opportunities:
            match = self.score_opportunity(contractor, opp)
            results.append(match)
        
        # Sort by score and return top K
        results.sort(key=lambda x: x.score_total, reverse=True)
        return results[:top_k]
    
    def export_matches_to_csv(self, matches: List[MatchResult], output_file: str):
        """Export match results to CSV for analysis"""
        data = []
        for match in matches:
            data.append({
                'opportunity_id': match.opportunity_id,
                'contractor_id': match.contractor_id,
                'score': match.score_total,
                'tier': match.tier,
                'cap_applied': match.cap,
                'naics_score': match.breakdown.get('naics', 0),
                'text_score': match.breakdown.get('text', 0),
                'agency_score': match.breakdown.get('agency', 0),
                'value_score': match.breakdown.get('value_fit', 0),
                'timing_score': match.breakdown.get('timing', 0),
                'top_reason': match.reasons_positive[0] if match.reasons_positive else '',
                'top_blocker': match.reasons_negative[0] if match.reasons_negative else '',
                'teaming_needed': ', '.join(match.teaming_suggestions)
            })
        
        df = pd.DataFrame(data)
        df.to_csv(output_file, index=False)
        print(f"Exported {len(matches)} matches to {output_file}")


# Usage example
if __name__ == "__main__":
    # Initialize matching engine
    matcher = LRAFMatchingEngine()
    
    # Example contractor data
    contractor = {
        'id': 'contractor-001',
        'legal_name': 'Acme GovTech LLC',
        'uei': 'ABCDEF123XYZ',
        'naics': ['541511', '541512', '541513'],
        'pscs': ['D399', 'R499'],
        'capability_summary': 'Cloud migration DevSecOps zero trust cybersecurity',
        'sb_flags': {'8a': True, 'HUBZone': True},
        'vehicles': ['GSA MAS', '8(a) STARS III'],
        'vehicle_role': {'GSA MAS': 'prime', '8(a) STARS III': 'sub'},
        'facility_clearance': 'Secret',
        'avg_annual_receipts_3yr': 12500000,
        'internal_bid_cycle_days': 45,
        'places_of_performance': [{'state': 'TX', 'city': 'San Antonio', 'remote_ok': True}],
        'past_performance': [
            {
                'agency_parent': 'Department of Defense',
                'obligated_value': 2750000,
                'naics': '541513'
            }
        ]
    }
    
    # Example opportunity
    opportunity = {
        'id': 'opp-001',
        'title': 'Cloud Migration Services',
        'description': 'DevSecOps cloud migration zero trust implementation',
        'agency_parent': 'Department of Defense',
        'naics': ['541512'],
        'pscs': ['D399'],
        'set_aside': '8(a)',
        'vehicle': 'GSA MAS',
        'est_value_min': 2000000,
        'est_value_max': 3000000,
        'est_value_mid': 2500000,
        'final_rfp_date': '2025-03-15',
        'place_of_performance': {'state': 'TX', 'city': 'Austin'},
        'required_clearance': 'Secret'
    }
    
    # Score the match
    result = matcher.score_opportunity(contractor, opportunity)
    
    print(f"\nMatch Result:")
    print(f"  Score: {result.score_total:.3f}")
    print(f"  Tier: {result.tier}")
    print(f"  Cap Applied: {result.cap}")
    print(f"\nScore Breakdown:")
    for feature, score in result.breakdown.items():
        print(f"  {feature}: {score:.3f}")
    print(f"\nPositive Factors:")
    for reason in result.reasons_positive:
        print(f"  + {reason}")
    print(f"\nNegative Factors:")
    for reason in result.reasons_negative:
        print(f"  - {reason}")
    if result.teaming_suggestions:
        print(f"\nTeaming Suggestions:")
        for suggestion in result.teaming_suggestions:
            print(f"  → {suggestion}")
