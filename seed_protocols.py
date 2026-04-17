import os
import django
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from django.contrib.auth.models import User
from Reboot_App.models import CCProtocol, CCPrescription

# Full Protocol Data from Flask protocol_seeds.py
LONGEVITY_PROTOCOLS = [
    {
        "lgp_id": "LGP-001",
        "name": "Comprehensive Longevity Assessment (CLA)",
        "category": "Assessment",
        "description": "Foundational assessment establishing baseline across all five HPS dimensions. Integrates biomarkers, fitness, cognition, sleep, and lifestyle data for a holistic longevity trajectory view.",
        "hallmarks_of_ageing": ["All Hallmarks"],
        "evidence_level": "A",
        "hps_dimensions": ["BR", "PF", "CA", "SR", "BL"],
        "duration_default_weeks": 2,
        "interventions": [
            {"type": "Clinical Assessment", "name": "Baseline Biomarker Panel", "details": "Comprehensive labs: glucose, HbA1c, lipid panel, LFTs, KFTs, hs-CRP, homocysteine, Vitamin D, B12, Iron Panel, TSH, Free T4, Testosterone, DHEA-S, Cortisol, IGF-1, Telomere Length."},
            {"type": "Clinical Assessment", "name": "Physical Fitness Assessment", "details": "VO2 Max estimation, Resting HR, Blood Pressure, BMI, Body Fat % (DEXA), Skeletal Muscle Mass (DEXA), Bone Mineral Density (T-score)."},
            {"type": "Clinical Assessment", "name": "Cognitive Assessment Battery", "details": "Montreal Cognitive Assessment (MoCA), Reaction Time (Cognitive)."},
            {"type": "Clinical Assessment", "name": "Sleep Quality Assessment", "details": "Sleep Duration & Efficiency (wearable), Pittsburgh Sleep Quality Index (PSQI)."},
            {"type": "Clinical Assessment", "name": "Lifestyle & Psychological Assessment", "details": "PHQ-9 (Depression), GAD-7 (Anxiety), Lifestyle Consistency Scoring."},
            {"type": "Clinical Assessment", "name": "Biological Age Calculation", "details": "Levine PhenoAge algorithm and VO2max proxy calculation."},
        ],
        "smart_goals_template": {
            "specific": "Achieve target values for key biomarkers, fitness metrics, cognitive scores, sleep quality, and lifestyle adherence.",
            "measurable": "Quantifiable improvements in all assessed metrics.",
            "achievable": "Goals set based on individual baseline and evidence-based protocol targets.",
            "relevant": "Directly contribute to improving HPS dimensions and overall longevity.",
            "time_bound": "Complete full assessment within 2 weeks; set targets for 12-16 week intervals."
        },
        "codes": {
            "icd10": [
                {"code": "Z00.00", "desc": "General adult medical exam without abnormal findings"},
                {"code": "Z00.01", "desc": "General adult medical exam with abnormal findings"},
            ],
            "loinc": [
                {"code": "1558-6", "desc": "Glucose, Fasting"}, {"code": "4548-4", "desc": "HbA1c"},
                {"code": "2093-3", "desc": "Total Cholesterol"}, {"code": "13457-7", "desc": "LDL Cholesterol"},
                {"code": "2085-9", "desc": "HDL Cholesterol"}, {"code": "2571-8", "desc": "Triglycerides"},
                {"code": "30522-7", "desc": "hs-CRP"}, {"code": "13965-9", "desc": "Homocysteine"},
                {"code": "14771-0", "desc": "Vitamin D, 25-OH"}, {"code": "2132-9", "desc": "Vitamin B12"},
                {"code": "3016-3", "desc": "TSH"}, {"code": "2857-1", "desc": "Testosterone Total"},
                {"code": "2191-5", "desc": "DHEA-S"}, {"code": "2143-6", "desc": "Cortisol, AM"},
                {"code": "2484-4", "desc": "IGF-1"}, {"code": "98898-1", "desc": "Telomere Length"},
                {"code": "80493-0", "desc": "VO2 Max"}, {"code": "72133-2", "desc": "MoCA"},
                {"code": "52741-7", "desc": "PSQI"}, {"code": "44261-6", "desc": "PHQ-9"},
                {"code": "69737-5", "desc": "GAD-7"},
            ]
        },
    },
    {
        "lgp_id": "LGP-002",
        "name": "Zone 2 Aerobic Training — Metabolic Foundation",
        "category": "Exercise & Fitness",
        "description": "Sustained aerobic exercise at Zone 2 intensity to improve mitochondrial function, enhance fat oxidation, and build aerobic capacity crucial for longevity and disease prevention.",
        "hallmarks_of_ageing": ["Genomic Instability", "Telomere Attrition", "Mitochondrial Dysfunction", "Deregulated Nutrient Sensing"],
        "evidence_level": "A",
        "hps_dimensions": ["BR", "PF", "SR"],
        "duration_default_weeks": 12,
        "interventions": [
            {"type": "Exercise Prescription", "name": "Zone 2 Aerobic Training", "details": "Frequency: 3-5x/week; Intensity: 60-70% HRmax (Zone 2); Duration: 30-60 min/session; Type: Cycling, walking, rowing, swimming; Volume: 150-300 min/week; Progression: +5% volume/week."},
        ],
        "smart_goals_template": {
            "specific": "Achieve 150-300 minutes of Zone 2 aerobic exercise per week at 60-70% HRmax.",
            "measurable": "Track weekly duration and average HR during sessions.",
            "achievable": "Gradually increase volume by 5% per week.",
            "relevant": "Enhances mitochondrial function, fat oxidation, and cardiovascular health.",
            "time_bound": "Maintain target volume for minimum 12 weeks."
        },
        "codes": {
            "icd10": [{"code": "Z72.3", "desc": "Lack of physical exercise"}],
            "loinc": [
                {"code": "80493-0", "desc": "VO2 Max"}, {"code": "8867-4", "desc": "Resting Heart Rate"},
                {"code": "80404-7", "desc": "HRV RMSSD"}, {"code": "39156-5", "desc": "BMI"},
            ]
        },
    },
    {
        "lgp_id": "LGP-003",
        "name": "Resistance Training for Longevity (RTL)",
        "category": "Exercise & Fitness",
        "description": "Build and maintain skeletal muscle mass, strength, and power — critical for metabolic health, functional independence, and sarcopenia prevention. Positively impacts bone density and insulin sensitivity.",
        "hallmarks_of_ageing": ["Genomic Instability", "Loss of Proteostasis", "Stem Cell Exhaustion", "Deregulated Nutrient Sensing"],
        "evidence_level": "A",
        "hps_dimensions": ["PF", "BR"],
        "duration_default_weeks": 24,
        "interventions": [
            {"type": "Exercise Prescription", "name": "Resistance Training", "details": "Frequency: 2-3x/week; Intensity: 70-85% 1RM; Sets/Reps: 3-4 sets x 8-12 reps; Type: Compound movements (squat, deadlift, push, pull); Progression: +2.5-5% load per phase."},
        ],
        "smart_goals_template": {
            "specific": "Increase strength and skeletal muscle mass through compound resistance exercises.",
            "measurable": "Progressive overload: increase load by 2.5-5% per phase; track skeletal muscle mass.",
            "achievable": "Adhere to 2-3 sessions/week with appropriate recovery.",
            "relevant": "Combats sarcopenia, enhances metabolic health and Physical Fitness.",
            "time_bound": "Significant strength gains and muscle mass increases within 12-24 weeks."
        },
        "codes": {
            "icd10": [
                {"code": "M62.50", "desc": "Muscle weakness, unspecified"},
                {"code": "M81.0", "desc": "Osteoporosis without pathological fracture"},
            ],
            "loinc": [
                {"code": "73964-3", "desc": "Skeletal Muscle Mass"}, {"code": "83318-2", "desc": "Handgrip Strength"},
                {"code": "38265-5", "desc": "Bone Mineral Density T-score"},
            ]
        },
    },
    {
        "lgp_id": "LGP-004",
        "name": "Norwegian 4x4 HIIT Protocol",
        "category": "Exercise & Fitness",
        "description": "High-intensity interval training with four 4-minute intervals at 85-95% HRmax, interspersed with 3-minute active recovery. Rapidly improves VO2max and cardiovascular fitness.",
        "hallmarks_of_ageing": ["Mitochondrial Dysfunction", "Deregulated Nutrient Sensing"],
        "evidence_level": "A",
        "hps_dimensions": ["PF", "SR"],
        "duration_default_weeks": 8,
        "interventions": [
            {"type": "Exercise Prescription", "name": "4x4 HIIT Intervals", "details": "Frequency: 2x/week (after Zone 2 base); Intensity: 85-95% HRmax (Zone 4-5); Interval: 4 min work / 3 min active recovery; Type: Running, cycling, rowing."},
        ],
        "smart_goals_template": {
            "specific": "Complete two sessions per week of 4x4 minute HIIT intervals.",
            "measurable": "Track session adherence and maintain target HR zones during intervals.",
            "achievable": "Integrate after building a Zone 2 aerobic base (LGP-002).",
            "relevant": "Significantly increases VO2max and cardiovascular health.",
            "time_bound": "Complete protocol for at least 8 weeks."
        },
        "codes": {
            "icd10": [{"code": "Z72.3", "desc": "Lack of physical exercise"}],
            "loinc": [
                {"code": "80493-0", "desc": "VO2 Max"}, {"code": "80404-7", "desc": "HRV RMSSD"},
                {"code": "8867-4", "desc": "Resting Heart Rate"},
            ]
        },
    },
    {
        "lgp_id": "LGP-005",
        "name": "Time-Restricted Eating 16:8 (TRE)",
        "category": "Nutrition & Metabolism",
        "description": "Restrict food intake to an 8-hour window daily with 16-hour fasting. Promotes metabolic flexibility, enhances cellular repair via autophagy, and improves insulin sensitivity.",
        "hallmarks_of_ageing": ["Disabled Macroautophagy", "Deregulated Nutrient Sensing", "Loss of Proteostasis"],
        "evidence_level": "B",
        "hps_dimensions": ["BR", "BL"],
        "duration_default_weeks": 12,
        "interventions": [
            {"type": "Dietary Intervention", "name": "16:8 Time-Restricted Eating", "details": "Eating window: 8-10 hours; Fasting: 14-16 hours; No caloric intake during fast; CGM monitoring recommended; aims to activate mTOR inhibition and autophagy."},
        ],
        "smart_goals_template": {
            "specific": "Adhere to an 8-10 hour eating window daily.",
            "measurable": "Track daily adherence to the eating window.",
            "achievable": "Start with 10-hour window and gradually reduce.",
            "relevant": "Improves metabolic health, promotes cellular repair.",
            "time_bound": "Maintain adherence for minimum 12 weeks."
        },
        "codes": {
            "icd10": [
                {"code": "E66.01", "desc": "Morbid obesity due to excess calories"},
                {"code": "R73.09", "desc": "Prediabetes"},
            ],
            "loinc": [
                {"code": "1558-6", "desc": "Glucose, Fasting"}, {"code": "4548-4", "desc": "HbA1c"},
                {"code": "20448-7", "desc": "Insulin, Fasting"},
            ]
        },
    },
    {
        "lgp_id": "LGP-006",
        "name": "Mediterranean Longevity Diet (MLD)",
        "category": "Nutrition & Metabolism",
        "description": "Plant-forward dietary pattern emphasizing olive oil, nuts, legumes, fish, abundant vegetables and fruits. Associated with reduced chronic disease risk and improved longevity.",
        "hallmarks_of_ageing": ["Altered Intercellular Communication", "Chronic Inflammation", "Dysbiosis"],
        "evidence_level": "A",
        "hps_dimensions": ["BR", "BL"],
        "duration_default_weeks": 16,
        "interventions": [
            {"type": "Dietary Intervention", "name": "Mediterranean Longevity Diet", "details": "Primary fat: EVOO >= 4 tbsp/day; Nuts, legumes, fish (3x/week); Abundant vegetables & fruits; Minimal red meat; Moderate wine intake optional."},
        ],
        "smart_goals_template": {
            "specific": "Adopt dietary pattern rich in vegetables, fruits, whole grains, legumes, nuts, fish, and healthy fats.",
            "measurable": "Track Mediterranean Diet Adherence Score (MEDAS).",
            "achievable": "Gradually incorporate Mediterranean-style meals.",
            "relevant": "Reduces inflammation, improves cardiovascular health, supports gut diversity.",
            "time_bound": "Maintain consistently for at least 16 weeks."
        },
        "codes": {
            "icd10": [
                {"code": "E78.5", "desc": "Hyperlipidemia"}, {"code": "I10", "desc": "Essential hypertension"},
            ],
            "loinc": [
                {"code": "30522-7", "desc": "hs-CRP"}, {"code": "2093-3", "desc": "Total Cholesterol"},
                {"code": "13457-7", "desc": "LDL"}, {"code": "2085-9", "desc": "HDL"},
                {"code": "2571-8", "desc": "Triglycerides"},
            ]
        },
    },
    {
        "lgp_id": "LGP-007",
        "name": "Fasting Mimicking Diet (FMD) — Monthly 5-Day",
        "category": "Nutrition & Metabolism",
        "description": "Short-term periodic diet mimicking fasting benefits while providing essential nutrients. Promotes cellular regeneration, stem cell rejuvenation, and metabolic benefits.",
        "hallmarks_of_ageing": ["Disabled Macroautophagy", "Stem Cell Exhaustion", "Deregulated Nutrient Sensing", "Cellular Senescence"],
        "evidence_level": "B",
        "hps_dimensions": ["BR", "BL"],
        "duration_default_weeks": 24,
        "interventions": [
            {"type": "Dietary Intervention", "name": "5-Day Fasting Mimicking Diet", "details": "Monthly 5-day cycle. Day 1: ~1100 kcal; Days 2-5: ~725 kcal. Plant-based, high healthy fats, low protein. Induces autophagy and stem cell rejuvenation."},
        ],
        "smart_goals_template": {
            "specific": "Complete a 5-day FMD each month.",
            "measurable": "Track adherence to daily caloric and macronutrient targets.",
            "achievable": "Follow provided meal plan and guidance.",
            "relevant": "Supports cellular repair, metabolic health, and longevity.",
            "time_bound": "Adhere to monthly cycle for 3-6 months."
        },
        "codes": {
            "icd10": [{"code": "Z00.00", "desc": "Preventive general adult exam"}],
            "loinc": [
                {"code": "1558-6", "desc": "Glucose, Fasting"}, {"code": "4548-4", "desc": "HbA1c"},
                {"code": "2484-4", "desc": "IGF-1"},
            ]
        },
    },
    {
        "lgp_id": "LGP-008",
        "name": "CBT-I for Insomnia & Sleep Optimisation",
        "category": "Behavioral & Psychology",
        "description": "Cognitive Behavioral Therapy for Insomnia — structured program to identify and change thoughts and behaviors interfering with sleep, improving sleep quality and duration.",
        "hallmarks_of_ageing": ["Altered Intercellular Communication", "Chronic Inflammation"],
        "evidence_level": "A",
        "hps_dimensions": ["SR", "CA", "BL"],
        "duration_default_weeks": 8,
        "interventions": [
            {"type": "Behavioral Therapy", "name": "CBT-I Program", "details": "6-8 sessions; sleep diary analysis; stimulus control; sleep restriction therapy; cognitive restructuring for sleep-related thoughts."},
        ],
        "smart_goals_template": {
            "specific": "Improve sleep onset latency, sleep efficiency, and reduce nighttime awakenings.",
            "measurable": "Track sleep diary metrics, PSQI scores, subjective sleep quality.",
            "achievable": "Consistent application of CBT-I techniques.",
            "relevant": "Enhances Recovery & Sleep, Cognitive Agility, Lifestyle Consistency.",
            "time_bound": "Achieve significant sleep improvement within 8 weeks."
        },
        "codes": {
            "icd10": [
                {"code": "G47.00", "desc": "Insomnia, unspecified"},
                {"code": "F51.01", "desc": "Insomnia due to anxiety/depression"},
            ],
            "loinc": [
                {"code": "52741-7", "desc": "PSQI"}, {"code": "93832-4", "desc": "Sleep Duration"},
                {"code": "93831-6", "desc": "Sleep Efficiency"}, {"code": "44261-6", "desc": "PHQ-9"},
            ]
        },
    },
    {
        "lgp_id": "LGP-009",
        "name": "Mindfulness-Based Stress Reduction (MBSR)",
        "category": "Behavioral & Psychology",
        "description": "8-week program teaching mindfulness meditation to manage stress, reduce anxiety, and improve emotional well-being through present-moment awareness and acceptance.",
        "hallmarks_of_ageing": ["Altered Intercellular Communication", "Chronic Inflammation"],
        "evidence_level": "A",
        "hps_dimensions": ["CA", "SR", "BL"],
        "duration_default_weeks": 8,
        "interventions": [
            {"type": "Behavioral Therapy", "name": "MBSR Program", "details": "8 weeks; 2.5 hours/week group sessions plus full-day retreat. Body scan meditation, sitting meditation, mindful yoga, informal mindfulness practices."},
        ],
        "smart_goals_template": {
            "specific": "Develop and practice daily mindfulness meditation for at least 10 minutes.",
            "measurable": "Track daily meditation adherence and perceived stress levels.",
            "achievable": "Gradually increase meditation duration and integrate into daily activities.",
            "relevant": "Reduces stress, improves emotional regulation, enhances cognitive agility.",
            "time_bound": "Commit to 8-week program and establish consistent practice."
        },
        "codes": {
            "icd10": [
                {"code": "Z73.0", "desc": "Burnout"}, {"code": "F41.1", "desc": "Generalized anxiety disorder"},
            ],
            "loinc": [
                {"code": "69737-5", "desc": "GAD-7"}, {"code": "44261-6", "desc": "PHQ-9"},
                {"code": "80404-7", "desc": "HRV RMSSD"},
            ]
        },
    },
    {
        "lgp_id": "LGP-010",
        "name": "Vitamin D Optimisation Protocol",
        "category": "Supplementation",
        "description": "Achieve and maintain optimal serum 25-hydroxyvitamin D levels crucial for bone health, immune function, and numerous physiological processes linked to longevity.",
        "hallmarks_of_ageing": ["Genomic Instability"],
        "evidence_level": "A",
        "hps_dimensions": ["BR"],
        "duration_default_weeks": 12,
        "interventions": [
            {"type": "Supplementation", "name": "Vitamin D3 + K2", "details": "D3: 2000-5000 IU/day guided by serum levels. K2-MK7: 90-200 mcg/day for calcium regulation."},
        ],
        "smart_goals_template": {
            "specific": "Achieve and maintain serum 25(OH)D levels between 50-80 ng/mL.",
            "measurable": "Monitor via blood tests.",
            "achievable": "Adjust D3 dosage based on lab results.",
            "relevant": "Supports bone health, immune function, Biological Resilience.",
            "time_bound": "Reach target levels within 12 weeks, maintain thereafter."
        },
        "codes": {
            "icd10": [{"code": "E55.9", "desc": "Vitamin D deficiency, unspecified"}],
            "loinc": [{"code": "14771-0", "desc": "Vitamin D, 25-OH"}]
        },
    },
    {
        "lgp_id": "LGP-011",
        "name": "Omega-3 Fatty Acid Protocol",
        "category": "Supplementation",
        "description": "Optimize EPA and DHA omega-3 intake for anti-inflammatory, cardiovascular protective, and brain health benefits vital for longevity.",
        "hallmarks_of_ageing": ["Altered Intercellular Communication", "Chronic Inflammation"],
        "evidence_level": "A",
        "hps_dimensions": ["BR", "BL"],
        "duration_default_weeks": 16,
        "interventions": [
            {"type": "Supplementation", "name": "Omega-3 (EPA + DHA)", "details": "EPA + DHA: 3-5 g/day. Sources: fatty fish or high-quality fish oil/algal oil. Target Omega-3 Index > 8%."},
        ],
        "smart_goals_template": {
            "specific": "Achieve daily intake of 3-5g EPA and DHA.",
            "measurable": "Track intake via diet and supplements; monitor Omega-3 Index.",
            "achievable": "Use supplements and/or incorporate fatty fish regularly.",
            "relevant": "Reduces inflammation, supports cardiovascular and brain health.",
            "time_bound": "Maintain target intake for at least 16 weeks."
        },
        "codes": {
            "icd10": [{"code": "E78.5", "desc": "Hyperlipidemia"}],
            "loinc": [
                {"code": "2093-3", "desc": "Total Cholesterol"}, {"code": "2571-8", "desc": "Triglycerides"},
                {"code": "47920-4", "desc": "EPA in serum"},
            ]
        },
    },
    {
        "lgp_id": "LGP-012",
        "name": "NAD+ Precursor Supplementation (NMN/NR)",
        "category": "Supplementation",
        "description": "Supplement with NMN or NR to boost NAD+ levels — a crucial coenzyme for cellular energy production and DNA repair that declines with age.",
        "hallmarks_of_ageing": ["Loss of Proteostasis", "Mitochondrial Dysfunction"],
        "evidence_level": "B",
        "hps_dimensions": ["BR"],
        "duration_default_weeks": 12,
        "interventions": [
            {"type": "Supplementation", "name": "NAD+ Precursor", "details": "NMN: 250-1000 mg/day OR NR: 500-1000 mg/day. Morning dosing recommended."},
        ],
        "smart_goals_template": {
            "specific": "Take NMN or NR supplements daily as prescribed.",
            "measurable": "Track daily supplement adherence.",
            "achievable": "Consistent daily intake.",
            "relevant": "Supports cellular energy metabolism and DNA repair.",
            "time_bound": "Maintain supplementation for at least 12 weeks."
        },
        "codes": {
            "icd10": [{"code": "Z00.00", "desc": "Preventive general adult exam"}],
            "loinc": [{"code": "47920-4", "desc": "NAD+ levels (emerging)"}]
        },
    },
    {
        "lgp_id": "LGP-013",
        "name": "Cognitive Training Programme",
        "category": "Cognitive Health",
        "description": "Structured mentally stimulating activities to enhance memory, attention, processing speed, and executive function — crucial for maintaining cognitive agility throughout life.",
        "hallmarks_of_ageing": ["Epigenetic Alterations", "Altered Intercellular Communication"],
        "evidence_level": "B",
        "hps_dimensions": ["CA", "SR"],
        "duration_default_weeks": 16,
        "interventions": [
            {"type": "Cognitive Training", "name": "Cognitive Exercises", "details": "Dual-task exercises, memory training, attention exercises, cognitive games via AgeReboot app. Modules: memory, attention, processing speed, executive function."},
        ],
        "smart_goals_template": {
            "specific": "Engage in cognitive training for at least 20 minutes, 3 times per week.",
            "measurable": "Track session duration and frequency via app.",
            "achievable": "Integrate short, focused sessions into daily routine.",
            "relevant": "Improves Cognitive Agility and supports brain health.",
            "time_bound": "Adhere for minimum 16 weeks."
        },
        "codes": {
            "icd10": [{"code": "F06.70", "desc": "Mild cognitive impairment, unspecified"}],
            "loinc": [{"code": "72133-2", "desc": "MoCA"}]
        },
    },
    {
        "lgp_id": "LGP-014",
        "name": "Gut Microbiome Diversity Protocol",
        "category": "Gut Health",
        "description": "Foster a diverse, resilient gut microbiome through dietary and lifestyle interventions — recognizing its impact on immune function, metabolism, and brain health.",
        "hallmarks_of_ageing": ["Dysbiosis", "Altered Intercellular Communication"],
        "evidence_level": "B",
        "hps_dimensions": ["BR", "BL"],
        "duration_default_weeks": 16,
        "interventions": [
            {"type": "Dietary Intervention", "name": "Gut-Shaping Diet", "details": "> 30 different plant species/week. Daily fermented foods (yogurt, kefir, kimchi, sauerkraut). Diverse prebiotic fibres (inulin, FOS, GOS)."},
            {"type": "Supplementation", "name": "Targeted Probiotics", "details": "Strains: L. acidophilus, B. longum, B. infantis based on microbiome testing."},
        ],
        "smart_goals_template": {
            "specific": "Consume a wide variety of plant-based and fermented foods daily.",
            "measurable": "Track daily intake of different plant species and fermented foods.",
            "achievable": "Gradually introduce new plant foods and fermented options.",
            "relevant": "Improves gut health, immune function, metabolic regulation.",
            "time_bound": "Implement and maintain for at least 16 weeks."
        },
        "codes": {
            "icd10": [
                {"code": "K58.9", "desc": "Irritable bowel syndrome, unspecified"},
                {"code": "Z71.3", "desc": "Dietary counseling"},
            ],
            "loinc": [{"code": "416083000", "desc": "Microbiome composition (emerging)"}]
        },
    },
    {
        "lgp_id": "LGP-015",
        "name": "Hormonal Optimisation — Testosterone (Male)",
        "category": "Hormonal Health",
        "description": "Address suboptimal testosterone in men through lifestyle interventions, targeted supplementation, and physician-supervised HRT when necessary.",
        "hallmarks_of_ageing": ["Deregulated Nutrient Sensing"],
        "evidence_level": "B",
        "hps_dimensions": ["BR", "PF"],
        "duration_default_weeks": 16,
        "interventions": [
            {"type": "Lifestyle Intervention", "name": "Lifestyle Factors", "details": "Optimise sleep, reduce stress, incorporate resistance training (LGP-003) and Zone 2 cardio (LGP-002), maintain healthy body composition."},
            {"type": "Supplementation", "name": "Targeted Supplements", "details": "Zinc, Vitamin D, Magnesium, DHEA-S as indicated."},
            {"type": "Hormone Therapy", "name": "TRT (Physician-Prescribed)", "details": "Injections, gels, or patches prescribed by physician based on labs and symptomology."},
        ],
        "smart_goals_template": {
            "specific": "Achieve total testosterone > 400 ng/dL.",
            "measurable": "Monitor total and free testosterone via blood tests.",
            "achievable": "Combine lifestyle changes with physician-guided TRT if indicated.",
            "relevant": "Improves muscle mass, energy, mood, and sexual function.",
            "time_bound": "Achieve target levels within 12-16 weeks."
        },
        "codes": {
            "icd10": [{"code": "E29.1", "desc": "Testicular hypofunction"}],
            "loinc": [
                {"code": "2857-1", "desc": "Testosterone Total"}, {"code": "2990-0", "desc": "Testosterone Free"},
                {"code": "2191-5", "desc": "DHEA-S"},
            ]
        },
    },
    {
        "lgp_id": "LGP-016",
        "name": "Sauna + Cold Contrast Therapy",
        "category": "Recovery & Stress",
        "description": "Utilise physiological stresses of heat (sauna) and cold exposure to stimulate adaptive cardiovascular, recovery, and mitochondrial responses.",
        "hallmarks_of_ageing": ["Mitochondrial Dysfunction"],
        "evidence_level": "B",
        "hps_dimensions": ["SR", "BR"],
        "duration_default_weeks": 12,
        "interventions": [
            {"type": "Heat/Cold Exposure", "name": "Sauna + Cold Plunge", "details": "Alternate: 15-20 min sauna (80-100C) then 1-3 min cold water (10-15C). Multiple cycles per session, 3x/week."},
        ],
        "smart_goals_template": {
            "specific": "Complete 2-3 cycles of sauna + cold plunge per session, 3x/week.",
            "measurable": "Track session frequency and duration.",
            "achievable": "Gradually increase cold exposure duration.",
            "relevant": "Improves recovery, cardiovascular health, and resilience.",
            "time_bound": "Adhere for at least 12 weeks."
        },
        "codes": {
            "icd10": [{"code": "Z00.00", "desc": "Preventive general adult exam"}],
            "loinc": [
                {"code": "8867-4", "desc": "Resting Heart Rate"}, {"code": "80404-7", "desc": "HRV RMSSD"},
            ]
        },
    },
    {
        "lgp_id": "LGP-017",
        "name": "Probiotic Longevity Protocol",
        "category": "Gut Health",
        "description": "Specific probiotic strains to modulate the gut microbiome, improve gut barrier function, reduce inflammation, and support longevity.",
        "hallmarks_of_ageing": ["Dysbiosis", "Altered Intercellular Communication"],
        "evidence_level": "B",
        "hps_dimensions": ["BR", "BL"],
        "duration_default_weeks": 12,
        "interventions": [
            {"type": "Supplementation", "name": "Targeted Probiotic Strains", "details": "L. acidophilus, B. longum, B. infantis based on individual needs and microbiome assessment."},
        ],
        "smart_goals_template": {
            "specific": "Take prescribed probiotic supplements daily.",
            "measurable": "Track daily supplement adherence.",
            "achievable": "Consistent daily intake.",
            "relevant": "Enhances gut health and immune function.",
            "time_bound": "Maintain for at least 12 weeks."
        },
        "codes": {
            "icd10": [
                {"code": "K58.9", "desc": "IBS, unspecified"}, {"code": "Z71.3", "desc": "Dietary counseling"},
            ],
            "loinc": [{"code": "416083000", "desc": "Microbiome composition (emerging)"}]
        },
    },
    {
        "lgp_id": "LGP-018",
        "name": "Breathwork & HRV Biofeedback",
        "category": "Recovery & Stress",
        "description": "Controlled breathing techniques with HRV biofeedback to enhance parasympathetic tone, reduce stress, and improve emotional regulation and resilience.",
        "hallmarks_of_ageing": ["Altered Intercellular Communication", "Genomic Instability"],
        "evidence_level": "B",
        "hps_dimensions": ["SR", "CA"],
        "duration_default_weeks": 12,
        "interventions": [
            {"type": "Behavioral Therapy", "name": "Breathwork + HRV Biofeedback", "details": "Guided breathing exercises (diaphragmatic, box breathing). HRV biofeedback using device to promote heart-respiratory coherence. 15 min daily."},
        ],
        "smart_goals_template": {
            "specific": "Practice guided breathwork + HRV biofeedback for 15 minutes daily.",
            "measurable": "Track session frequency and HRV coherence scores.",
            "achievable": "Integrate into daily routine using app or device.",
            "relevant": "Reduces stress, improves emotional regulation and recovery.",
            "time_bound": "Commit to daily practice for at least 12 weeks."
        },
        "codes": {
            "icd10": [{"code": "F41.1", "desc": "Generalized anxiety disorder"}],
            "loinc": [
                {"code": "80404-7", "desc": "HRV RMSSD"}, {"code": "8867-4", "desc": "Resting Heart Rate"},
            ]
        },
    },
    {
        "lgp_id": "LGP-019",
        "name": "Anti-Ageing Supplement Stack (Evidence-Graded)",
        "category": "Supplementation",
        "description": "Curated supplement stack with evidence-graded anti-ageing benefits: antioxidants, mitochondrial support, DNA repair agents, and senolytics under physician supervision.",
        "hallmarks_of_ageing": ["Genomic Instability", "Telomere Attrition", "Epigenetic Alterations", "Loss of Proteostasis", "Mitochondrial Dysfunction", "Cellular Senescence"],
        "evidence_level": "B",
        "hps_dimensions": ["BR"],
        "duration_default_weeks": 52,
        "interventions": [
            {"type": "Supplementation", "name": "Multi-Supplement Protocol", "details": "May include: Resveratrol, Quercetin, CoQ10, PQQ, Alpha-Ketoglutarate, Spermidine, TA-65. Physician-supervised senolytics (Dasatinib + Quercetin) as indicated."},
        ],
        "smart_goals_template": {
            "specific": "Adhere to prescribed anti-ageing supplement regimen.",
            "measurable": "Track daily supplement adherence.",
            "achievable": "Consistent daily intake of recommended supplements.",
            "relevant": "Supports cellular repair mechanisms and metabolic processes.",
            "time_bound": "Maintain regimen as advised by physician."
        },
        "codes": {
            "icd10": [
                {"code": "Z00.00", "desc": "Preventive general adult exam"},
                {"code": "E55.9", "desc": "Vitamin D deficiency"},
            ],
            "loinc": [
                {"code": "30522-7", "desc": "hs-CRP"}, {"code": "98898-1", "desc": "Telomere Length"},
            ]
        },
    },
    {
        "lgp_id": "LGP-020",
        "name": "Longevity Social Connection Programme",
        "category": "Social & Lifestyle",
        "description": "Emphasizes the vital role of strong social connections in promoting mental, emotional, and physical health — contributing to increased lifespan and quality of life.",
        "hallmarks_of_ageing": ["Altered Intercellular Communication", "Epigenetic Alterations"],
        "evidence_level": "B",
        "hps_dimensions": ["BL", "CA"],
        "duration_default_weeks": 52,
        "interventions": [
            {"type": "Social Intervention", "name": "Social Engagement Activities", "details": "Participation in social groups, community events, family gatherings. Building meaningful relationships. Facilitated social events or introductions."},
        ],
        "smart_goals_template": {
            "specific": "Engage in at least one meaningful social interaction per week.",
            "measurable": "Track frequency and perceived quality of social interactions.",
            "achievable": "Actively seek opportunities for social connection.",
            "relevant": "Enhances Lifestyle Consistency and Cognitive Agility, reduces isolation.",
            "time_bound": "Maintain consistent social engagement long-term."
        },
        "codes": {
            "icd10": [{"code": "Z60.4", "desc": "Social isolation"}],
            "loinc": []
        },
    },
]

def seed_protocols():
    print("Clearing and seeding protocols with full parity data...")
    CCProtocol.objects.all().delete()
    
    clinician = User.objects.filter(email='clinical_admin@agereboot.com').first()
    member4 = User.objects.filter(username='member_04').first()
    member5 = User.objects.filter(username='member_05').first()

    if not clinician:
        print("Warning: Clinician 'clinical_admin@agereboot.com' not found.")
    
    created_protocols = []
    for p_data in LONGEVITY_PROTOCOLS:
        # Generate impact scores for the dimensions mentioned (legacy logic uses ~15-35 range)
        impacts = {dim: round(random.uniform(15, 35), 1) for dim in p_data["hps_dimensions"]}
        
        protocol = CCProtocol.objects.create(
            lgp_id=p_data["lgp_id"],
            name=p_data["name"],
            description=p_data["description"],
            category=p_data["category"],
            evidence_grade=p_data["evidence_level"],
            intervention_type=p_data["interventions"][0]["type"] if p_data["interventions"] else "",
            duration_default_weeks=p_data["duration_default_weeks"],
            hps_dimensions=p_data["hps_dimensions"],
            impact_scores=impacts,
            hallmarks_of_ageing=p_data["hallmarks_of_ageing"],
            codes=p_data.get("codes", {}),
            interventions=p_data.get("interventions", []),
            smart_goals_template=p_data["smart_goals_template"]
        )
        created_protocols.append(protocol)
        print(f"  Created Protocol: {protocol.lgp_id} - {protocol.name}")

    if clinician and member4 and member5:
        print("\nPrescribing protocols to member_04 and member_05...")
        CCPrescription.objects.filter(member__in=[member4, member5]).delete()

        # Prescribe 3 protocols to member4
        for p in random.sample(created_protocols, 3):
            CCPrescription.objects.create(
                member=member4,
                clinician=clinician,
                protocol=p,
                protocol_name=p.name,
                category=p.category,
                duration_weeks=p.duration_default_weeks,
                status="active"
            )
            print(f"  Prescribed {p.lgp_id} to member_04")

        # Prescribe 3 protocols to member5
        for p in random.sample(created_protocols, 3):
            CCPrescription.objects.create(
                member=member5,
                clinician=clinician,
                protocol=p,
                protocol_name=p.name,
                category=p.category,
                duration_weeks=p.duration_default_weeks,
                status="active"
            )
            print(f"  Prescribed {p.lgp_id} to member_05")

    print("\nFull protocol parity seeding complete.")

if __name__ == "__main__":
    seed_protocols()
