from django.core.management.base import BaseCommand
from django.utils import timezone
from Reboot_App.models import LabPartner, LabPanel, PharmacyCatalogItem

class Command(BaseCommand):
    help = 'Seed Clinical and Pharmacy data from Flask legacy'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Clinical Data...")

        # 1. Lab Partners
        partners = [
            {"id": "LP-THY", "name": "Thyrocare", "type": "reference_lab", "tat_modifier": 0, "accreditation": "NABL"},
            {"id": "LP-SRL", "name": "SRL Diagnostics", "type": "reference_lab", "tat_modifier": 0, "accreditation": "CAP"},
            {"id": "LP-MET", "name": "Metropolis Healthcare", "type": "reference_lab", "tat_modifier": 1, "accreditation": "NABL"},
            {"id": "LP-DRL", "name": "Dr. Lal PathLabs", "type": "reference_lab", "tat_modifier": 0, "accreditation": "NABL"},
            {"id": "LP-ING", "name": "In-House AgeReboot Lab", "type": "in_house", "tat_modifier": -1, "accreditation": "ISO 15189"},
        ]
        for p in partners:
            LabPartner.objects.update_or_create(id=p["id"], defaults=p)
        self.stdout.write(f"  - Seeded {len(partners)} Lab Partners")

        # 2. Lab Panels
        panels = [
            {"panel_id": "LP-COMP-MET", "name": "Comprehensive Metabolic Panel", "category": "Metabolic", "biomarkers": ["glucose", "bun", "creatinine", "sodium", "potassium", "calcium", "co2", "chloride", "albumin", "total_protein", "alt", "ast", "bilirubin"], "loinc": "24323-8", "price": 45.00, "turnaround_days": 1},
            {"panel_id": "LP-LIPID", "name": "Advanced Lipid Panel", "category": "Cardiovascular", "biomarkers": ["total_cholesterol", "ldl_cholesterol", "hdl_cholesterol", "triglycerides", "apoB", "lp_a", "sdLDL"], "loinc": "57698-3", "price": 85.00, "turnaround_days": 2},
            {"panel_id": "LP-THYROID", "name": "Complete Thyroid Panel", "category": "Endocrine", "biomarkers": ["tsh", "free_t4", "free_t3", "reverse_t3", "thyroid_antibodies"], "loinc": "94661-6", "price": 120.00, "turnaround_days": 2},
            {"panel_id": "LP-HORMONE-M", "name": "Male Hormone Panel", "category": "Hormonal", "biomarkers": ["total_testosterone", "free_testosterone", "estradiol", "dhea_s", "shbg", "lh", "fsh", "prolactin"], "loinc": "Custom-HM", "price": 250.00, "turnaround_days": 3},
            {"panel_id": "LP-INFLAM", "name": "Inflammation Panel", "category": "Immune", "biomarkers": ["hscrp", "esr", "ferritin", "il6", "tnf_alpha", "fibrinogen"], "loinc": "Custom-INF", "price": 180.00, "turnaround_days": 3},
            {"panel_id": "LP-CBC", "name": "Complete Blood Count + Diff", "category": "Hematology", "biomarkers": ["wbc", "rbc", "hemoglobin", "hematocrit", "platelets", "mcv", "mch", "mchc", "rdw", "mpv"], "loinc": "57021-8", "price": 25.00, "turnaround_days": 1},
            {"panel_id": "LP-HBA1C", "name": "HbA1c + Fasting Insulin", "category": "Metabolic", "biomarkers": ["hba1c", "fasting_insulin", "fasting_glucose"], "loinc": "4548-4", "price": 55.00, "turnaround_days": 1},
            {"panel_id": "LP-VIT", "name": "Vitamin & Mineral Panel", "category": "Nutritional", "biomarkers": ["vitamin_d", "vitamin_b12", "folate", "iron", "zinc", "magnesium_rbc", "omega3_index"], "loinc": "Custom-VIT", "price": 160.00, "turnaround_days": 3},
            {"panel_id": "LP-LIVER", "name": "Hepatic Function Panel", "category": "Hepatic", "biomarkers": ["alt", "ast", "ggt", "alkaline_phosphatase", "bilirubin", "albumin"], "loinc": "24325-3", "price": 40.00, "turnaround_days": 1},
            {"panel_id": "LP-AGING", "name": "AgeReboot Longevity Panel", "category": "Longevity", "biomarkers": ["telomere_length", "dna_methylation_age", "nad_level", "glutathione", "coq10", "igf1"], "loinc": "Custom-AGE", "price": 450.00, "turnaround_days": 7},
        ]
        for p in panels:
            LabPanel.objects.update_or_create(panel_id=p["panel_id"], defaults=p)
        self.stdout.write(f"  - Seeded {len(panels)} Lab Panels")

        # 3. Pharmacy Catalog
        catalog = [
            {"item_id": "RX-001", "name": "Metformin 500mg", "type": "prescription", "category": "Metabolic", "requires_rx": True, "price": 12.00},
            {"item_id": "RX-002", "name": "Testosterone Cypionate 200mg/mL", "type": "prescription", "category": "Hormonal", "requires_rx": True, "price": 85.00},
            {"item_id": "RX-003", "name": "Levothyroxine 50mcg", "type": "prescription", "category": "Thyroid", "requires_rx": True, "price": 15.00},
            {"item_id": "RX-004", "name": "Low-Dose Naltrexone 4.5mg", "type": "prescription", "category": "Immune", "requires_rx": True, "price": 45.00},
            {"item_id": "RX-005", "name": "Rapamycin 1mg (Sirolimus)", "type": "prescription", "category": "Longevity", "requires_rx": True, "price": 120.00},
            {"item_id": "NT-001", "name": "NMN 500mg (Nicotinamide Mononucleotide)", "type": "nutraceutical", "category": "NAD+ Support", "requires_rx": False, "price": 65.00},
            {"item_id": "NT-002", "name": "Omega-3 Fish Oil (EPA 1000mg + DHA 500mg)", "type": "nutraceutical", "category": "Cardiovascular", "requires_rx": False, "price": 35.00},
            {"item_id": "NT-003", "name": "Vitamin D3 5000 IU + K2 MK-7 200mcg", "type": "nutraceutical", "category": "Bone & Immune", "requires_rx": False, "price": 22.00},
            {"item_id": "NT-004", "name": "Magnesium Glycinate 400mg", "type": "nutraceutical", "category": "Sleep & Recovery", "requires_rx": False, "price": 18.00},
            {"item_id": "NT-005", "name": "CoQ10 (Ubiquinol) 200mg", "type": "nutraceutical", "category": "Mitochondrial", "requires_rx": False, "price": 42.00},
            {"item_id": "NT-006", "name": "Resveratrol 500mg + Quercetin 500mg", "type": "nutraceutical", "category": "Senolytic", "requires_rx": False, "price": 55.00},
            {"item_id": "NT-007", "name": "Creatine Monohydrate 5g", "type": "nutraceutical", "category": "Muscle & Brain", "requires_rx": False, "price": 15.00},
            {"item_id": "NT-008", "name": "Ashwagandha KSM-66 600mg", "type": "nutraceutical", "category": "Adaptogen", "requires_rx": False, "price": 25.00},
            {"item_id": "NT-009", "name": "Spermidine 1mg", "type": "nutraceutical", "category": "Autophagy", "requires_rx": False, "price": 48.00},
            {"item_id": "NT-010", "name": "Alpha-Ketoglutarate (AKG) 1000mg", "type": "nutraceutical", "category": "Longevity", "requires_rx": False, "price": 38.00},
            {"item_id": "NT-011", "name": "Berberine 500mg", "type": "nutraceutical", "category": "Metabolic", "requires_rx": False, "price": 28.00},
            {"item_id": "NT-012", "name": "Probiotic Multi-Strain 50B CFU", "type": "nutraceutical", "category": "Gut Health", "requires_rx": False, "price": 32.00},
        ]
        for i in catalog:
            PharmacyCatalogItem.objects.update_or_create(item_id=i["item_id"], defaults=i)
        self.stdout.write(f"  - Seeded {len(catalog)} Pharmacy Catalog Items")

        self.stdout.write(self.style.SUCCESS("Clinical Seeding Complete!"))
