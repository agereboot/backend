"""
HPS Engine v3.0 — Normative Reference Data
Age-sex-adjusted population means and standard deviations.
Sources: NHANES, UK Biobank, ICMR, WHO, ADA, ACC/AHA
"""

BIOMARKER_DEFINITIONS = {
    "hrv_rmssd": {
        "name": "HRV (RMSSD)", "domain": "Autonomic", "pillar": "BR",
        "unit": "ms", "direction": "higher_better",
        "optimal_low": 30, "optimal_high": 80,
        "weight": 1.2,
        "data_source": "wearable"
    },
    "resting_hr": {
        "name": "Resting Heart Rate", "domain": "Cardiovascular", "pillar": "BR",
        "unit": "bpm", "direction": "lower_better",
        "optimal_low": 50, "optimal_high": 65,
        "weight": 1.0,
        "data_source": "wearable"
    },
    "hscrp": {
        "name": "hsCRP", "domain": "Inflammation", "pillar": "BR",
        "unit": "mg/L", "direction": "lower_better",
        "optimal_low": 0.1, "optimal_high": 0.5,
        "weight": 1.3,
        "data_source": "lab_report"
    },
    "homa_ir": {
        "name": "HOMA-IR", "domain": "Metabolic", "pillar": "BR",
        "unit": "ratio", "direction": "lower_better",
        "optimal_low": 0.5, "optimal_high": 1.0,
        "weight": 1.4,
        "data_source": "lab_report"
    },
    "fasting_glucose": {
        "name": "Fasting Glucose", "domain": "Metabolic", "pillar": "BR",
        "unit": "mg/dL", "direction": "optimal_range",
        "optimal_low": 70, "optimal_high": 85,
        "weight": 1.1,
        "data_source": "lab_report"
    },
    "hba1c": {
        "name": "HbA1c", "domain": "Metabolic", "pillar": "BR",
        "unit": "%", "direction": "lower_better",
        "optimal_low": 4.5, "optimal_high": 5.4,
        "weight": 1.3,
        "data_source": "lab_report"
    },
    "ldl_c": {
        "name": "LDL-C", "domain": "Lipid", "pillar": "BR",
        "unit": "mg/dL", "direction": "lower_better",
        "optimal_low": 50, "optimal_high": 100,
        "weight": 1.0,
        "data_source": "lab_report"
    },
    "hdl_c": {
        "name": "HDL-C", "domain": "Lipid", "pillar": "BR",
        "unit": "mg/dL", "direction": "higher_better",
        "optimal_low": 60, "optimal_high": 100,
        "weight": 0.9,
        "data_source": "lab_report"
    },
    "triglycerides": {
        "name": "Triglycerides", "domain": "Lipid", "pillar": "BR",
        "unit": "mg/dL", "direction": "lower_better",
        "optimal_low": 50, "optimal_high": 100,
        "weight": 0.8,
        "data_source": "lab_report"
    },
    "vitamin_d": {
        "name": "Vitamin D (25-OH)", "domain": "Micronutrient", "pillar": "BR",
        "unit": "ng/mL", "direction": "optimal_range",
        "optimal_low": 40, "optimal_high": 60,
        "weight": 0.7,
        "data_source": "lab_report"
    },
    "vo2_max": {
        "name": "VO2 Max", "domain": "Cardiorespiratory", "pillar": "PF",
        "unit": "mL/kg/min", "direction": "higher_better",
        "optimal_low": 35, "optimal_high": 55,
        "weight": 1.25,
        "data_source": "doctor_assessment"
    },
    "grip_strength": {
        "name": "Grip Strength", "domain": "Functional", "pillar": "PF",
        "unit": "kg", "direction": "higher_better",
        "optimal_low": 30, "optimal_high": 55,
        "weight": 0.90,
        "data_source": "doctor_assessment"
    },
    "body_fat_pct": {
        "name": "Body Fat %", "domain": "Anthropometric", "pillar": "PF",
        "unit": "%", "direction": "lower_better",
        "optimal_low": 10, "optimal_high": 20,
        "weight": 0.60,
        "data_source": "doctor_assessment"
    },
    "mobility_score": {
        "name": "Mobility Score", "domain": "Functional", "pillar": "PF",
        "unit": "score", "direction": "higher_better",
        "optimal_low": 60, "optimal_high": 100,
        "weight": 0.35,
        "data_source": "doctor_assessment"
    },
    "memory_processing": {
        "name": "Memory & Processing", "domain": "Cognitive", "pillar": "CA",
        "unit": "score", "direction": "higher_better",
        "optimal_low": 70, "optimal_high": 100,
        "weight": 0.50,
        "data_source": "doctor_assessment"
    },
    "reaction_time": {
        "name": "Reaction Time", "domain": "Cognitive", "pillar": "CA",
        "unit": "ms", "direction": "lower_better",
        "optimal_low": 200, "optimal_high": 300,
        "weight": 0.65,
        "data_source": "doctor_assessment"
    },
    "stress_pss": {
        "name": "Perceived Stress (PSS)", "domain": "HPA Axis", "pillar": "CA",
        "unit": "score", "direction": "lower_better",
        "optimal_low": 0, "optimal_high": 13,
        "weight": 0.85,
        "data_source": "doctor_assessment"
    },
    "cortisol_am": {
        "name": "Cortisol (AM)", "domain": "HPA Axis", "pillar": "CA",
        "unit": "ug/dL", "direction": "optimal_range",
        "optimal_low": 10, "optimal_high": 18,
        "weight": 0.45,
        "data_source": "lab_report",
        "conditional": True
    },
    "sleep_duration": {
        "name": "Sleep Duration", "domain": "Sleep", "pillar": "SR",
        "unit": "hours", "direction": "optimal_range",
        "optimal_low": 7.0, "optimal_high": 9.0,
        "weight": 1.2,
        "data_source": "wearable"
    },
    "deep_sleep_pct": {
        "name": "Deep Sleep %", "domain": "Sleep", "pillar": "SR",
        "unit": "%", "direction": "higher_better",
        "optimal_low": 15, "optimal_high": 25,
        "weight": 1.1,
        "data_source": "wearable"
    },
    "sleep_efficiency": {
        "name": "Sleep Efficiency", "domain": "Sleep", "pillar": "SR",
        "unit": "%", "direction": "higher_better",
        "optimal_low": 85, "optimal_high": 95,
        "weight": 1.0,
        "data_source": "wearable"
    },
    "recovery_score": {
        "name": "Recovery Score", "domain": "Recovery", "pillar": "SR",
        "unit": "score", "direction": "higher_better",
        "optimal_low": 60, "optimal_high": 100,
        "weight": 0.9,
        "data_source": "wearable"
    },
    "diet_quality": {
        "name": "Diet Quality Score", "domain": "Nutrition", "pillar": "BL",
        "unit": "score", "direction": "higher_better",
        "optimal_low": 70, "optimal_high": 100,
        "weight": 1.2,
        "data_source": "self_assessment"
    },
    "activity_consistency": {
        "name": "Activity Consistency", "domain": "Exercise", "pillar": "BL",
        "unit": "%", "direction": "higher_better",
        "optimal_low": 70, "optimal_high": 100,
        "weight": 1.1,
        "data_source": "wearable"
    },
    "smoking_score": {
        "name": "Smoking Status", "domain": "Behaviour", "pillar": "BL",
        "unit": "score", "direction": "higher_better",
        "optimal_low": 80, "optimal_high": 100,
        "weight": 1.3,
        "data_source": "emr"
    },
    "alcohol_score": {
        "name": "Alcohol Consumption", "domain": "Behaviour", "pillar": "BL",
        "unit": "score", "direction": "higher_better",
        "optimal_low": 70, "optimal_high": 100,
        "weight": 0.9,
        "data_source": "emr"
    },
    "daily_steps": {
        "name": "Daily Steps", "domain": "Physical Activity", "pillar": "PF",
        "unit": "steps/day", "direction": "higher_better",
        "optimal_low": 8000, "optimal_high": 10000,
        "weight": 0.65,
        "data_source": "wearable"
    },
    "active_energy_kcal": {
        "name": "Active Energy", "domain": "Physical Activity", "pillar": "PF",
        "unit": "kcal/day", "direction": "higher_better",
        "optimal_low": 500, "optimal_high": 800,
        "weight": 0.60,
        "data_source": "wearable"
    },
    "sedentary_time_hrs": {
        "name": "Sedentary Time", "domain": "Physical Activity", "pillar": "PF",
        "unit": "hrs/day", "direction": "lower_better",
        "optimal_low": 4, "optimal_high": 6,
        "weight": 0.40,
        "data_source": "wearable"
    },
    "phq9_score": {
        "name": "PHQ-9 Depression Screen", "domain": "Mental Health", "pillar": "CA",
        "unit": "score", "direction": "lower_better",
        "optimal_low": 0, "optimal_high": 4,
        "weight": 1.10,
        "data_source": "questionnaire"
    },
    "gad7_score": {
        "name": "GAD-7 Anxiety Screen", "domain": "Mental Health", "pillar": "CA",
        "unit": "score", "direction": "lower_better",
        "optimal_low": 0, "optimal_high": 4,
        "weight": 0.90,
        "data_source": "questionnaire"
    },
    "moca_score": {
        "name": "MoCA Cognitive Assessment", "domain": "Cognitive", "pillar": "CA",
        "unit": "score", "direction": "higher_better",
        "optimal_low": 26, "optimal_high": 30,
        "weight": 1.00,
        "data_source": "questionnaire"
    },
}

PILLAR_CONFIG = {
    "BR": {"name": "Biological Resilience", "max_points": 280, "color": "#7B35D8"},
    "PF": {"name": "Physical Fitness", "max_points": 250, "color": "#4F46E5"},
    "CA": {"name": "Cognitive Health", "max_points": 150, "color": "#0F9F8F"},
    "SR": {"name": "Sleep & Recovery", "max_points": 160, "color": "#D97706"},
    "BL": {"name": "Behaviour & Lifestyle", "max_points": 160, "color": "#EF4444"},
}

# Age-sex normative means and SDs (from NHANES / UK Biobank / ICMR)
NORMATIVE_DATA = {
    "hrv_rmssd": {
        "M": {"20-29": (42, 15), "30-39": (35, 13), "40-49": (28, 11), "50-59": (22, 9), "60-69": (18, 8), "70+": (15, 7)},
        "F": {"20-29": (45, 16), "30-39": (38, 14), "40-49": (30, 12), "50-59": (24, 10), "60-69": (20, 9), "70+": (16, 7)},
    },
    "resting_hr": {
        "M": {"20-29": (68, 10), "30-39": (70, 11), "40-49": (72, 11), "50-59": (73, 12), "60-69": (72, 11), "70+": (71, 11)},
        "F": {"20-29": (72, 10), "30-39": (73, 11), "40-49": (74, 11), "50-59": (75, 12), "60-69": (74, 11), "70+": (73, 11)},
    },
    "hscrp": {
        "M": {"20-29": (1.2, 1.5), "30-39": (1.5, 1.8), "40-49": (1.8, 2.0), "50-59": (2.2, 2.3), "60-69": (2.6, 2.5), "70+": (3.0, 2.8)},
        "F": {"20-29": (1.5, 1.8), "30-39": (1.8, 2.0), "40-49": (2.0, 2.2), "50-59": (2.5, 2.5), "60-69": (2.8, 2.7), "70+": (3.2, 3.0)},
    },
    "homa_ir": {
        "M": {"20-29": (1.8, 1.0), "30-39": (2.0, 1.2), "40-49": (2.3, 1.3), "50-59": (2.5, 1.4), "60-69": (2.4, 1.3), "70+": (2.3, 1.2)},
        "F": {"20-29": (1.6, 0.9), "30-39": (1.8, 1.0), "40-49": (2.1, 1.2), "50-59": (2.3, 1.3), "60-69": (2.2, 1.2), "70+": (2.1, 1.1)},
    },
    "fasting_glucose": {
        "M": {"20-29": (88, 10), "30-39": (92, 12), "40-49": (96, 14), "50-59": (100, 16), "60-69": (102, 17), "70+": (104, 18)},
        "F": {"20-29": (85, 9), "30-39": (88, 11), "40-49": (92, 13), "50-59": (96, 15), "60-69": (98, 16), "70+": (100, 17)},
    },
    "hba1c": {
        "M": {"20-29": (5.2, 0.4), "30-39": (5.3, 0.5), "40-49": (5.5, 0.6), "50-59": (5.6, 0.6), "60-69": (5.7, 0.7), "70+": (5.8, 0.7)},
        "F": {"20-29": (5.1, 0.4), "30-39": (5.2, 0.4), "40-49": (5.4, 0.5), "50-59": (5.5, 0.6), "60-69": (5.6, 0.6), "70+": (5.7, 0.7)},
    },
    "vo2_max": {
        "M": {"20-29": (44, 8), "30-39": (41, 8), "40-49": (38, 7), "50-59": (35, 7), "60-69": (31, 6), "70+": (27, 6)},
        "F": {"20-29": (36, 7), "30-39": (34, 6), "40-49": (31, 6), "50-59": (28, 5), "60-69": (25, 5), "70+": (22, 5)},
    },
    "grip_strength": {
        "M": {"20-29": (47, 9), "30-39": (46, 9), "40-49": (44, 8), "50-59": (41, 8), "60-69": (37, 8), "70+": (32, 7)},
        "F": {"20-29": (29, 5), "30-39": (28, 5), "40-49": (27, 5), "50-59": (25, 5), "60-69": (23, 5), "70+": (20, 4)},
    },
    "body_fat_pct": {
        "M": {"20-29": (18, 6), "30-39": (20, 6), "40-49": (22, 6), "50-59": (24, 6), "60-69": (25, 6), "70+": (26, 6)},
        "F": {"20-29": (25, 6), "30-39": (27, 6), "40-49": (29, 7), "50-59": (31, 7), "60-69": (32, 7), "70+": (33, 7)},
    },
    "ldl_c": {
        "M": {"20-29": (105, 30), "30-39": (115, 32), "40-49": (125, 34), "50-59": (130, 35), "60-69": (128, 34), "70+": (125, 33)},
        "F": {"20-29": (100, 28), "30-39": (108, 30), "40-49": (118, 32), "50-59": (130, 35), "60-69": (135, 36), "70+": (133, 35)},
    },
    "hdl_c": {
        "M": {"20-29": (48, 12), "30-39": (46, 12), "40-49": (45, 11), "50-59": (47, 12), "60-69": (49, 12), "70+": (50, 13)},
        "F": {"20-29": (58, 14), "30-39": (56, 13), "40-49": (55, 13), "50-59": (58, 14), "60-69": (60, 14), "70+": (61, 14)},
    },
    "triglycerides": {
        "M": {"20-29": (110, 50), "30-39": (130, 60), "40-49": (145, 65), "50-59": (150, 65), "60-69": (145, 60), "70+": (140, 55)},
        "F": {"20-29": (95, 40), "30-39": (105, 45), "40-49": (120, 55), "50-59": (135, 60), "60-69": (140, 60), "70+": (138, 58)},
    },
    "sleep_duration": {
        "M": {"20-29": (7.0, 1.2), "30-39": (6.8, 1.2), "40-49": (6.6, 1.3), "50-59": (6.5, 1.3), "60-69": (6.4, 1.4), "70+": (6.3, 1.4)},
        "F": {"20-29": (7.2, 1.2), "30-39": (7.0, 1.2), "40-49": (6.8, 1.3), "50-59": (6.7, 1.3), "60-69": (6.5, 1.4), "70+": (6.4, 1.4)},
    },
    "deep_sleep_pct": {
        "M": {"20-29": (20, 5), "30-39": (18, 5), "40-49": (16, 5), "50-59": (14, 5), "60-69": (12, 4), "70+": (10, 4)},
        "F": {"20-29": (21, 5), "30-39": (19, 5), "40-49": (17, 5), "50-59": (15, 5), "60-69": (13, 4), "70+": (11, 4)},
    },
    "sleep_efficiency": {
        "M": {"20-29": (88, 5), "30-39": (86, 6), "40-49": (84, 6), "50-59": (82, 7), "60-69": (80, 7), "70+": (78, 8)},
        "F": {"20-29": (89, 5), "30-39": (87, 5), "40-49": (85, 6), "50-59": (83, 6), "60-69": (81, 7), "70+": (79, 7)},
    },
    "vitamin_d": {
        "M": {"20-29": (25, 12), "30-39": (24, 11), "40-49": (23, 11), "50-59": (22, 10), "60-69": (21, 10), "70+": (20, 10)},
        "F": {"20-29": (23, 11), "30-39": (22, 11), "40-49": (21, 10), "50-59": (20, 10), "60-69": (19, 9), "70+": (18, 9)},
    },
    "daily_steps": {
        "M": {"20-29": (7500, 3000), "30-39": (7000, 2800), "40-49": (6500, 2600), "50-59": (6000, 2400), "60-69": (5500, 2200), "70+": (4500, 2000)},
        "F": {"20-29": (7000, 2800), "30-39": (6500, 2600), "40-49": (6000, 2400), "50-59": (5500, 2200), "60-69": (5000, 2000), "70+": (4000, 1800)},
    },
    "active_energy_kcal": {
        "M": {"20-29": (420, 180), "30-39": (380, 170), "40-49": (340, 160), "50-59": (300, 150), "60-69": (260, 140), "70+": (220, 120)},
        "F": {"20-29": (340, 150), "30-39": (310, 140), "40-49": (280, 130), "50-59": (250, 120), "60-69": (220, 110), "70+": (190, 100)},
    },
    "sedentary_time_hrs": {
        "M": {"20-29": (8.2, 2.5), "30-39": (8.5, 2.5), "40-49": (8.8, 2.4), "50-59": (9.0, 2.3), "60-69": (9.2, 2.3), "70+": (9.5, 2.2)},
        "F": {"20-29": (7.8, 2.4), "30-39": (8.0, 2.4), "40-49": (8.3, 2.3), "50-59": (8.5, 2.3), "60-69": (8.8, 2.2), "70+": (9.0, 2.2)},
    },
}

# For biomarkers without detailed normative data, use simple defaults
DEFAULT_NORMATIVE = {
    "mobility_score": {"M": (65, 15), "F": (68, 14)},
    "memory_processing": {"M": (72, 12), "F": (74, 11)},
    "reaction_time": {"M": (280, 40), "F": (290, 42)},
    "stress_pss": {"M": (15, 7), "F": (16, 7)},
    "cortisol_am": {"M": (14, 4), "F": (13, 4)},
    "recovery_score": {"M": (65, 15), "F": (67, 14)},
    "diet_quality": {"M": (55, 18), "F": (58, 17)},
    "activity_consistency": {"M": (52, 22), "F": (50, 21)},
    "smoking_score": {"M": (75, 25), "F": (80, 22)},
    "alcohol_score": {"M": (65, 20), "F": (75, 18)},
    "phq9_score": {"M": (5.0, 5.0), "F": (5.5, 5.2)},
    "gad7_score": {"M": (4.0, 4.0), "F": (4.5, 4.2)},
    "moca_score": {"M": (25.5, 3.0), "F": (25.0, 3.2)},
}


def get_age_band(age):
    if age < 30:
        return "20-29"
    elif age < 40:
        return "30-39"
    elif age < 50:
        return "40-49"
    elif age < 60:
        return "50-59"
    elif age < 70:
        return "60-69"
    return "70+"


def get_normative(biomarker_code, age, sex):
    age_band = get_age_band(age)
    if biomarker_code in NORMATIVE_DATA:
        sex_data = NORMATIVE_DATA[biomarker_code].get(sex, NORMATIVE_DATA[biomarker_code].get("M"))
        return sex_data.get(age_band, sex_data.get("40-49", (50, 15)))
    if biomarker_code in DEFAULT_NORMATIVE:
        return DEFAULT_NORMATIVE[biomarker_code].get(sex, DEFAULT_NORMATIVE[biomarker_code].get("M"))
    return (50, 15)

BIOMARKER_CORRELATIONS = {
    ("hba1c", "fasting_glucose"): {"strength": 0.85, "direction": "positive", "insight": "Both reflect glycemic control. Improving one directly improves the other."},
    ("hba1c", "homa_ir"): {"strength": 0.72, "direction": "positive", "insight": "Insulin resistance drives elevated HbA1c. Addressing HOMA-IR is the root fix."},
    ("hba1c", "triglycerides"): {"strength": 0.55, "direction": "positive", "insight": "Metabolic syndrome link. Reducing carbs improves both simultaneously."},
    ("hba1c", "body_fat_pct"): {"strength": 0.60, "direction": "positive", "insight": "Excess body fat increases insulin resistance, raising HbA1c."},
    ("fasting_glucose", "homa_ir"): {"strength": 0.78, "direction": "positive", "insight": "HOMA-IR is calculated from fasting glucose. They move together."},
    ("ldl_c", "hscrp"): {"strength": 0.45, "direction": "positive", "insight": "Inflammation accelerates LDL oxidation. Reducing hsCRP protects arteries."},
    ("ldl_c", "triglycerides"): {"strength": 0.40, "direction": "positive", "insight": "Both improve with dietary changes."},
    ("hdl_c", "triglycerides"): {"strength": 0.50, "direction": "negative", "insight": "High triglycerides suppress HDL. Exercise and omega-3 raise HDL while lowering TG."},
    ("hdl_c", "vo2_max"): {"strength": 0.48, "direction": "positive", "insight": "Aerobic fitness directly raises HDL."},
    ("hscrp", "body_fat_pct"): {"strength": 0.52, "direction": "positive", "insight": "Fat tissue produces inflammatory cytokines. Losing body fat reduces hsCRP."},
    ("hscrp", "sleep_duration"): {"strength": 0.35, "direction": "negative", "insight": "Poor sleep elevates inflammation."},
    ("vo2_max", "resting_hr"): {"strength": 0.65, "direction": "negative", "insight": "Higher VO2 Max = lower resting HR. Cardio training improves both."},
    ("sleep_duration", "cortisol_am"): {"strength": 0.40, "direction": "negative", "insight": "Sleep deprivation spikes cortisol."},
    ("sleep_duration", "recovery_score"): {"strength": 0.70, "direction": "positive", "insight": "More quality sleep = better recovery."},
    ("deep_sleep_pct", "recovery_score"): {"strength": 0.75, "direction": "positive", "insight": "Deep sleep is when tissue repair happens."},
    ("stress_pss", "cortisol_am"): {"strength": 0.55, "direction": "positive", "insight": "Chronic stress elevates cortisol."},
    ("stress_pss", "sleep_efficiency"): {"strength": 0.45, "direction": "negative", "insight": "Stress ruins sleep quality."},
    ("body_fat_pct", "vo2_max"): {"strength": 0.50, "direction": "negative", "insight": "Lower body fat improves VO2 Max efficiency."},
    ("vitamin_d", "recovery_score"): {"strength": 0.35, "direction": "positive", "insight": "Vitamin D supports muscle recovery and immune function."},
    ("diet_quality", "hscrp"): {"strength": 0.40, "direction": "negative", "insight": "Anti-inflammatory diet directly reduces hsCRP."},
}

COGNITIVE_ASSESSMENTS = [
    {"code": "phq9", "name": "PHQ-9 (Patient Health Questionnaire)", "domain": "Depression Screening",
     "description": "Globally validated 9-item depression severity scale (Kroenke et al., 2001).",
     "scoring": "0-4 Minimal, 5-9 Mild, 10-14 Moderate, 15-19 Moderately Severe, 20-27 Severe",
     "questions": ["Little interest or pleasure in doing things", "Feeling down, depressed, or hopeless", "Trouble falling/staying asleep", "Feeling tired or having little energy", "Poor appetite or overeating", "Feeling bad about yourself", "Trouble concentrating on things", "Moving or speaking slowly, or being fidgety", "Thoughts that you would be better off dead"],
     "options": ["Not at all (0)", "Several days (1)", "More than half the days (2)", "Nearly every day (3)"],
     "max_score": 27, "pillar": "CA", "reference": "Kroenke K, et al. J Gen Intern Med. 2001"},
    {"code": "gad7", "name": "GAD-7 (Generalized Anxiety Disorder)", "domain": "Anxiety Screening",
     "description": "7-item scale for screening generalized anxiety disorder.",
     "scoring": "0-4 Minimal, 5-9 Mild, 10-14 Moderate, 15-21 Severe",
     "questions": ["Feeling nervous, anxious, or on edge", "Not being able to stop worrying", "Worrying too much about different things", "Trouble relaxing", "Being so restless that it's hard to sit still", "Becoming easily annoyed or irritable", "Feeling afraid as if something awful might happen"],
     "options": ["Not at all (0)", "Several days (1)", "More than half the days (2)", "Nearly every day (3)"],
     "max_score": 21, "pillar": "CA", "reference": "Spitzer RL, et al. Arch Intern Med. 2006"},
    {"code": "psqi", "name": "Pittsburgh Sleep Quality Index", "domain": "Sleep Quality",
     "description": "Global standard for measuring sleep quality over the past month.",
     "scoring": "0-5 Good, 6-10 Poor, 11-21 Very Poor",
     "questions": ["Subjective sleep quality rating", "How long to fall asleep?", "Hours of actual sleep?", "Cannot get to sleep within 30 min", "Wake up in the middle of the night", "Cannot breathe comfortably", "Taken medicine to help sleep?", "Trouble staying awake during day?", "Enthusiasm to get things done?"],
     "options": ["Not during past month (0)", "Less than once/week (1)", "Once or twice/week (2)", "Three+ times/week (3)"],
     "max_score": 21, "pillar": "SR", "reference": "Buysse DJ, et al. Psychiatry Res. 1989"},
    {"code": "dass21", "name": "DASS-21", "domain": "Psychological Wellbeing",
     "description": "21-item self-report measuring depression, anxiety, and stress.",
     "scoring": "Depression: 0-4 Normal, 5-6 Mild, 7-10 Moderate, 11-13 Severe, 14+ Extreme",
     "questions": ["I found it hard to wind down", "I was aware of dryness of my mouth", "I couldn't experience any positive feeling", "I experienced breathing difficulty", "I found it difficult to work up initiative", "I tended to over-react", "I experienced trembling"],
     "options": ["Did not apply (0)", "Applied some of the time (1)", "Applied good part of time (2)", "Applied most of the time (3)"],
     "max_score": 63, "pillar": "CA", "reference": "Lovibond SH & Lovibond PF. 1995"},
    {"code": "moca", "name": "MoCA (Montreal Cognitive Assessment)", "domain": "Cognitive Function",
     "description": "Rapid screening for mild cognitive impairment.",
     "scoring": "26-30 Normal, 18-25 Mild Impairment, <18 Moderate/Severe",
     "questions": ["Visuospatial/Executive", "Naming", "Attention", "Language", "Abstraction", "Delayed Recall", "Orientation"],
     "options": ["Score per section varies"],
     "max_score": 30, "pillar": "CA", "reference": "Nasreddine ZS, et al. J Am Geriatr Soc. 2005"},
]
