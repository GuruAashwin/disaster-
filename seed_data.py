import requests
import json
import random
from uuid import uuid4

BASE_URL = "http://localhost:8000"

def create_users():
    users = [
        {"username": "rescuer1", "password": "password", "role": "rescuer"},
        {"username": "police_admin", "password": "password", "role": "police"},
        {"username": "family_user", "password": "password", "role": "public"},
        {"username": "admin", "password": "password", "role": "admin"}
    ]
    for u in users:
        res = requests.post(f"{BASE_URL}/auth/register", json=u)
        print(f"Created user {u['username']}: {res.status_code}")

def seed_data():
    # Login as rescuer
    res = requests.post(f"{BASE_URL}/auth/login", data={"username": "rescuer1", "password": "password"})
    if res.status_code != 200:
        print("Login failed, ensure server is running!")
        return
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Database seeded with demo users and prepared for records.")

if __name__ == "__main__":
    create_users()
    seed_data()
