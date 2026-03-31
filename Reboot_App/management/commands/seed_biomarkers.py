"""
biomarkers/management/commands/seed_biomarkers.py

Run once to populate BiomarkerDefinition, PillarConfig,
WearableDevice, CognitiveAssessmentTemplate, and BiomarkerCorrelation
from the original FastAPI hard-coded dicts.

Usage:
    python manage.py seed_biomarkers
"""

from django.core.management.base import BaseCommand

# from Reboot_App.management.commands.models import (
#     BiomarkerDefinition, PillarConfig, WearableDevice,
#     CognitiveAssessmentTemplate, BiomarkerCorrelation,
# )

from Reboot_App.models import (
    BiomarkerDefinition,
    PillarConfig,
    WearableDevice,
    CognitiveAssessmentTemplate,
    BiomarkerCorrelation,
)


# ── Copy-paste from hps_engine/normative.py ──────────────────────────────────

PILLAR_CONFIG = {
    "MH": {"name": "Metabolic Health",   "color": "#E84B4B"},
    "CV": {"name": "Cardiovascular",     "color": "#E84B95"},
    "SR": {"name": "Sleep & Recovery",   "color": "#7B35D8"},
    "CA": {"name": "Cognitive & Mental", "color": "#3599E8"},
    "BM": {"name": "Body Composition",   "color": "#35C4E8"},
    "NU": {"name": "Nutrition",          "color": "#35E88A"},
}

BIOMARKER_DEFINITIONS = {
    "hba1c":           {"name": "HbA1c",              "domain": "Glycemic Control",      "pillar": "MH", "unit": "%",         "direction": "lower_better",  "optimal_low": 4.0,  "optimal_high": 5.7,  "data_source": "lab"},
    "fasting_glucose": {"name": "Fasting Glucose",    "domain": "Glycemic Control",      "pillar": "MH", "unit": "mg/dL",     "direction": "lower_better",  "optimal_low": 70,   "optimal_high": 99,   "data_source": "lab"},
    "homa_ir":         {"name": "HOMA-IR",            "domain": "Insulin Resistance",    "pillar": "MH", "unit": "",          "direction": "lower_better",  "optimal_low": 0,    "optimal_high": 1.5,  "data_source": "lab"},
    "ldl_c":           {"name": "LDL Cholesterol",    "domain": "Lipid Panel",           "pillar": "CV", "unit": "mg/dL",     "direction": "lower_better",  "optimal_low": 0,    "optimal_high": 100,  "data_source": "lab"},
    "hdl_c":           {"name": "HDL Cholesterol",    "domain": "Lipid Panel",           "pillar": "CV", "unit": "mg/dL",     "direction": "higher_better", "optimal_low": 60,   "optimal_high": 100,  "data_source": "lab"},
    "triglycerides":   {"name": "Triglycerides",      "domain": "Lipid Panel",           "pillar": "CV", "unit": "mg/dL",     "direction": "lower_better",  "optimal_low": 0,    "optimal_high": 150,  "data_source": "lab"},
    "hscrp":           {"name": "hsCRP",              "domain": "Inflammation",          "pillar": "CV", "unit": "mg/L",      "direction": "lower_better",  "optimal_low": 0,    "optimal_high": 1.0,  "data_source": "lab"},
    "vo2_max":         {"name": "VO2 Max",            "domain": "Aerobic Fitness",       "pillar": "CV", "unit": "mL/kg/min", "direction": "higher_better", "optimal_low": 40,   "optimal_high": 60,   "data_source": "wearable"},
    "resting_hr":      {"name": "Resting Heart Rate", "domain": "Cardiovascular",        "pillar": "CV", "unit": "bpm",       "direction": "lower_better",  "optimal_low": 40,   "optimal_high": 60,   "data_source": "wearable"},
    "hrv_rmssd":       {"name": "HRV (RMSSD)",        "domain": "Recovery",              "pillar": "SR", "unit": "ms",        "direction": "higher_better", "optimal_low": 40,   "optimal_high": 80,   "data_source": "wearable"},
    "sleep_duration":  {"name": "Sleep Duration",     "domain": "Sleep",                 "pillar": "SR", "unit": "hrs",       "direction": "optimal_range", "optimal_low": 7,    "optimal_high": 9,    "data_source": "wearable"},
    "deep_sleep_pct":  {"name": "Deep Sleep %",       "domain": "Sleep Quality",         "pillar": "SR", "unit": "%",         "direction": "higher_better", "optimal_low": 20,   "optimal_high": 25,   "data_source": "wearable"},
    "sleep_efficiency":{"name": "Sleep Efficiency",   "domain": "Sleep Quality",         "pillar": "SR", "unit": "%",         "direction": "higher_better", "optimal_low": 85,   "optimal_high": 100,  "data_source": "wearable"},
    "recovery_score":  {"name": "Recovery Score",     "domain": "Recovery",              "pillar": "SR", "unit": "/100",      "direction": "higher_better", "optimal_low": 70,   "optimal_high": 100,  "data_source": "wearable"},
    "cortisol_am":     {"name": "Cortisol (AM)",      "domain": "Hormonal",              "pillar": "CA", "unit": "µg/dL",     "direction": "optimal_range", "optimal_low": 6,    "optimal_high": 18,   "data_source": "lab"},
    "stress_pss":      {"name": "Stress (PSS)",       "domain": "Psychological",         "pillar": "CA", "unit": "/40",       "direction": "lower_better",  "optimal_low": 0,    "optimal_high": 13,   "data_source": "manual"},
    "vitamin_d":       {"name": "Vitamin D",          "domain": "Nutrition",             "pillar": "NU", "unit": "ng/mL",     "direction": "optimal_range", "optimal_low": 40,   "optimal_high": 60,   "data_source": "lab"},
    "body_fat_pct":    {"name": "Body Fat %",         "domain": "Body Composition",      "pillar": "BM", "unit": "%",         "direction": "lower_better",  "optimal_low": 8,    "optimal_high": 20,   "data_source": "manual"},
    "diet_quality":    {"name": "Diet Quality Score", "domain": "Nutrition",             "pillar": "NU", "unit": "/100",      "direction": "higher_better", "optimal_low": 70,   "optimal_high": 100,  "data_source": "manual"},
    "spo2":            {"name": "SpO2",               "domain": "Respiratory",           "pillar": "CV", "unit": "%",         "direction": "higher_better", "optimal_low": 95,   "optimal_high": 100,  "data_source": "wearable"},
}

BIOMARKER_CORRELATIONS = {
    ("hba1c", "fasting_glucose"): {"strength": 0.85, "direction": "positive", "insight": "Both reflect glycemic control. Improving one directly improves the other."},
    ("hba1c", "homa_ir"):         {"strength": 0.72, "direction": "positive", "insight": "Insulin resistance drives elevated HbA1c. Addressing HOMA-IR is the root fix."},
    ("hba1c", "triglycerides"):   {"strength": 0.55, "direction": "positive", "insight": "Metabolic syndrome link. Reducing carbs improves both simultaneously."},
    ("hba1c", "body_fat_pct"):    {"strength": 0.60, "direction": "positive", "insight": "Excess body fat increases insulin resistance, raising HbA1c."},
    ("fasting_glucose", "homa_ir"):{"strength": 0.78,"direction": "positive", "insight": "HOMA-IR is calculated from fasting glucose. They move together."},
    ("ldl_c", "hscrp"):           {"strength": 0.45, "direction": "positive", "insight": "Inflammation accelerates LDL oxidation. Reducing hsCRP protects arteries."},
    ("ldl_c", "triglycerides"):   {"strength": 0.40, "direction": "positive", "insight": "Both improve with dietary changes."},
    ("hdl_c", "triglycerides"):   {"strength": 0.50, "direction": "negative", "insight": "High triglycerides suppress HDL."},
    ("hdl_c", "vo2_max"):         {"strength": 0.48, "direction": "positive", "insight": "Aerobic fitness directly raises HDL."},
    ("hscrp", "body_fat_pct"):    {"strength": 0.52, "direction": "positive", "insight": "Fat tissue produces inflammatory cytokines."},
    ("hscrp", "sleep_duration"):  {"strength": 0.35, "direction": "negative", "insight": "Poor sleep elevates inflammation."},
    ("vo2_max", "resting_hr"):    {"strength": 0.65, "direction": "negative", "insight": "Higher VO2 Max = lower resting HR."},
    ("sleep_duration", "cortisol_am"):  {"strength": 0.40, "direction": "negative", "insight": "Sleep deprivation spikes cortisol."},
    ("sleep_duration", "recovery_score"):{"strength": 0.70,"direction": "positive","insight": "More quality sleep = better recovery."},
    ("deep_sleep_pct", "recovery_score"):{"strength": 0.75,"direction": "positive","insight": "Deep sleep is when tissue repair happens."},
    ("stress_pss", "cortisol_am"):{"strength": 0.55, "direction": "positive", "insight": "Chronic stress elevates cortisol."},
    ("stress_pss", "sleep_efficiency"):{"strength":0.45,"direction":"negative","insight": "Stress ruins sleep quality."},
    ("body_fat_pct", "vo2_max"):  {"strength": 0.50, "direction": "negative", "insight": "Lower body fat improves VO2 Max efficiency."},
    ("vitamin_d", "recovery_score"):{"strength": 0.35,"direction": "positive","insight": "Vitamin D supports muscle recovery."},
    ("diet_quality", "hscrp"):    {"strength": 0.40, "direction": "negative", "insight": "Anti-inflammatory diet directly reduces hsCRP."},
}

WEARABLE_DEVICES = {
    "apple_health":  {"name": "Apple Health",        "category": "phone", "icon": "apple",    "auth_url": "https://appleid.apple.com/auth/authorize",            "scope": "healthkit.read",                         "metrics": ["Heart Rate","HRV","Steps","Sleep","SpO2","VO2 Max","Active Energy","Mindful Minutes"]},
    "google_health": {"name": "Google Health Connect","category": "phone","icon": "google",   "auth_url": "https://accounts.google.com/o/oauth2/auth",           "scope": "https://www.googleapis.com/auth/fitness.activity.read", "metrics": ["Heart Rate","Steps","Sleep","Blood Glucose","Blood Pressure","SpO2","Body Temperature"]},
    "oura":          {"name": "Oura Ring",           "category": "ring",  "icon": "oura",     "auth_url": "https://cloud.ouraring.com/oauth/authorize",          "scope": "daily heartrate sleep",                  "metrics": ["HRV RMSSD","Deep Sleep","REM","Recovery Score","Skin Temperature","Readiness"]},
    "garmin":        {"name": "Garmin Connect",      "category": "watch", "icon": "garmin",   "auth_url": "https://connect.garmin.com/oauthConfirm",             "scope": "activity sleep",                         "metrics": ["VO2 Max","HRV Status","Body Battery","Sleep Score","Stress Level","Steps"]},
    "fitbit":        {"name": "Fitbit",              "category": "watch", "icon": "fitbit",   "auth_url": "https://www.fitbit.com/oauth2/authorize",             "scope": "activity heartrate sleep weight",        "metrics": ["Heart Rate","Sleep Stages","SpO2","Stress Score","Active Zone Minutes","Steps"]},
    "whoop":         {"name": "WHOOP",               "category": "band",  "icon": "whoop",    "auth_url": "https://api.prod.whoop.com/oauth/oauth2/auth",        "scope": "read:recovery read:sleep",               "metrics": ["HRV","Recovery Score","Sleep Performance","Strain Score","Respiratory Rate"]},
    "withings":      {"name": "Withings",            "category": "scale", "icon": "withings", "auth_url": "https://account.withings.com/oauth2_user/authorize2", "scope": "user.metrics user.activity",             "metrics": ["Weight","Body Fat %","Blood Pressure","ECG","Pulse Wave Velocity"]},
    "samsung_health":{"name": "Samsung Health",      "category": "phone", "icon": "samsung",  "auth_url": "https://account.samsung.com/accounts/v1/SAHMS/auth",  "scope": "health.read",                            "metrics": ["Heart Rate","SpO2","Sleep","Steps","Stress","Blood Pressure","Body Composition"]},
    "polar":         {"name": "Polar",               "category": "watch", "icon": "polar",    "auth_url": "https://flow.polar.com/oauth2/authorization",         "scope": "accesslink.read_all",                    "metrics": ["Heart Rate","HRV","Sleep","Running Index","Cardio Load","Nightly Recharge"]},
    "amazfit":       {"name": "Amazfit / Zepp",      "category": "watch", "icon": "amazfit",  "auth_url": "https://auth.amazfit.com/oauth2/authorize",           "scope": "health.read",                            "metrics": ["Heart Rate","SpO2","Sleep","PAI Score","Stress","Steps"]},
    "coros":         {"name": "COROS",               "category": "watch", "icon": "coros",    "auth_url": "https://connect.coros.com/oauth2/authorize",          "scope": "activity.read",                          "metrics": ["Heart Rate","HRV","Sleep","Training Load","Base Fitness","VO2 Max"]},
}

COGNITIVE_ASSESSMENTS = [
    {"code": "phq9",  "name": "PHQ-9 (Patient Health Questionnaire)", "domain": "Depression Screening",   "description": "Globally validated 9-item depression severity scale.", "scoring": "0-4 Minimal, 5-9 Mild, 10-14 Moderate, 15-19 Moderately Severe, 20-27 Severe", "questions": ["Little interest or pleasure in doing things","Feeling down, depressed, or hopeless","Trouble falling/staying asleep","Feeling tired or having little energy","Poor appetite or overeating","Feeling bad about yourself","Trouble concentrating on things","Moving or speaking slowly, or being fidgety","Thoughts that you would be better off dead"], "options": ["Not at all (0)","Several days (1)","More than half the days (2)","Nearly every day (3)"], "max_score": 27, "pillar": "CA", "reference": "Kroenke K, et al. J Gen Intern Med. 2001"},
    {"code": "gad7",  "name": "GAD-7 (Generalized Anxiety Disorder)", "domain": "Anxiety Screening",      "description": "7-item scale for screening generalized anxiety disorder.", "scoring": "0-4 Minimal, 5-9 Mild, 10-14 Moderate, 15-21 Severe",                        "questions": ["Feeling nervous, anxious, or on edge","Not being able to stop worrying","Worrying too much about different things","Trouble relaxing","Being so restless that it's hard to sit still","Becoming easily annoyed or irritable","Feeling afraid as if something awful might happen"], "options": ["Not at all (0)","Several days (1)","More than half the days (2)","Nearly every day (3)"], "max_score": 21, "pillar": "CA", "reference": "Spitzer RL, et al. Arch Intern Med. 2006"},
    {"code": "psqi",  "name": "Pittsburgh Sleep Quality Index",        "domain": "Sleep Quality",           "description": "Global standard for measuring sleep quality over the past month.", "scoring": "0-5 Good, 6-10 Poor, 11-21 Very Poor",                                   "questions": ["Subjective sleep quality rating","How long to fall asleep?","Hours of actual sleep?","Cannot get to sleep within 30 min","Wake up in the middle of the night","Cannot breathe comfortably","Taken medicine to help sleep?","Trouble staying awake during day?","Enthusiasm to get things done?"], "options": ["Not during past month (0)","Less than once/week (1)","Once or twice/week (2)","Three+ times/week (3)"], "max_score": 21, "pillar": "SR", "reference": "Buysse DJ, et al. Psychiatry Res. 1989"},
    {"code": "dass21","name": "DASS-21",                                "domain": "Psychological Wellbeing","description": "21-item self-report measuring depression, anxiety, and stress.", "scoring": "Depression: 0-4 Normal, 5-6 Mild, 7-10 Moderate, 11-13 Severe, 14+ Extreme","questions": ["I found it hard to wind down","I was aware of dryness of my mouth","I couldn't experience any positive feeling","I experienced breathing difficulty","I found it difficult to work up initiative","I tended to over-react","I experienced trembling"], "options": ["Did not apply (0)","Applied some of the time (1)","Applied good part of time (2)","Applied most of the time (3)"], "max_score": 63, "pillar": "CA", "reference": "Lovibond SH & Lovibond PF. 1995"},
    {"code": "moca",  "name": "MoCA (Montreal Cognitive Assessment)",  "domain": "Cognitive Function",     "description": "Rapid screening for mild cognitive impairment.", "scoring": "26-30 Normal, 18-25 Mild Impairment, <18 Moderate/Severe",                     "questions": ["Visuospatial/Executive","Naming","Attention","Language","Abstraction","Delayed Recall","Orientation"], "options": ["Score per section varies"], "max_score": 30, "pillar": "CA", "reference": "Nasreddine ZS, et al. J Am Geriatr Soc. 2005"},
]


class Command(BaseCommand):
    help = "Seed all biomarker reference data from the original FastAPI dicts"

    def handle(self, *args, **options):
        self._seed_pillars()
        self._seed_definitions()
        self._seed_correlations()
        self._seed_wearable_devices()
        self._seed_cognitive_templates()
        self.stdout.write(self.style.SUCCESS("✅  Biomarker reference data seeded successfully."))

    def _seed_pillars(self):
        for code, cfg in PILLAR_CONFIG.items():
            PillarConfig.objects.update_or_create(
                code=code, defaults={"name": cfg["name"], "color": cfg["color"]}
            )
        self.stdout.write(f"  Pillars: {len(PILLAR_CONFIG)} upserted")

    def _seed_definitions(self):
        for code, d in BIOMARKER_DEFINITIONS.items():
            BiomarkerDefinition.objects.update_or_create(code=code, defaults={
                "name": d["name"], "domain": d.get("domain", ""),
                "pillar": d["pillar"], "unit": d.get("unit", ""),
                "direction": d.get("direction", "optimal_range"),
                "optimal_low": d.get("optimal_low"), "optimal_high": d.get("optimal_high"),
                "data_source": d.get("data_source", "manual"),
            })
        self.stdout.write(f"  Definitions: {len(BIOMARKER_DEFINITIONS)} upserted")

    def _seed_correlations(self):
        count = 0
        for (a, b), info in BIOMARKER_CORRELATIONS.items():
            try:
                defn_a = BiomarkerDefinition.objects.get(code=a)
                defn_b = BiomarkerDefinition.objects.get(code=b)
            except BiomarkerDefinition.DoesNotExist:
                continue
            BiomarkerCorrelation.objects.update_or_create(
                biomarker_a=defn_a, biomarker_b=defn_b,
                defaults={"strength": info["strength"], "direction": info["direction"],
                          "insight": info["insight"]},
            )
            count += 1
        self.stdout.write(f"  Correlations: {count} upserted")

    def _seed_wearable_devices(self):
        for device_id, cfg in WEARABLE_DEVICES.items():
            WearableDevice.objects.update_or_create(device_id=device_id, defaults={
                "name": cfg["name"], "category": cfg["category"],
                "icon": cfg.get("icon", ""), "auth_url": cfg.get("auth_url", ""),
                "scope": cfg.get("scope", ""), "metrics": cfg.get("metrics", []),
            })
        self.stdout.write(f"  Wearable devices: {len(WEARABLE_DEVICES)} upserted")

    def _seed_cognitive_templates(self):
        for t in COGNITIVE_ASSESSMENTS:
            CognitiveAssessmentTemplate.objects.update_or_create(code=t["code"], defaults={
                "name": t["name"], "domain": t["domain"],
                "description": t.get("description", ""),
                "scoring": t.get("scoring", ""),
                "questions": t.get("questions", []),
                "options": t.get("options", []),
                "max_score": t["max_score"], "pillar": t["pillar"],
                "reference": t.get("reference", ""),
            })
        self.stdout.write(f"  Cognitive templates: {len(COGNITIVE_ASSESSMENTS)} upserted")