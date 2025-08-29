# Navy LRAF Matching System - TSV Data Guide

## 🎯 Overview

This enhanced LRAF system processes TSV (Tab-Separated Values) data from Navy procurement forecasts and matches them with contractor capabilities. Key improvements:

- **TSV Support**: Handles tab-separated files from Navy systems
- **Dual-Source Contractor Data**: Combines profile + capabilities files
- **User Input**: Customize NAICS codes and target agencies
- **Navy-Specific**: Properly maps all Navy procurement fields

## 📁 Required File Structure

```
your_project/
├── cip.py                 # Contractor ingestion (TSV compatible)
├── me.py                  # Matching engine (4-factor scoring)
├── lraf-pi.py            # Main pipeline (Navy-specific)
├── run_navy_lraf.py      # Execution script
├── data/
│   ├── contractors/
│   │   ├── navancio_contractor_profile.tsv
│   │   └── navancio_capabilities_final.tsv
│   └── forecasts/
│       └── navy_procurement_consolidated.tsv
└── lraf_output/          # Results directory (created automatically)
```

## 🚀 Quick Start

### 1. Install Requirements
```bash
pip install pandas numpy
```

### 2. Place Your Files
Ensure all 4 Python files are in your project directory and TSV data files are in the correct subdirectories.

### 3. Run the System
```bash
python run_navy_lraf.py
```

### 4. Provide User Inputs
When prompted:
- **NAICS Codes**: Enter up to 5 primary NAICS codes (e.g., "541512, 541511, 518210")
- **Target Agency**: Press Enter for "Navy" or specify another agency

## 📊 Data File Requirements

### Contractor Profile TSV (`navancio_contractor_profile.tsv`)
Required columns:
- `legal_name` - Company legal name
- `uei` - Unique Entity Identifier
- `capability_summary` - Core capability statement
- `capability_keywords` - Searchable keywords (optional)
- `naics` - NAICS codes (semicolon-separated)
- `pscs` - PSC codes (semicolon-separated)
- `sb_flags` - Small business certifications (JSON format)
- `facility_clearance` - Security clearance level
- `target_agencies` - Preferred agencies (optional)

### Capabilities TSV (`navancio_capabilities_final.tsv`)
Enhances contractor profile with:
- `background_summary` - Detailed background per service area
- `expertise_areas` - Specific expertise descriptions
- `key_capabilities` - Detailed capability statements
- `service_area` - Service category

### Navy Procurement TSV (`navy_procurement_consolidated.tsv`)
Standard Navy columns (automatically mapped):
- `record_id` - Unique opportunity ID
- `Requirement Title` - Opportunity title
- `Requirement Description` - Detailed description
- `Associated Program or Requirement Office` - Agency/office
- `Anticipated NAICS Code` - Industry code
- `Anticipated PSC` - Product/service code
- `Anticipated Procurement Method` - Set-aside type
- `Anticipated Personnel Clearance` - Required clearance
- `value_min_millions` / `value_max_millions` - Value range
- `Anticipated Solicitation FY/Quarter` - RFP timing
- And 30+ other fields...

## 🎯 Scoring System

### 4-Factor Model (Simplified for Speed)
1. **Capability Text Match (60%)** - How well contractor capabilities match opportunity description
2. **NAICS Alignment (25%)** - Industry code matching (exact, 4-digit, or 3-digit)
3. **PSC Match (10%)** - Product/Service Code alignment
4. **Certifications (5%)** - Set-aside eligibility

### Performance Gates
- **Set-Aside Gate**: Wrong certification → Cap at 50%
- **Clearance Gate**: Insufficient clearance → Cap at 30%

### Tier Classifications
- **Tier A (≥70%)**: Strong match - pursue immediately
- **Tier B (50-69%)**: Good match - worth monitoring
- **Tier C (35-49%)**: Possible with teaming
- **Ignore (<35%)**: Not worth pursuing

## 📈 Output Files

The system generates three key files in `lraf_output/`:

### 1. `matching_summary.csv`
Overview of all contractors:
```csv
contractor_name,tier_a_count,tier_b_count,tier_c_count,total_qualified
NAVANCIO LLC,145,287,412,432
```

### 2. `tier_a_opportunities.csv`
High-priority opportunities to pursue:
```csv
contractor,opportunity,agency,score,capability_match,naics_match,rfp_fy,value_min_millions
NAVANCIO LLC,Cloud Migration Services,NAVSEA,0.875,0.82,1.0,2026,5.5
```

### 3. `[contractor]_matches.csv`
Detailed scoring for each contractor:
```csv
opportunity_id,title,score,tier,capability_match,naics_match,reasons,incumbent
```

## 🔧 Customization

### Adjust Scoring Weights
Edit `me.py` line 15:
```python
self.weights = {
    'capability_text': 0.60,  # Increase for text-heavy matching
    'naics': 0.25,           # Increase for strict NAICS alignment
    'psc': 0.10,             
    'certifications': 0.05   
}
```

### Change Tier Thresholds
Edit `me.py` line 22:
```python
self.tier_thresholds = {
    'A': 0.70,  # Lower to get more Tier A matches
    'B': 0.50,
    'C': 0.35
}
```

### Filter by Value Range
Add to `lraf-pi.py` after loading opportunities:
```python
# Filter to opportunities over $5M
self.opportunities = [o for o in self.opportunities 
                     if o.get('est_value_min', 0) >= 5.0]
```

## 🐛 Troubleshooting

### "No opportunities loaded"
- Check TSV file uses tabs, not commas
- Verify column names match Navy format
- Ensure file path is correct

### Low match scores
- Enhance contractor capability statements with more technical keywords
- Add relevant NAICS codes when prompted
- Check that PSC codes are properly formatted (uppercase)

### Memory issues with large files
- Process in batches by filtering `Source_Organization`
- Limit to specific fiscal years
- Reduce `top_k` parameter in matching

## 📝 Navy-Specific Features

1. **Multi-Agency Support**: Filters by `Source_Organization` and `Associated Program or Requirement Office`
2. **Value Parsing**: Handles Navy's complex value fields (min/max/anticipated)
3. **Timeline Tracking**: Captures FY and Quarter for solicitation and award
4. **Incumbent Analysis**: Tracks current contractors for competitive intel
5. **UIC Mapping**: Preserves Contracting Office UICs for POC identification

## 💡 Best Practices

1. **Enhance Capabilities**: Combine all capability documents into comprehensive statements
2. **NAICS Strategy**: Enter broad NAICS codes that cover multiple service areas
3. **Regular Updates**: Re-run weekly as Navy updates procurement forecasts
4. **Tier A Focus**: Concentrate BD efforts on Tier A matches only
5. **Incumbent Intel**: Check incumbent field for recompete opportunities

## 🚦 Quick Wins

For immediate high-value matches:
1. Enter IT-related NAICS codes: 541511, 541512, 541519
2. Target "TBD" set-asides (open competition)
3. Focus on Q1/Q2 FY26 opportunities (nearest term)
4. Look for "Follow-on" opportunities with no incumbent

---

**Version 2.0** - Navy TSV Edition
Last Updated: August 2025
