"""
parse_and_filter_data.py — Parse JSON files and filter by target categories
"""
import json
import csv
import os
from pathlib import Path

# Target categories/skills
TARGET_SKILLS = [
    "tailoring", "embroidery", "sewing", "stitching",
    "carpentry", "woodworking", "carpenter", "wood",
    "beautician", "mehendi", "makeup", "hair", "beauty",
    "handicraft", "pottery", "weaving", "terracotta", "artisan",
    "welding", "metal", "fabrication", "welder"
]

def matches_target(text):
    """Check if text contains any target skill keywords"""
    if not text:
        return False
    text_lower = text.lower()
    return any(skill in text_lower for skill in TARGET_SKILLS)

def parse_schemes(input_file, output_file):
    """Parse myscheme_all_schemes.json and filter by categories"""
    print(f"\n📋 Parsing schemes from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    filtered = []
    for item in data:
        fields = item.get('fields', {})
        
        # Check scheme name, description, categories, and tags
        name = fields.get('schemeName', '')
        desc = fields.get('briefDescription', '')
        categories = ' '.join(fields.get('schemeCategory', []))
        tags = ' '.join(fields.get('tags', []))
        
        combined_text = f"{name} {desc} {categories} {tags}"
        
        if matches_target(combined_text):
            filtered.append({
                'id': item.get('id', ''),
                'name': name,
                'description': desc,
                'ministry': fields.get('nodalMinistryName', ''),
                'categories': '|'.join(fields.get('schemeCategory', [])),
                'tags': '|'.join(fields.get('tags', [])),
                'state': '|'.join(fields.get('beneficiaryState', [])),
                'level': fields.get('level', ''),
                'url': fields.get('slug', '')
            })
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if filtered:
            writer = csv.DictWriter(f, fieldnames=filtered[0].keys())
            writer.writeheader()
            writer.writerows(filtered)
    
    print(f"✅ Filtered {len(filtered)} schemes → {output_file}")
    return len(filtered)

def parse_jobs(input_file, output_file):
    """Parse ncs_job_listings.json and filter by skills/functional area"""
    print(f"\n💼 Parsing jobs from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    filtered = []
    for item in data:
        # Check job title, description, skills, and functional area
        title = item.get('jobTitle', '')
        desc = item.get('jobDescription', '')
        skills = ' '.join(item.get('requiredSkills', []))
        functional = item.get('functionalArea', '')
        
        combined_text = f"{title} {desc} {skills} {functional}"
        
        if matches_target(combined_text):
            locations = item.get('jobLocations', [])
            location_str = ', '.join([loc.get('city', '') for loc in locations]) if locations else 'All India'
            
            filtered.append({
                'id': item.get('id', ''),
                'title': title,
                'description': desc[:500],  # Truncate long descriptions
                'company': item.get('employerId', ''),
                'skills': '|'.join(item.get('requiredSkills', [])),
                'location': location_str,
                'job_type': item.get('jobType', ''),
                'vacancies': item.get('noOfVacancies', 0),
                'min_salary': item.get('minSalary', 0),
                'max_salary': item.get('maxSalary', 0),
                'experience': f"{item.get('minExperience', 0)}-{item.get('maxExperience', 0)}"
            })
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if filtered:
            writer = csv.DictWriter(f, fieldnames=filtered[0].keys())
            writer.writeheader()
            writer.writerows(filtered)
    
    print(f"✅ Filtered {len(filtered)} jobs → {output_file}")
    return len(filtered)

def parse_training(input_file, output_file):
    """Parse skill_india_training_centers.json and filter by courses"""
    print(f"\n🎓 Parsing training centers from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    filtered = []
    for item in data:
        tc_name = item.get('TcName', '')
        qp_details = item.get('QpDetails', [])
        
        # Check training center name and course names
        courses = ' '.join([qp.get('QpName', '') for qp in qp_details])
        combined_text = f"{tc_name} {courses}"
        
        if matches_target(combined_text):
            location = item.get('TcLocation', {})
            
            # Get all relevant courses
            course_list = [qp.get('QpName', '') for qp in qp_details]
            
            filtered.append({
                'id': item.get('Id', ''),
                'name': tc_name,
                'description': f"Training center offering: {', '.join(course_list[:3])}",
                'provider': item.get('TrainingProviderId', ''),
                'skills': '|'.join(course_list),
                'location': f"{location.get('District', '')}, {location.get('State', '')}",
                'address': location.get('AddressLine1', ''),
                'contact': item.get('TcSpocMobile', ''),
                'email': item.get('TcSpocEmail', '')
            })
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if filtered:
            writer = csv.DictWriter(f, fieldnames=filtered[0].keys())
            writer.writeheader()
            writer.writerows(filtered)
    
    print(f"✅ Filtered {len(filtered)} training centers → {output_file}")
    return len(filtered)

if __name__ == "__main__":
    # Set paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    
    # Input files
    schemes_input = data_dir / "myscheme_all_schemes.json"
    jobs_input = data_dir / "ncs_job_listings.json"
    training_input = data_dir / "skill_india_training_centers.json"
    
    # Output files
    schemes_output = data_dir / "schemes_filtered.csv"
    jobs_output = data_dir / "jobs_filtered.csv"
    training_output = data_dir / "upskill_filtered.csv"
    
    print("="*80)
    print("FILTERING DATA FOR TARGET CATEGORIES")
    print("="*80)
    print("\nTarget Skills:")
    print("1. Tailoring & Embroidery")
    print("2. Carpentry & Woodworking")
    print("3. Beautician (Mehendi/Makeup/Hair)")
    print("4. Handicraft Artisan (Pottery/Weaving/Terracotta)")
    print("5. Welding / Metal Fabrication")
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
