import os
import django
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from rest_framework.test import force_authenticate
from Reboot_App.views_lab_ingestion import upload_lab_report, get_patient_reports, get_report_detail, approve_report_values

def test_lab_ingestion_flow():
    # Make sure we have a user
    user = User.objects.get(id=1)
    factory = RequestFactory()
    
    print("Testing upload_lab_report...")
    request = factory.post('/lab-ingestion/upload-report', data=json.dumps({'lab_partner': 'TestLab'}), content_type='application/json')
    force_authenticate(request, user=user)
    response = upload_lab_report(request)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        report_id = response.data['report']['id']
        print(f"Report ID: {report_id}")
        
        print("\nTesting get_patient_reports...")
        request = factory.get(f'/lab-ingestion/reports/{user.id}')
        force_authenticate(request, user=user)
        response = get_patient_reports(request, patient_id=user.id)
        print(f"Status: {response.status_code}")
        print(f"Reports found: {len(response.data['reports'])}")
        
        print("\nTesting get_report_detail...")
        request = factory.get(f'/lab-ingestion/report/{report_id}')
        force_authenticate(request, user=user)
        response = get_report_detail(request, report_id=report_id)
        print(f"Status: {response.status_code}")
        print(f"Visual cards: {len(response.data['visual_cards'])}")
        
        print("\nTesting approve_report_values...")
        request = factory.post(f'/lab-ingestion/report/{report_id}/approve', data=json.dumps({'corrected_values': []}), content_type='application/json')
        force_authenticate(request, user=user)
        response = approve_report_values(request, report_id=report_id)
        print(f"Status: {response.status_code}")
        print(f"Ingested: {response.data['ingested']}")
    else:
        print(f"Error: {response.data}")

if __name__ == "__main__":
    test_lab_ingestion_flow()
