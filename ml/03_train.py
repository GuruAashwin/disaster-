import pandas as pd
import numpy as np
import os
import json
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
from features import compute_features # local import (02_features.py renamed to features.py in next step or just import normally)

# Fix for import naming
import importlib.util
spec = importlib.util.spec_from_file_location("features_module", "ml/02_features.py")
features_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(features_module)
compute_features = features_module.compute_features

def create_pairs(df):
    """
    Creates positive (match) and negative (non-match) pairs from records.
    """
    print("Creating pairs...")
    found = df[df['type'] == 'found']
    missing = df[df['type'] == 'missing']
    
    pairs = []
    
    # Positive pairs (matches)
    for _, f_row in found.iterrows():
        m_row = missing[missing['person_id'] == f_row['person_id']]
        if not m_row.empty:
            m_row = m_row.iloc[0]
            pair = {
                'found_name': f_row['name'], 'missing_name': m_row['name'],
                'found_age_min': f_row['age_min'], 'found_age_max': f_row['age_max'],
                'missing_age_min': m_row['age_min'], 'missing_age_max': m_row['age_max'],
                'found_lat': f_row['lat'], 'found_lon': f_row['lon'],
                'missing_lat': m_row['lat'], 'missing_lon': m_row['lon'],
                'person_id': f_row['person_id'],
                'is_match': 1
            }
            pairs.append(pair)
            
    # Negative pairs (hard and easy)
    # Shuffle missing and pair randomly
    missing_shuffled = missing.sample(frac=1, random_state=42).reset_index(drop=True)
    for i, f_row in enumerate(found.head(len(found)).itertuples()):
        m_row = missing_shuffled.iloc[i]
        if m_row['person_id'] != f_row.person_id:
            pair = {
                'found_name': f_row.name, 'missing_name': m_row['name'],
                'found_age_min': f_row.age_min, 'found_age_max': f_row.age_max,
                'missing_age_min': m_row['age_min'], 'missing_age_max': m_row['age_max'],
                'found_lat': f_row.lat, 'found_lon': f_row.lon,
                'missing_lat': m_row['lat'], 'missing_lon': m_row['lon'],
                'person_id': f_row.person_id,
                'is_match': 0
            }
            pairs.append(pair)
            
    return pd.DataFrame(pairs)

def main():
    if not os.path.exists("data/synthetic_records.csv"):
        print("Run generate_data.py first!")
        return
        
    df = pd.read_csv("data/synthetic_records.csv")
    pairs_df = create_pairs(df)
    
    print("Computing features...")
    features_list = pairs_df.apply(compute_features, axis=1)
    features_df = pd.DataFrame(features_list.tolist())
    
    X = features_df[['name_ratio', 'name_token_set', 'name_partial', 'age_overlap', 'age_diff', 'distance_km']]
    y = pairs_df['is_match']
    groups = pairs_df['person_id']
    
    # Split preventing leakage
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(gss.split(X, y, groups))
    
    X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
    X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]
    
    print("Training ML Model...")
    base_clf = HistGradientBoostingClassifier(random_state=42, class_weight='balanced')
    clf = CalibratedClassifierCV(base_clf, cv=5, method='isotonic')
    clf.fit(X_train, y_train)
    
    print("Evaluating...")
    preds = clf.predict(X_test)
    probs = clf.predict_proba(X_test)[:, 1]
    
    metrics = {
        "precision": precision_score(y_test, preds),
        "recall": recall_score(y_test, preds),
        "f1": f1_score(y_test, preds),
        "auc": roc_auc_score(y_test, probs)
    }
    
    print(json.dumps(metrics, indent=2))
    
    os.makedirs("models", exist_ok=True)
    joblib.dump(clf, "models/matching_model.joblib")
    
    # Save metadata
    meta = {
        "version": "1.0.0",
        "features": list(X.columns),
        "metrics": metrics
    }
    with open("models/metadata.json", "w") as f:
        json.dump(meta, f)
    
    print("Model saved to models/matching_model.joblib")

if __name__ == "__main__":
    main()
