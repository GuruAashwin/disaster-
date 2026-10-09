import os
import json
import joblib
import pandas as pd
from rapidfuzz import fuzz
import math
from pathlib import Path
from app.services.image_similarity import compute_photos_confidence

# Try loading the model, fallback to rules if not found
MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../ml/models/matching_model.joblib")
try:
    clf = joblib.load(MODEL_PATH)
    ML_ENABLED = True
except:
    clf = None
    ML_ENABLED = False

# Path to person images directory
PERSON_IMAGES_DIR = Path(__file__).parent / "person_images"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def score_pair(found_record, missing_record):
    """
    Takes two dictionaries (already cleaned) and returns a score and reason.
    """
    name_f = str(found_record.get('name_cleaned', '')).lower()
    name_m = str(missing_record.get('name_cleaned', '')).lower()
    
    name_ratio = fuzz.ratio(name_f, name_m) / 100.0
    name_token_set = fuzz.token_set_ratio(name_f, name_m) / 100.0
    name_partial = fuzz.partial_ratio(name_f, name_m) / 100.0
    
    f_min = found_record.get('age_min', -1)
    f_max = found_record.get('age_max', -1)
    m_min = missing_record.get('age_min', -1)
    m_max = missing_record.get('age_max', -1)
    
    if f_min is None or m_min is None or f_min == -1 or m_min == -1:
        age_overlap = 1
        age_diff = 0
    else:
        overlap = max(0, min(f_max, m_max) - max(f_min, m_min))
        age_overlap = 1 if overlap >= 0 else 0
        f_center = (f_min + f_max) / 2
        m_center = (m_min + m_max) / 2
        age_diff = abs(f_center - m_center)
        
    lat_f = found_record.get('lat')
    lon_f = found_record.get('lon')
    lat_m = missing_record.get('lat')
    lon_m = missing_record.get('lon')
    
    if lat_f is None or lat_m is None:
        distance_km = 50.0
    else:
        distance_km = haversine(lat_f, lon_f, lat_m, lon_m)
        
    features = {
        'name_ratio': name_ratio,
        'name_token_set': name_token_set,
        'name_partial': name_partial,
        'age_overlap': age_overlap,
        'age_diff': age_diff,
        'distance_km': distance_km
    }
    
    # Reasons for explainability
    reasons = []
    if name_token_set > 0.8:
        reasons.append(f"Name highly similar ({name_f} / {name_m})")
    if age_overlap == 1 and age_diff <= 2:
        reasons.append("Age within 2 years")
    if distance_km < 5.0:
        reasons.append(f"Found near last-seen area ({distance_km:.1f} km)")
        
    score = 0
    model_version = "rules-v1"
    
    if ML_ENABLED and clf is not None:
        # Use ML model
        X = pd.DataFrame([features])
        prob = clf.predict_proba(X)[0][1]
        score = float(prob)
        model_version = "ml-v1"
    else:
        # Fallback Baseline Rule
        age_score = 1.0 if age_overlap == 1 and age_diff <= 5 else 0.5
        loc_score = max(0, 1.0 - (distance_km / 20.0))
        score = (0.45 * name_token_set) + (0.20 * age_score) + (0.25 * loc_score) + 0.10
        
    return {
        "score": score,
        "reasons": reasons,
        "model_version": model_version,
        "raw_features": features
    }


def compute_photo_match_confidence(found_person, missing_person):
    """
    Compute photo match confidence between two persons.
    
    Args:
        found_person: Person ORM object (found type)
        missing_person: Person ORM object (missing type)
        
    Returns:
        Confidence score 0-100, or 0 if no photos available
    """
    try:
        found_photos = found_person.photo_filenames or []
        missing_photos = missing_person.photo_filenames or []
        
        if not found_photos or not missing_photos:
            return 0.0
        
        # Compute image similarity
        confidence = compute_photos_confidence(
            found_photos,
            missing_photos,
            PERSON_IMAGES_DIR
        )
        
        return confidence
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error computing photo confidence: {e}")
        return 0.0
