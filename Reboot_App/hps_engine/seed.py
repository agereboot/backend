"""
HPS Engine v3.0 — Seed Data Generator
50 anonymized datasets based on population health distributions.
Sources: NHANES 2017-2020, UK Biobank, WHO Global Health Observatory.
"""
import random
import uuid
from datetime import datetime, timezone, timedelta

FRANCHISE_NAMES = [
    "Tata Group", "Infosys", "Wipro", "Reliance", "Mahindra",
    "Adani Group", "Bajaj", "HCL Tech", "Tech Mahindra", "HDFC Bank",
    "ICICI", "Larsen & Toubro", "Bharti Airtel", "ITC Limited", "Godrej",
    "Asian Paints", "Hindustan Unilever", "Nestle India", "Kotak Mahindra", "Sun Pharma"
]

FIRST_NAMES_M = ["Aarav", "Vihaan", "Aditya", "Sai", "Arjun", "Reyansh", "Ayaan", "Krishna", "Ishaan", "Shaurya",
                  "Atharv", "Vivaan", "Ansh", "Dhruv", "Kabir", "Ritvik", "Aarush", "Kian", "Darsh", "Arnav",
                  "Rudra", "Laksh", "Pranav", "Advait", "Veer"]
FIRST_NAMES_F = ["Saanvi", "Aanya", "Aadhya", "Aarohi", "Ananya", "Pari", "Anika", "Navya", "Myra", "Sara",
                  "Diya", "Kiara", "Prisha", "Riya", "Isha", "Aditi", "Kavya", "Mahi", "Nisha", "Tara",
                  "Meera", "Shreya", "Pooja", "Neha", "Sneha"]


def _rand_normal(mean, sd, low=None, high=None):
    v = random.gauss(mean, sd)
    if low is not None:
        v = max(low, v)
    if high is not None:
        v = min(high, v)
    return round(v, 1)


def generate_biomarker_set(age, sex):
    """Generate realistic biomarker values based on age/sex distributions"""
    s = sex
    age_factor = (age - 30) / 40  # 0 at 30, 1 at 70

    data = {
        "hrv_rmssd": _rand_normal(45 - age_factor * 25, 12, 5, 120),
        "resting_hr": _rand_normal(65 + age_factor * 10, 8, 40, 110),
        "hscrp": _rand_normal(1.0 + age_factor * 2, 1.2, 0.1, 15),
        "homa_ir": _rand_normal(1.5 + age_factor * 1.5, 0.8, 0.3, 8),
        "fasting_glucose": _rand_normal(85 + age_factor * 20, 10, 60, 200),
        "hba1c": _rand_normal(5.2 + age_factor * 0.6, 0.4, 4.0, 10),
        "ldl_c": _rand_normal(100 + age_factor * 40, 25, 40, 250),
        "hdl_c": _rand_normal(55 - age_factor * 8 + (10 if s == "F" else 0), 12, 25, 100),
        "triglycerides": _rand_normal(100 + age_factor * 60, 40, 40, 400),
        "vitamin_d": _rand_normal(30 - age_factor * 10, 12, 5, 80),
        "vo2_max": _rand_normal(42 - age_factor * 15 - (8 if s == "F" else 0), 7, 12, 65),
        "grip_strength": _rand_normal(42 - age_factor * 12 - (18 if s == "F" else 0), 6, 10, 70),
        "body_fat_pct": _rand_normal(20 + age_factor * 8 + (7 if s == "F" else 0), 5, 5, 50),
        "mobility_score": _rand_normal(75 - age_factor * 20, 12, 20, 100),
        "memory_processing": _rand_normal(78 - age_factor * 15, 10, 30, 100),
        "reaction_time": _rand_normal(260 + age_factor * 60, 30, 150, 500),
        "stress_pss": _rand_normal(14, 6, 0, 40),
        "sleep_duration": _rand_normal(7.2 - age_factor * 0.8, 0.8, 4, 10),
        "deep_sleep_pct": _rand_normal(18 - age_factor * 8, 4, 3, 35),
        "sleep_efficiency": _rand_normal(87 - age_factor * 8, 5, 60, 99),
        "recovery_score": _rand_normal(70 - age_factor * 15, 12, 20, 100),
        "diet_quality": _rand_normal(58, 15, 10, 100),
        "activity_consistency": _rand_normal(55, 18, 5, 100),
        "smoking_score": random.choice([100, 100, 100, 100, 80, 60, 40, 20]),
        "alcohol_score": _rand_normal(72, 15, 10, 100),
    }

    # Randomly remove some metrics (simulate incomplete panels)
    n_remove = random.randint(0, 6)
    keys_to_remove = random.sample(list(data.keys()), min(n_remove, len(data)))
    for k in keys_to_remove:
        del data[k]

    return data


def generate_seed_users(n=50):
    """Generate n anonymized user profiles with biomarker data"""
    users = []
    for i in range(n):
        sex = random.choice(["M", "F"])
        age = random.randint(22, 68)
        names = FIRST_NAMES_M if sex == "M" else FIRST_NAMES_F
        name = random.choice(names)
        franchise = random.choice(FRANCHISE_NAMES)

        user = {
            "id": str(uuid.uuid4()),
            "name": f"{name} {chr(65 + random.randint(0, 25))}.",
            "email": f"user{i+1}@agereboot.demo",
            "password_hash": "$2b$12$LJ3CJ0T.M.UxMhFqVg2Zfu7UJZ8L5M0CzJb6FbRxT5E8YvRvSFCHe",
            "age": age,
            "sex": sex,
            "height_cm": _rand_normal(170 if sex == "M" else 158, 8, 140, 200),
            "weight_kg": _rand_normal(75 if sex == "M" else 62, 12, 40, 140),
            "ethnicity": random.choice(["SOUTH_ASIAN", "SOUTH_ASIAN", "SOUTH_ASIAN", "EAST_ASIAN", "ALL"]),
            "franchise": franchise,
            "role": "athlete",
            "managed_conditions": random.choice([[], [], [], [], ["T2DM"], ["Hypertension"], ["Hypothyroid"]]),
            "adherence_pct": _rand_normal(72, 15, 20, 100),
            "joined_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365))).isoformat(),
            "is_demo": True,
        }

        user["biomarkers"] = generate_biomarker_set(age, sex)
        users.append(user)

    return users
