import os
import django
import uuid
import random
from datetime import datetime, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from django.contrib.auth.models import User
from Reboot_App.models import LabPartner, LabPanel, LabOrder

LAB_PANELS = [
    {"panel_id": "LP-COMP-MET", "name": "Comprehensive Metabolic Panel", "category": "Metabolic", "biomarkers": ["glucose", "bun", "creatinine", "sodium", "potassium", "calcium", "co2", "chloride", "albumin", "total_protein", "alt", "ast", "bilirubin"], "price": 45.00, "turnaround_days": 1},
    {"panel_id": "LP-LIPID", "name": "Advanced Lipid Panel", "category": "Cardiovascular", "biomarkers": ["total_cholesterol", "ldl_cholesterol", "hdl_cholesterol", "triglycerides", "apoB", "lp_a", "sdLDL"], "price": 85.00, "turnaround_days": 2},
    {"panel_id": "LP-THYROID", "name": "Complete Thyroid Panel", "category": "Endocrine", "biomarkers": ["tsh", "free_t4", "free_t3", "reverse_t3", "thyroid_antibodies"], "price": 120.00, "turnaround_days": 2},
    {"panel_id": "LP-HORMONE-M", "name": "Male Hormone Panel", "category": "Hormonal", "biomarkers": ["total_testosterone", "free_testosterone", "estradiol", "dhea_s", "shbg", "lh", "fsh", "prolactin"], "price": 250.00, "turnaround_days": 3},
    {"panel_id": "LP-INFLAM", "name": "Inflammation Panel", "category": "Immune", "biomarkers": ["hscrp", "esr", "ferritin", "il6", "tnf_alpha", "fibrinogen"], "price": 180.00, "turnaround_days": 3},
    {"panel_id": "LP-CBC", "name": "Complete Blood Count + Diff", "category": "Hematology", "biomarkers": ["wbc", "rbc", "hemoglobin", "hematocrit", "platelets", "mcv", "mch", "mchc", "rdw", "mpv"], "price": 25.00, "turnaround_days": 1},
    {"panel_id": "LP-HBA1C", "name": "HbA1c + Fasting Insulin", "category": "Metabolic", "biomarkers": ["hba1c", "fasting_insulin", "fasting_glucose"], "price": 55.00, "turnaround_days": 1},
    {"panel_id": "LP-VIT", "name": "Vitamin & Mineral Panel", "category": "Nutritional", "biomarkers": ["vitamin_d", "vitamin_b12", "folate", "iron", "zinc", "magnesium_rbc", "omega3_index"], "price": 160.00, "turnaround_days": 3},
    {"panel_id": "LP-LIVER", "name": "Hepatic Function Panel", "category": "Hepatic", "biomarkers": ["alt", "ast", "ggt", "alkaline_phosphatase", "bilirubin", "albumin"], "price": 40.00, "turnaround_days": 1},
    {"panel_id": "LP-AGING", "name": "AgeReboot Longevity Panel", "category": "Longevity", "biomarkers": ["telomere_length", "dna_methylation_age", "nad_level", "glutathione", "coq10", "igf1"], "price": 450.00, "turnaround_days": 7},
]

LAB_PARTNERS = [
    {"id": "LP-THY", "name": "Thyrocare", "type": "reference_lab", "tat_modifier": 0, "accreditation": "NABL"},
    {"id": "LP-SRL", "name": "SRL Diagnostics", "type": "reference_lab", "tat_modifier": 0, "accreditation": "CAP"},
    {"id": "LP-MET", "name": "Metropolis Healthcare", "type": "reference_lab", "tat_modifier": 1, "accreditation": "NABL"},
    {"id": "LP-DRL", "name": "Dr. Lal PathLabs", "type": "reference_lab", "tat_modifier": 0, "accreditation": "NABL"},
    {"id": "LP-ING", "name": "In-House AgeReboot Lab", "type": "in_house", "tat_modifier": -1, "accreditation": "ISO 15189"},
]

def seed():
    print("Starting lab data seeding...")
    
    # 1. Lab Partners
    for lp in LAB_PARTNERS:
        partner, created = LabPartner.objects.get_or_create(
            id=lp["id"],
            defaults={
                "name": lp["name"],
                "type": lp["type"],
                "tat_modifier": lp["tat_modifier"],
                "accreditation": lp["accreditation"]
            }
        )
        if created:
            print(f"Created LabPartner: {lp['name']}")
            
    # 2. Lab Panels
    for p in LAB_PANELS:
        panel, created = LabPanel.objects.get_or_create(
            panel_id=p["panel_id"],
            defaults={
                "name": p["name"],
                "category": p["category"],
                "tests_included": p["biomarkers"],
                "price": p["price"],
                "turnaround_time": f"{p['turnaround_days']} day(s)"
            }
        )
        if created:
            print(f"Created LabPanel: {p['name']}")

    # 3. Lab Orders for member_04 and member_05
    clinician = User.objects.filter(email='clinical_admin@agereboot.com').first()
    if not clinician:
        print("Error: clinical_admin@agereboot.com not found. Skipping orders.")
        return

    targets = User.objects.filter(username__in=['member_04', 'member_05'])
    if not targets.exists():
        print("Error: member_04 or member_05 not found. Skipping orders.")
        return

    panels = list(LabPanel.objects.all())
    partners = list(LabPartner.objects.all())

    for member in targets:
        # Create a few orders for each member
        for i in range(2):
            panel = random.choice(panels)
            partner = random.choice(partners)
            status = random.choice(["ordered", "collected", "processing", "resulted"])
            days_ago = random.randint(1, 30)
            ordered_at = timezone.now() - timedelta(days=days_ago)
            
            order_num = f"LO-{ordered_at.strftime('%Y%m%d')}-{random.randint(100000, 999999)}"
            
            order = LabOrder.objects.create(
                id=uuid.uuid4(),
                order_number=order_num,
                patient=member,
                ordered_by=clinician,
                panel=panel,
                lab_partner=partner,
                priority=random.choice(["routine", "urgent"]),
                status=status,
                price=panel.price,
                turnaround_days=int(panel.turnaround_time.split()[0]) + partner.tat_modifier,
                ordered_at=ordered_at
            )
            
            if status == "resulted":
                order.resulted_at = ordered_at + timedelta(days=order.turnaround_days)
                # Add some fake results
                results = []
                for test in panel.tests_included[:3]:
                    val = random.uniform(50, 150)
                    results.append({
                        "test_name": test,
                        "value": round(val, 2),
                        "unit": "mg/dL",
                        "reference_low": 70,
                        "reference_high": 120,
                        "flag": "high" if val > 120 else ("low" if val < 70 else "normal")
                    })
                order.results = results
                order.abnormal_count = sum(1 for r in results if r["flag"] != "normal")
                order.save()
            
            print(f"Created LabOrder {order_num} for {member.username} (Status: {status})")

    print("Lab data seeding complete.")

if __name__ == "__main__":
    seed()
