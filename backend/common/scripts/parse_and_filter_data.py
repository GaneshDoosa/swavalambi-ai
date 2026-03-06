"""
parse_and_filter_data.py — Parse JSON files and filter by target categories
"""
import json
import csv
import os
from pathlib import Path

# Target professions - 5 professions with balanced data
TARGET_PROFESSIONS = {
    "agriculture": ["agriculture", "farming", "farmer", "organic", "crop", "livestock", "dairy", "horticulture", "agri", "rural"],
    "tailoring": ["tailoring", "tailor", "sewing", "stitching", "embroidery", "garment", "textile", "fashion", "apparel"],
    "healthcare": ["healthcare", "health", "nursing", "nurse", "medical", "hospital", "clinic", "patient care", "home health", "wellness"],
    "tourism": ["tourism", "tourist", "hotel", "hospitality", "guest service", "travel", "resort", "housekeeping", "front office"],
    "electrician": ["electrician", "electrical", "electric", "wiring", "electronics", "solar", "power", "installation"]
}

# Limit per profession
LIMIT_PER_PROFESSION = 100

def matches_profession(text, profession_keywords):
    """Check if text contains any keywords for a specific profession"""
    if not text:
        return False
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in profession_keywords)

def categorize_by_profession(items, text_extractor):
    """Categorize items by profession and limit each to LIMIT_PER_PROFESSION"""
    categorized = {prof: [] for prof in TARGET_PROFESSIONS.keys()}
    
    for item in items:
        text = text_extractor(item)
        
        # Check which profession this item belongs to
        for profession, keywords in TARGET_PROFESSIONS.items():
            if matches_profession(text, keywords):
                if len(categorized[profession]) < LIMIT_PER_PROFESSION:
                    categorized[profession].append(item)
                break  # Only assign to first matching profession
    
    return categorized

def parse_schemes(input_file, output_file):
    """Parse myscheme_all_schemes.json and filter by professions (100 per profession)"""
    print(f"\n📋 Parsing schemes from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract text for categorization
    def extract_text(item):
        fields = item.get('fields', {})
        name = fields.get('schemeName', '')
        desc = fields.get('briefDescription', '')
        categories = ' '.join(fields.get('schemeCategory', []))
        tags = ' '.join(fields.get('tags', []))
        return f"{name} {desc} {categories} {tags}"
    
    # Categorize by profession
    categorized = categorize_by_profession(data, extract_text)
    
    # Convert to output format
    filtered = []
    for profession, items in categorized.items():
        print(f"  {profession}: {len(items)} schemes")
        for item in items:
            fields = item.get('fields', {})
            filtered.append({
                'id': item.get('id', ''),
                'name': fields.get('schemeName', ''),
                'description': fields.get('briefDescription', ''),
                'ministry': fields.get('nodalMinistryName', ''),
                'categories': '|'.join(fields.get('schemeCategory', [])),
                'tags': '|'.join(fields.get('tags', [])),
                'state': '|'.join(fields.get('beneficiaryState', [])),
                'level': fields.get('level', ''),
                'url': fields.get('slug', ''),
                'profession': profession
            })
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if filtered:
            writer = csv.DictWriter(f, fieldnames=filtered[0].keys())
            writer.writeheader()
            writer.writerows(filtered)
    
    print(f"✅ Filtered {len(filtered)} schemes (max 100 per profession) → {output_file}")
    return len(filtered)

def parse_jobs(input_file, output_file):
    """Parse ncs_job_listings.json and filter by professions (100 per profession)"""
    print(f"\n💼 Parsing jobs from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract text for categorization
    def extract_text(item):
        title = item.get('jobTitle', '')
        desc = item.get('jobDescription', '')
        skills = ' '.join(item.get('requiredSkills', []))
        functional = item.get('functionalArea', '')
        return f"{title} {desc} {skills} {functional}"
    
    # Categorize by profession
    categorized = categorize_by_profession(data, extract_text)
    
    # Convert to output format
    filtered = []
    for profession, items in categorized.items():
        print(f"  {profession}: {len(items)} jobs")
        for item in items:
            locations = item.get('jobLocations', [])
            location_str = ', '.join([loc.get('city', '') for loc in locations]) if locations else 'All India'
            
            filtered.append({
                'id': item.get('id', ''),
                'title': item.get('jobTitle', ''),
                'description': item.get('jobDescription', '')[:500],  # Truncate
                'company': item.get('employerId', ''),
                'skills': '|'.join(item.get('requiredSkills', [])),
                'location': location_str,
                'job_type': item.get('jobType', ''),
                'vacancies': item.get('noOfVacancies', 0),
                'min_salary': item.get('minSalary', 0),
                'max_salary': item.get('maxSalary', 0),
                'experience': f"{item.get('minExperience', 0)}-{item.get('maxExperience', 0)}",
                'profession': profession
            })
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if filtered:
            writer = csv.DictWriter(f, fieldnames=filtered[0].keys())
            writer.writeheader()
            writer.writerows(filtered)
    
    print(f"✅ Filtered {len(filtered)} jobs (max 100 per profession) → {output_file}")
    return len(filtered)

def parse_training(input_file, output_file):
    """Parse skill_india_training_centers.json and filter by professions (100 per profession)"""
    print(f"\n🎓 Parsing training centers from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract text for categorization
    def extract_text(item):
        tc_name = item.get('TcName', '')
        qp_details = item.get('QpDetails', [])
        courses = ' '.join([qp.get('QpName', '') for qp in qp_details])
        return f"{tc_name} {courses}"
    
    # Categorize by profession
    categorized = categorize_by_profession(data, extract_text)
    
    # Convert to output format
    filtered = []
    for profession, items in categorized.items():
        print(f"  {profession}: {len(items)} training centers")
        for item in items:
            location = item.get('TcLocation', {})
            qp_details = item.get('QpDetails', [])
            course_list = [qp.get('QpName', '') for qp in qp_details]
            
            filtered.append({
                'id': item.get('Id', ''),
                'name': item.get('TcName', ''),
                'description': f"Training center offering: {', '.join(course_list[:3])}",
                'provider': item.get('TrainingProviderId', ''),
                'skills': '|'.join(course_list),
                'location': f"{location.get('District', '')}, {location.get('State', '')}",
                'address': location.get('AddressLine1', ''),
                'contact': item.get('TcSpocMobile', ''),
                'email': item.get('TcSpocEmail', ''),
                'profession': profession
            })
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if filtered:
            writer = csv.DictWriter(f, fieldnames=filtered[0].keys())
            writer.writeheader()
            writer.writerows(filtered)
    
    print(f"✅ Filtered {len(filtered)} training centers (max 100 per profession) → {output_file}")
    return len(filtered)

if __name__ == "__main__":
    # Set paths - use Downloads directory for input files
    downloads_dir = Path.home() / "Downloads"
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    
    # Ensure data directory exists
    data_dir.mkdir(exist_ok=True)
    
    # Input files from Downloads
    schemes_input = downloads_dir / "myscheme_all_schemes.json"
    jobs_input = downloads_dir / "ncs_job_listings.json"
    training_input = downloads_dir / "skill_india_training_centers.json"
    
    # Output files to data directory
    schemes_output = data_dir / "schemes_filtered.csv"
    jobs_output = data_dir / "jobs_filtered.csv"
    training_output = data_dir / "upskill_filtered.csv"
    
    print("="*80)
    print("FILTERING DATA FOR TARGET PROFESSIONS")
    print("="*80)
    print("\nTarget Professions (High Coverage):")
    print("1. Agriculture & Farming")
    print("2. Tailoring & Garment")
    print("3. Healthcare & Nursing")
    print("4. Tourism & Hospitality")
    print("5. Electrician & Electronics")
    print("="*80)
    
    # Parse all files
    total_schemes = parse_schemes(schemes_input, schemes_output)
    total_jobs = parse_jobs(jobs_input, jobs_output)
    total_training = parse_training(training_input, training_output)
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"✅ Schemes: {total_schemes} filtered records")
    print(f"✅ Jobs: {total_jobs} filtered records")
    print(f"✅ Training: {total_training} filtered records")
    print(f"\nTotal: {total_schemes + total_jobs + total_training} records")
    print("="*80)
