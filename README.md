# LRAF Matching System - Complete Setup & Usage Guide

## 📁 Project Structure

First, organize your files in this structure:

```
lraf-matching/
│
├── code/
│   ├── contractor_ingestion.py    # Contractor data ingestion module
│   ├── matching_engine.py         # Core matching algorithm
│   └── lraf_pipeline.py          # Main integration script
│
├── data/
│   ├── contractors/               # Contractor data files
│   │   ├── contractor_profile.csv
│   │   └── past_performance.csv
│   │
│   └── forecasts/                # Opportunity/forecast files
│       └── opportunities.csv
│
├── lraf_output/                  # Generated results (auto-created)
│   ├── matching_summary.csv
│   ├── capture_plans_tier_a.csv
│   └── [contractor_name]_matches.csv
│
└── README.md                     # This file
```

## 🚀 Step-by-Step Setup Instructions

### Step 1: Install Python Dependencies

Open a terminal/command prompt and run:

```bash
# Navigate to your project directory
cd lraf-matching

# Install required packages
pip install pandas numpy
```

### Step 2: Set Up Your File Structure

```bash
# Create the directory structure
mkdir -p code data/contractors data/forecasts lraf_output

# Move your Python files to the code directory
# Move this README to the root directory
```

### Step 3: Prepare Your Data Files

#### A. Contractor Profile CSV (`data/contractors/contractor_profile.csv`)

Your contractor CSV must have these columns (order doesn't matter):

```csv
legal_name,dba,uei,cage,website,bd_lead_name,bd_lead_email,bd_lead_phone,sb_flags,capability_summary,capability_keywords,naics,pscs,vehicles,vehicle_role,facility_clearance,cleared_headcount,avg_annual_receipts_3yr,avg_employees_12mo,places_of_performance,internal_bid_cycle_days,target_agencies,min_deal_value
```

**Example row:**
```csv
Acme GovTech LLC,,ABCDEF123XYZ,1A2B3,https://acmegov.com,Jane Doe,jane@acmegov.com,555-123-4567,"{""8a"":true,""HUBZone"":true}","Cloud migration and DevSecOps for DoD and civilian agencies with focus on zero trust architecture","cloud migration;zero trust;devsecops;kubernetes;aws","541512;541513","D399;R499","GSA MAS;8(a) STARS III","{""GSA MAS"":""prime"",""8(a) STARS III"":""sub""}",Secret,8,12500000,42,"[{""city"":""San Antonio"",""state"":""TX"",""remote_ok"":true}]",45,"Department of Defense;Department of Interior",250000
```

#### B. Past Performance CSV (`data/contractors/past_performance.csv`)

```csv
title,agency_parent,agency_bureau,naics,psc,role,vehicle,contract_type,obligated_value,pop_start,pop_end,piid,short_description
```

**Example row:**
```csv
IT Operations Support,Department of the Air Force,AFMC,541513,D399,prime,GSA MAS,FFP,2750000,2022-05-01,2025-04-30,FA1234-22-F-5678,"24/7 NOC support with 98.9% uptime SLA"
```

#### C. Opportunities/Forecast CSV (`data/forecasts/opportunities.csv`)

Your standardized forecast file must have these columns:

```csv
source,source_url,agency,bureau,office,title,description,keywords,naics,pscs,set_aside,vehicle,contract_type,est_value_min,est_value_max,place_city,place_state,remote_ok,pop_est_start,rfi_date,draft_rfp_date,final_rfp_date,required_clearance,co_name,co_email,co_phone
```

**Example row:**
```csv
SAM.gov,https://sam.gov/opp/123,Department of Defense,Air Force,AFMC,Cloud Migration Services,"Seeking cloud migration and DevSecOps support for mission critical systems","cloud;migration;devsecops;aws",541512,D399,8(a),GSA MAS,FFP,2000000,3000000,Austin,TX,false,2025-06-01,2025-02-15,2025-03-15,2025-04-15,Secret,John Smith,john.smith@af.mil,555-987-6543
```

### Step 4: Data Preparation Tips

#### Formatting Requirements:

- **UEI**: Exactly 12 characters (e.g., `ABCDEF123XYZ`)
- **CAGE**: Exactly 5 characters (e.g., `1A2B3`)
- **NAICS**: 6-digit codes separated by semicolons (e.g., `541511;541512`)
- **PSCs**: 4-character codes separated by semicolons (e.g., `D399;R499`)
- **JSON fields**: Use double quotes for JSON (e.g., `{"8a":true}`)
- **Arrays**: Use semicolons to separate items in text fields
- **Dates**: Use YYYY-MM-DD format

## 💻 How to Use the Tool

### Basic Usage

1. **Navigate to your project directory:**
```bash
cd lraf-matching/code
```

2. **Run the main pipeline:**
```bash
python lraf_pipeline.py
```

The tool will automatically:
- Load contractors from `data/contractors/contractor_profile.csv`
- Load past performance from `data/contractors/past_performance.csv`
- Load opportunities from `data/forecasts/opportunities.csv`
- Run matching algorithm for each contractor
- Generate results in `lraf_output/` directory

### What Happens When You Run It

```
🚀 Starting LRAF Pipeline
------------------------------------------------------------

📥 Loading Contractor Data...
✓ Loaded 15 contractors
✓ Loaded past performance data

📥 Loading Opportunity Data...
✓ Loaded 250 opportunities

🔄 Running matching for 15 contractors...
  Acme GovTech LLC: A:12 B:28 C:35
  TechCorp Federal: A:8 B:22 C:41
  [... continues for each contractor ...]

📤 Exporting Results...
✓ Exported summary to lraf_output/matching_summary.csv
✓ Exported individual match files to lraf_output/
✓ Exported 47 Tier A capture plans

============================================================
LRAF MATCHING EXECUTIVE SUMMARY
============================================================

📊 Overall Statistics:
  • Contractors Processed: 15
  • Opportunities Analyzed: 250
  • Total Qualified Matches: 285
    - Tier A (Pursue Now): 87
    - Tier B (Monitor): 198

🎯 Top Performers:
  • Acme GovTech LLC:
    - Tier A: 12, Tier B: 28
    - Top Agencies: DoD, VA, DHS
  [... top 3 contractors ...]

✅ LRAF Pipeline Complete!
```

## 📊 Understanding the Output

### 1. **matching_summary.csv**
High-level overview of all contractors:
- `contractor_name`: Company name
- `tier_a_count`: Number of "Pursue Now" opportunities
- `tier_b_count`: Number of "Monitor" opportunities  
- `total_qualified`: Sum of Tier A and B
- `top_agencies`: Agencies with most matches

### 2. **[contractor_name]_matches.csv**
Detailed matches for each contractor including:
- `title`: Opportunity title
- `agency`: Issuing agency
- `score`: Match score (0.000-1.000)
- `tier`: A (≥0.75), B (0.55-0.74), C (0.40-0.54)
- `naics_score`, `text_score`, `agency_score`: Component scores
- `top_reason`: Best matching factor
- `top_blocker`: Main limitation
- `teaming_needed`: Partnership recommendations
- `rfp_date`: Key deadline

### 3. **capture_plans_tier_a.csv**
Action plans for highest-priority opportunities:
- Pre-populated capture strategy
- Strengths and gaps analysis
- Teaming recommendations
- Next action items

## 🎯 Matching Score Interpretation

### Tier Definitions
- **Tier A (≥0.75)**: Strong match, pursue immediately
- **Tier B (0.55-0.74)**: Good match, monitor and prepare
- **Tier C (0.40-0.54)**: Potential match, consider teaming
- **Below 0.40**: Poor match, typically ignore

### Score Components (Weights)
- **Text Similarity (28%)**: Capability statement vs. opportunity description
- **NAICS Match (20%)**: Industry code alignment
- **Agency Affinity (16%)**: Past performance with agency
- **PSC Match (8%)**: Product/service code alignment
- **Timing Readiness (8%)**: Days until RFP vs. prep time
- **Value Fit (6%)**: Contract size vs. past performance
- **Role/Vehicle (6%)**: Prime/sub experience on vehicle
- **Geography (4%)**: Location feasibility
- **Certifications (4%)**: Required cert alignment

### Gates (Score Caps)
Certain mismatches cap the maximum possible score:
- Missing required vehicle: Cap at 0.60
- Missing set-aside certification: Cap at 0.50
- Insufficient clearance: Cap at 0.50
- Exceeds size standard: Cap at 0.70

## 🔧 Customization Options

### Adjust Matching Weights

Edit `matching_engine.py` line 15-25:
```python
self.weights = {
    'text': 0.28,        # Increase if capability statements are strong
    'naics': 0.20,       # Increase for NAICS-focused matching
    'agency': 0.16,      # Increase if past performance is key
    # ... adjust as needed (must sum to 1.0)
}
```

### Change Tier Thresholds

Edit `matching_engine.py` line 28-32:
```python
self.tier_thresholds = {
    'A': 0.75,   # Lower to get more Tier A matches
    'B': 0.55,   # Adjust middle tier range
    'C': 0.40    # Lower bound for consideration
}
```

### Modify Output Count

Edit `lraf_pipeline.py` line 234:
```python
# Change from top 50 to top 100 matches per contractor
pipeline.run_matching(top_k=100)
```

## 🐛 Troubleshooting

### Common Issues and Solutions

**"No contractors loaded"**
- Check CSV file path: `data/contractors/contractor_profile.csv`
- Verify CSV has headers matching the template
- Ensure UEI is 12 characters, CAGE is 5 characters

**"Invalid JSON in sb_flags"**
- Use double quotes in JSON: `{"8a":true}` not `{'8a':true}`
- Check for proper comma separation

**Low match scores for all opportunities**
- Verify capability_summary has rich keywords
- Check NAICS codes match between contractors and opportunities
- Ensure past_performance.csv is loaded if relying on agency affinity

**Missing output files**
- Check write permissions for `lraf_output/` directory
- Ensure no file locks from Excel or other programs

## 📝 Adding New Data

### To Add More Contractors
1. Append rows to `data/contractors/contractor_profile.csv`
2. Add corresponding past performance to `past_performance.csv`
3. Re-run the pipeline

### To Update Opportunities
1. Replace or append to `data/forecasts/opportunities.csv`
2. Re-run the pipeline for fresh matching

### To Process Multiple Forecast Files
Modify `lraf_pipeline.py` to load multiple files:
```python
# Around line 125, add:
pipeline.load_opportunities_from_csv('data/forecasts/forecast_file1.csv')
pipeline.load_opportunities_from_csv('data/forecasts/forecast_file2.csv')
```

## 🚦 Quick Start Checklist

- [ ] Python 3.7+ installed
- [ ] Created directory structure
- [ ] Placed Python files in `code/` directory
- [ ] Prepared contractor CSV with required columns
- [ ] Prepared opportunities CSV with required columns
- [ ] All UEIs are 12 characters
- [ ] All NAICS codes are 6 digits
- [ ] JSON fields use double quotes
- [ ] Dates in YYYY-MM-DD format
- [ ] Run `python lraf_pipeline.py` from `code/` directory
- [ ] Check `lraf_output/` for results

## 📧 Support Information

For issues or questions:
1. Check data formatting matches templates exactly
2. Verify all required columns are present
3. Review console output for specific error messages
4. Ensure Python dependencies are installed

## 🎯 Next Steps After Initial Run

1. **Review Tier A matches** in `capture_plans_tier_a.csv`
2. **Validate scores** with your BD team
3. **Adjust weights** based on domain expertise
4. **Schedule regular runs** (weekly/bi-weekly) with fresh forecasts
5. **Track win rates** to refine scoring algorithm

---

*Version 1.0 - LRAF Matching System*
