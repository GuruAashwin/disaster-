import pandas as pd
import numpy as np
import random
import uuid
import os

np.random.seed(42)
random.seed(42)

# Names based on Tamil Nadu context
FIRST_NAMES_EN = ["Arun", "Muthu", "Ravi", "Karthik", "Suresh", "Ramesh", "Priya", "Kavitha", "Lakshmi", "Bhavani", "Anbu", "Selvam"]
FIRST_NAMES_TA = ["அருண்", "முத்து", "ரவி", "கார்த்திக்", "சுரேஷ்", "ரமேஷ்", "பிரியா", "கவிதா", "லட்சுமி", "பவானி", "அன்பு", "செல்வம்"]
LAST_NAMES = ["Kumar", "Raj", "Kannan", "Swamy", "Natarajan", "Moorthy"]
INITIALS = ["K", "S", "R", "P", "M", "A", "V", "T"]

LOCATIONS = [
    ("Velachery Bus Stand", 12.9784, 80.2185),
    ("Tambaram Railway Station", 12.9249, 80.1100),
    ("Adyar Signal", 13.0012, 80.2565),
    ("Guindy Industrial Estate", 13.0116, 80.2114),
    ("Saidapet Bridge", 13.0213, 80.2231),
    ("Thiruvanmiyur Depot", 12.9863, 80.2588)
]

def corrupt_name(name):
    """Simulate realistic data entry errors, spelling variants, and initials."""
    r = random.random()
    if r < 0.2:
        return name.lower()
    if r < 0.4:
        # replace a vowel (Muthu -> Mutthu, Ravi -> Ravee)
        return name.replace('u', 'oo').replace('a', 'aa').replace('i', 'ee')
    if r < 0.6 and ' ' in name:
        # Swap first and last name (Kumar Arun)
        parts = name.split()
        if len(parts) == 2:
            return parts[1] + " " + parts[0]
    if r < 0.7:
        # Add random punctuation
        return name.replace(' ', '.')
    return name

def generate_true_people(n=5000):
    """Generate base ground-truth people."""
    people = []
    for _ in range(n):
        idx = random.randint(0, len(FIRST_NAMES_EN)-1)
        fname_en = FIRST_NAMES_EN[idx]
        lname = random.choice(LAST_NAMES)
        initial = random.choice(INITIALS)
        
        # Decide if name has initial or last name
        if random.random() < 0.5:
            full_name = f"{fname_en} {initial}"
        else:
            full_name = f"{fname_en} {lname}"
            
        age = random.randint(5, 85)
        gender = random.choice(["M", "F"])
        loc = random.choice(LOCATIONS)
        
        people.append({
            "person_id": str(uuid.uuid4()),
            "true_name": full_name,
            "true_age": age,
            "true_gender": gender,
            "true_lat": loc[1],
            "true_lon": loc[2],
            "base_loc_name": loc[0]
        })
    return people

def generate_records(true_people):
    """Generate noisy 'missing' and 'found' pairs for each person."""
    records = []
    for p in true_people:
        # 1. Missing Complaint (usually filed by family, relatively accurate but maybe vague loc)
        missing = {
            "record_id": str(uuid.uuid4()),
            "person_id": p["person_id"],
            "type": "missing",
            "name": p["true_name"] if random.random() < 0.8 else corrupt_name(p["true_name"]),
            "age_min": p["true_age"] - random.randint(0, 2),
            "age_max": p["true_age"] + random.randint(0, 2),
            "gender": p["true_gender"],
            "lat": p["true_lat"] + random.uniform(-0.01, 0.01),
            "lon": p["true_lon"] + random.uniform(-0.01, 0.01),
            "location_text": f"Lost near {p['base_loc_name']}"
        }
        
        # 2. Found Record (recorded by rescuer, high noise, age guessed)
        found = {
            "record_id": str(uuid.uuid4()),
            "person_id": p["person_id"],
            "type": "found",
            "name": corrupt_name(p["true_name"]) if random.random() < 0.7 else p["true_name"],
            # Age is often a guess, wider range
            "age_min": p["true_age"] - random.randint(2, 5), 
            "age_max": p["true_age"] + random.randint(2, 5),
            "gender": p["true_gender"] if random.random() < 0.95 else "Unknown",
            "lat": p["true_lat"] + random.uniform(-0.02, 0.02),
            "lon": p["true_lon"] + random.uniform(-0.02, 0.02),
            "location_text": f"Rescued at {p['base_loc_name']} area"
        }
        
        records.extend([missing, found])
        
    return pd.DataFrame(records)

def main():
    os.makedirs("data", exist_ok=True)
    print("Generating ground truth people...")
    true_people = generate_true_people(5000)
    
    print("Generating noisy records...")
    df = generate_records(true_people)
    
    # Save output
    output_path = "data/synthetic_records.csv"
    df.to_csv(output_path, index=False)
    print(f"Success! Saved {len(df)} synthetic records to ml/{output_path}")

if __name__ == "__main__":
    main()
