import pandas as pd
import numpy as np
import math
from rapidfuzz import fuzz

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def compute_features(row):
    """
    row: dictionary or pd.Series with found_* and missing_* prefixed columns
    """
    features = {}
    
    name_f = str(row.get('found_name', '')).lower()
    name_m = str(row.get('missing_name', '')).lower()
    
    # Text Features
    features['name_ratio'] = fuzz.ratio(name_f, name_m) / 100.0
    features['name_token_set'] = fuzz.token_set_ratio(name_f, name_m) / 100.0
    features['name_partial'] = fuzz.partial_ratio(name_f, name_m) / 100.0
    
    # Age Features
    f_min = row.get('found_age_min', -1)
    f_max = row.get('found_age_max', -1)
    m_min = row.get('missing_age_min', -1)
    m_max = row.get('missing_age_max', -1)
    
    if pd.isna(f_min) or pd.isna(m_min) or f_min == -1 or m_min == -1:
        features['age_overlap'] = 1 # Missing is neutral
        features['age_diff'] = 0
    else:
        # Do ranges overlap?
        overlap = max(0, min(f_max, m_max) - max(f_min, m_min))
        features['age_overlap'] = 1 if overlap >= 0 else 0
        
        # Center difference
        f_center = (f_min + f_max) / 2
        m_center = (m_min + m_max) / 2
        features['age_diff'] = abs(f_center - m_center)
        
    # Location Distance
    lat_f = row.get('found_lat')
    lon_f = row.get('found_lon')
    lat_m = row.get('missing_lat')
    lon_m = row.get('missing_lon')
    
    if pd.isna(lat_f) or pd.isna(lat_m):
        features['distance_km'] = 50.0 # Default penalty
    else:
        features['distance_km'] = haversine(lat_f, lon_f, lat_m, lon_m)
        
    # Baseline Rule Score
    name_score = features['name_token_set']
    age_score = 1.0 if features['age_overlap'] == 1 and features['age_diff'] <= 5 else 0.5
    loc_score = max(0, 1.0 - (features['distance_km'] / 20.0)) # 0 if > 20km
    
    features['baseline_score'] = (0.45 * name_score) + (0.20 * age_score) + (0.25 * loc_score) + 0.10
    
    return features
