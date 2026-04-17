import requests

BASE_URL = "http://localhost:8000/api"

def verify_parity():
    print("Verifying CC Protocols API Parity...")
    
    # We need a token. Normally we'd log in, but I'll assume standard credentials 
    # or just use the DB directly if I want to be quick.
    # However, testing the actual API response is better.
    
    # I'll use a Django shell script to verify the response structure instead of a real HTTP request 
    # to avoid auth complexity in this environment.
    pass

if __name__ == "__main__":
    # verification logic inside manage.py shell
    import subprocess
    cmd = """
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth.models import User
from Reboot_App.views_cc import get_cc_protocols
import json

factory = APIRequestFactory()
user = User.objects.get(email='clinical_admin@agereboot.com')
request = factory.get('/api/cc/protocols')
force_authenticate(request, user=user)

response = get_cc_protocols(request)
data = response.data

print(f"Top-level keys: {list(data.keys())}")
assert 'categories' in data
assert 'hallmarks' in data
assert 'protocols' in data
assert 'total' in data
print(f"Total protocols returned: {data['total']}")

p = data['protocols'][2] # Checking RTL (LGP-003)
print(f"Checking {p['lgp_id']} - {p['name']} fields:")
expected_fields = [
    'lgp_id', 'name', 'category', 'description', 'duration_default_weeks',
    'evidence_grade', 'hallmarks_of_ageing', 'hps_dimensions', 'impact_scores',
    'interventions', 'smart_goals_template', 'codes', 'id', 'created_at'
]
for field in expected_fields:
    assert field in p, f"Missing field: {field}"
    print(f"  ✓ {field}")

print("\n✓ API Parity Verified Successfully!")
"""
    with open("verify_parity_script.py", "w") as f:
        f.write(cmd)
    
    subprocess.run([".venv/Scripts/python.exe", "manage.py", "shell", "<", "verify_parity_script.py"], shell=True)
