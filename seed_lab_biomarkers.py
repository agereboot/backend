import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from Reboot_App.models import BiomarkerDefinition

BIOMARKER_DATA = {
    "fasting_glucose": {"name": "Fasting Glucose", "unit": "mg/dL", "optimal_low": 70, "optimal_high": 99, "longevity_low": 72, "longevity_high": 88, "pillar": "MH", "domain": "Glycemic Control"},
    "hba1c": {"name": "HbA1c", "unit": "%", "optimal_low": 4.0, "optimal_high": 5.6, "longevity_low": 4.5, "longevity_high": 5.2, "pillar": "MH", "domain": "Glycemic Control"},
    "total_cholesterol": {"name": "Total Cholesterol", "unit": "mg/dL", "optimal_low": 125, "optimal_high": 200, "longevity_low": 150, "longevity_high": 190, "pillar": "CV", "domain": "Lipid Panel"},
    "ldl_cholesterol": {"name": "LDL Cholesterol", "unit": "mg/dL", "optimal_low": 0, "optimal_high": 100, "longevity_low": 50, "longevity_high": 80, "pillar": "CV", "domain": "Lipid Panel"},
    "hdl_cholesterol": {"name": "HDL Cholesterol", "unit": "mg/dL", "optimal_low": 40, "optimal_high": 100, "longevity_low": 55, "longevity_high": 90, "pillar": "CV", "domain": "Lipid Panel"},
    "triglycerides": {"name": "Triglycerides", "unit": "mg/dL", "optimal_low": 0, "optimal_high": 150, "longevity_low": 40, "longevity_high": 100, "pillar": "CV", "domain": "Lipid Panel"},
    "tsh": {"name": "TSH", "unit": "mIU/L", "optimal_low": 0.4, "optimal_high": 4.0, "longevity_low": 1.0, "longevity_high": 2.5, "pillar": "MH", "domain": "Thyroid"},
    "vitamin_d": {"name": "Vitamin D", "unit": "ng/mL", "optimal_low": 30, "optimal_high": 100, "longevity_low": 50, "longevity_high": 80, "pillar": "NU", "domain": "Nutrition"},
    "vitamin_b12": {"name": "Vitamin B12", "unit": "pg/mL", "optimal_low": 200, "optimal_high": 900, "longevity_low": 500, "longevity_high": 800, "pillar": "NU", "domain": "Nutrition"},
    "hscrp": {"name": "hsCRP", "unit": "mg/L", "optimal_low": 0, "optimal_high": 3.0, "longevity_low": 0, "longevity_high": 0.5, "pillar": "CV", "domain": "Inflammation"},
    "ferritin": {"name": "Ferritin", "unit": "ng/mL", "optimal_low": 12, "optimal_high": 300, "longevity_low": 40, "longevity_high": 150, "pillar": "MH", "domain": "Iron"},
    "homocysteine": {"name": "Homocysteine", "unit": "umol/L", "optimal_low": 5, "optimal_high": 15, "longevity_low": 6, "longevity_high": 9, "pillar": "CV", "domain": "Metabolic"},
    "cortisol": {"name": "Cortisol (Morning)", "unit": "ug/dL", "optimal_low": 6, "optimal_high": 23, "longevity_low": 10, "longevity_high": 18, "pillar": "CA", "domain": "Hormones"},
    "creatinine": {"name": "Creatinine", "unit": "mg/dL", "optimal_low": 0.6, "optimal_high": 1.2, "longevity_low": 0.7, "longevity_high": 1.0, "pillar": "MH", "domain": "Kidney"},
}

for code, data in BIOMARKER_DATA.items():
    BiomarkerDefinition.objects.update_or_create(
        code=code,
        defaults={
            "name": data["name"],
            "unit": data["unit"],
            "optimal_low": data["optimal_low"],
            "optimal_high": data["optimal_high"],
            "longevity_low": data["longevity_low"],
            "longevity_high": data["longevity_high"],
            "pillar": data["pillar"],
            "domain": data["domain"],
            "data_source": "lab"
        }
    )

print("Biomarkers seeded successfully.")
