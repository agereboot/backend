import requests
import json
import uuid

BASE_URL = "http://127.0.0.1:8000"

def get_token():
    # Attempt to login or use a known token
    # For this script, we assume the server is running and we can get a token
    login_url = f"{BASE_URL}/api/token/" # Adjust if different
    # Skipping actual login for now, assuming we might need to create a user first
    pass

def test_mental_health():
    print("\n--- Testing Mental Health ---")
    # 1. Questions
    resp = requests.get(f"{BASE_URL}/health/mental-assessment/questions")
    print(f"GET Questions: {resp.status_code}")
    if resp.status_code == 200:
        questions = resp.json()["questions"]
        print(f"Fetched {len(questions)} questions")
        
        # 2. Submit
        answers = [{"id": q["id"], "score": 2} for q in questions[:5]]
        resp = requests.post(f"{BASE_URL}/health/mental-assessment/submit", json={"answers": answers})
        print(f"POST Submit: {resp.status_code}")
        if resp.status_code == 200:
            print("Submission successful")
            
    # 3. History
    resp = requests.get(f"{BASE_URL}/health/mental-assessment/history")
    print(f"GET History: {resp.status_code}")
    
    # 4. Burnout
    resp = requests.get(f"{BASE_URL}/health/burnout-prediction")
    print(f"GET Burnout: {resp.status_code}")

def test_care_team():
    print("\n--- Testing Care Team ---")
    # 1. List
    resp = requests.get(f"{BASE_URL}/care-team")
    print(f"GET Team: {resp.status_code}")
    if resp.status_code == 200:
        members = resp.json()["members"]
        print(f"Found {len(members)} members")
        if members:
            mid = members[0].get("id")
            # 2. Review
            if mid:
                resp = requests.post(f"{BASE_URL}/care-team/submit-review", json={
                    "member_id": mid, "rating": 5, "review_text": "Excellent coach!"
                })
                print(f"POST Review: {resp.status_code}")

def test_credits():
    print("\n--- Testing Credits ---")
    resp = requests.get(f"{BASE_URL}/credits/balance")
    print(f"GET Balance: {resp.status_code}")
    
    resp = requests.post(f"{BASE_URL}/credits/purchase", json={"amount": 50})
    print(f"POST Purchase: {resp.status_code}")

if __name__ == "__main__":
    # Note: These tests require the server to be running and authentication to be handled.
    # Since I cannot easily run a background server and keep it alive for requests here,
    # I will stick to unit-test style verification or manual check of the code.
    print("Verification script created. Ensure server is running and update headers with token.")
