"""
HPS Engine v3.0 — AgeReboot Longevity Roadmap Generator
Uses Claude Sonnet for personalized roadmap narratives.
"""
import os
import logging
import math
from .normative import PILLAR_CONFIG, BIOMARKER_DEFINITIONS

logger = logging.getLogger(__name__)

PILLAR_ICONS = {
    "BR": "heart-pulse",
    "PF": "dumbbell",
    "CA": "brain",
    "SR": "moon",
    "BL": "shield-check",
}

PILLAR_COLORS = {
    "BR": "#EF4444",
    "PF": "#0F9F8F",
    "CA": "#6366F1",
    "SR": "#8B5CF6",
    "BL": "#D97706",
}

# Comprehensive intervention library with credits, priority, and categories
INTERVENTION_LIBRARY = [
    # PHYSICAL FITNESS
    {"id": "pf-zone2", "pillar": "PF", "domain": "Physical Fitness", "type": "medical",
     "intervention": "Zone 2 Cardio Protocol (45 min, 3-4x/wk, 60-70% HRmax)",
     "evidence": "Grade A (Coyle 1984; Seiler 2010)", "hps_delta": "+20-40", "duration": "12-16 weeks",
     "contra": "Uncontrolled HTN (SBP>180); recent cardiac event (<6m)",
     "priority": "must_do", "credits": 0, "category": "exercise"},
    {"id": "pf-resistance", "pillar": "PF", "domain": "Physical Fitness", "type": "medical",
     "intervention": "Progressive Resistance Training (3x/wk, compound lifts)",
     "evidence": "Grade A (Peterson JAMA 2011)", "hps_delta": "+15-30", "duration": "16+ weeks",
     "contra": "Acute musculoskeletal injury; fracture risk",
     "priority": "must_do", "credits": 0, "category": "exercise"},
    {"id": "pf-vo2", "pillar": "PF", "domain": "Physical Fitness", "type": "medical",
     "intervention": "VO2 Max Testing & Coaching Session",
     "evidence": "Grade A", "hps_delta": "+10-20", "duration": "Single session + follow-up",
     "contra": "None", "priority": "good_to_do", "credits": 150, "category": "assessment"},

    # BIOMARKER RECOVERY
    {"id": "br-med-diet", "pillar": "BR", "domain": "Metabolic Health", "type": "nutraceutical",
     "intervention": "Mediterranean Diet (PREDIMED protocol)",
     "evidence": "Grade A (Estruch NEJM 2018)", "hps_delta": "+25-45", "duration": "8-16 weeks",
     "contra": "None at population level",
     "priority": "must_do", "credits": 0, "category": "nutrition"},
    {"id": "br-tre", "pillar": "BR", "domain": "Metabolic Health", "type": "medical",
     "intervention": "Time-Restricted Eating (16:8 TRE)",
     "evidence": "Grade B (Sutton Cell Metab 2018)", "hps_delta": "+15-25", "duration": "8+ weeks",
     "contra": "T1DM; eating disorder history",
     "priority": "good_to_do", "credits": 0, "category": "nutrition"},
    {"id": "br-vitd", "pillar": "BR", "domain": "Supplementation", "type": "nutraceutical",
     "intervention": "Vitamin D3 + K2 Supplementation (5000 IU D3 + 100 mcg K2/day)",
     "evidence": "Grade A (Heaney 2003; Holick NEJM 2007)", "hps_delta": "+15-30", "duration": "8-12 weeks",
     "contra": "Hypercalcaemia; sarcoidosis",
     "priority": "must_do", "credits": 25, "category": "supplement"},
    {"id": "br-omega3", "pillar": "BR", "domain": "Supplementation", "type": "nutraceutical",
     "intervention": "Omega-3 (3g EPA+DHA/day, pharmaceutical grade)",
     "evidence": "Grade A (Mozaffarian NEJM 2011)", "hps_delta": "+10-20", "duration": "8-16 weeks",
     "contra": "Fish allergy; anticoagulant therapy",
     "priority": "must_do", "credits": 30, "category": "supplement"},
    {"id": "br-nmn", "pillar": "BR", "domain": "Supplementation", "type": "nutraceutical",
     "intervention": "NMN (Nicotinamide Mononucleotide) 500mg/day",
     "evidence": "Grade B (Yoshino Science 2021)", "hps_delta": "+10-15", "duration": "12+ weeks",
     "contra": "Limited long-term safety data",
     "priority": "good_to_do", "credits": 75, "category": "supplement"},
    {"id": "br-metformin", "pillar": "BR", "domain": "Pharmaceutical", "type": "pharmaceutical",
     "intervention": "Metformin Off-Label (500mg-1000mg/day, with physician oversight)",
     "evidence": "Grade B (TAME Trial ongoing; Bannister 2014)", "hps_delta": "+10-25", "duration": "Ongoing",
     "contra": "Renal impairment (eGFR<30); lactic acidosis risk",
     "priority": "good_to_do", "credits": 200, "category": "prescription"},
    {"id": "br-rapamycin", "pillar": "BR", "domain": "Pharmaceutical", "type": "pharmaceutical",
     "intervention": "Low-Dose Rapamycin (Sirolimus 3-5mg/wk, clinician-supervised)",
     "evidence": "Grade C (Mannick Sci Translational Med 2014)", "hps_delta": "+10-20", "duration": "Ongoing",
     "contra": "Immunocompromised; organ transplant; active infection",
     "priority": "good_to_do", "credits": 350, "category": "prescription"},
    {"id": "br-hrv", "pillar": "BR", "domain": "Recovery", "type": "medical",
     "intervention": "HRV Biofeedback Training (resonance breathing 0.1 Hz)",
     "evidence": "Grade B (Lehrer 2014)", "hps_delta": "+15-25", "duration": "4-8 weeks",
     "contra": "Caution in arrhythmia",
     "priority": "good_to_do", "credits": 100, "category": "therapy"},
    {"id": "br-bloodwork", "pillar": "BR", "domain": "Diagnostics", "type": "medical",
     "intervention": "Comprehensive Longevity Blood Panel (80+ biomarkers)",
     "evidence": "Grade A", "hps_delta": "+5-10 (via data)", "duration": "Quarterly",
     "contra": "None",
     "priority": "must_do", "credits": 200, "category": "lab_test"},

    # SLEEP & RECOVERY
    {"id": "sr-cbti", "pillar": "SR", "domain": "Sleep", "type": "medical",
     "intervention": "CBT-I Lite (digital stimulus control + sleep restriction)",
     "evidence": "Grade A (Walker 2017; AASM 2021)", "hps_delta": "+20-35", "duration": "6-8 weeks",
     "contra": "None",
     "priority": "must_do", "credits": 80, "category": "therapy"},
    {"id": "sr-magnesium", "pillar": "SR", "domain": "Supplementation", "type": "nutraceutical",
     "intervention": "Magnesium Glycinate 400mg (evening dose)",
     "evidence": "Grade B (Abbasi 2012)", "hps_delta": "+5-15", "duration": "4-8 weeks",
     "contra": "Renal impairment",
     "priority": "good_to_do", "credits": 15, "category": "supplement"},
    {"id": "sr-sleep-study", "pillar": "SR", "domain": "Diagnostics", "type": "medical",
     "intervention": "Home Sleep Apnea Test (HSAT) + Polysomnography if indicated",
     "evidence": "Grade A", "hps_delta": "+15-40 (if treated)", "duration": "1-2 weeks",
     "contra": "None",
     "priority": "must_do", "credits": 250, "category": "lab_test"},

    # COGNITIVE ACUITY
    {"id": "ca-dual-nback", "pillar": "CA", "domain": "Cognitive", "type": "medical",
     "intervention": "Dual N-Back Training (30 min, 5x/wk)",
     "evidence": "Grade B (Jaeggi PNAS 2008)", "hps_delta": "+15-25", "duration": "12-24 weeks",
     "contra": "None",
     "priority": "good_to_do", "credits": 0, "category": "exercise"},
    {"id": "ca-lions-mane", "pillar": "CA", "domain": "Supplementation", "type": "nutraceutical",
     "intervention": "Lion's Mane Mushroom Extract (1000mg/day)",
     "evidence": "Grade B (Mori 2009)", "hps_delta": "+5-15", "duration": "8+ weeks",
     "contra": "Mushroom allergy",
     "priority": "good_to_do", "credits": 30, "category": "supplement"},
    {"id": "ca-neuro-assessment", "pillar": "CA", "domain": "Diagnostics", "type": "medical",
     "intervention": "Comprehensive Neurocognitive Assessment Battery",
     "evidence": "Grade A", "hps_delta": "+5-10 (via data)", "duration": "Single session",
     "contra": "None",
     "priority": "must_do", "credits": 180, "category": "assessment"},

    # BODY & LONGEVITY
    {"id": "bl-smoking", "pillar": "BL", "domain": "Behaviour", "type": "medical",
     "intervention": "Smoking Cessation (NRT + behavioural support)",
     "evidence": "Grade A (Cochrane 2022)", "hps_delta": "+40-80", "duration": "Ongoing",
     "contra": "None",
     "priority": "must_do", "credits": 0, "category": "lifestyle"},
    {"id": "bl-dexa", "pillar": "BL", "domain": "Diagnostics", "type": "medical",
     "intervention": "DEXA Body Composition + Visceral Fat Analysis",
     "evidence": "Grade A", "hps_delta": "+5-10 (via data)", "duration": "Single scan",
     "contra": "Pregnancy",
     "priority": "must_do", "credits": 120, "category": "lab_test"},
    {"id": "bl-telomere", "pillar": "BL", "domain": "Diagnostics", "type": "medical",
     "intervention": "Telomere Length + Epigenetic Clock (GrimAge) Testing",
     "evidence": "Grade B (Horvath 2013)", "hps_delta": "+5 (via data)", "duration": "Single test",
     "contra": "None",
     "priority": "good_to_do", "credits": 300, "category": "lab_test"},
    {"id": "bl-resveratrol", "pillar": "BL", "domain": "Supplementation", "type": "nutraceutical",
     "intervention": "Trans-Resveratrol 500mg/day (with quercetin co-factor)",
     "evidence": "Grade C (Baur Nature 2006)", "hps_delta": "+5-10", "duration": "12+ weeks",
     "contra": "Anticoagulant therapy; estrogen-sensitive conditions",
     "priority": "good_to_do", "credits": 40, "category": "supplement"},
]

FEASIBILITY_COEFFICIENTS = {
    "BR": 0.82, "PF": 0.75, "CA": 0.65, "SR": 0.72, "BL": 0.70,
}


def compute_priority_gaps(pillar_results):
    """Priority Gap Analysis: GAP(d) = (Target - Current) x Feasibility_CF"""
    gaps = []
    for code, data in pillar_results.items():
        target = 75.0
        current = data["percentage"]
        feasibility = FEASIBILITY_COEFFICIENTS.get(code, 0.7)
        gap_score = (target - current) * feasibility
        gaps.append({
            "pillar_code": code,
            "pillar_name": data["name"],
            "current_pct": current,
            "target_pct": target,
            "gap_score": round(gap_score, 1),
            "feasibility": feasibility,
            "icon": PILLAR_ICONS.get(code, "activity"),
            "color": PILLAR_COLORS.get(code, "#7B35D8"),
        })
    gaps.sort(key=lambda x: x["gap_score"], reverse=True)
    return gaps


def select_interventions(gaps, pillar_results, managed_conditions=None):
    """Select interventions per pillar, tagged must_do/good_to_do, with credits."""
    conditions = set(c.lower() for c in (managed_conditions or []))
    pillar_interventions = {}

    for gap in gaps:
        code = gap["pillar_code"]
        candidates = [i for i in INTERVENTION_LIBRARY if i["pillar"] == code]
        safe = []
        for iv in candidates:
            contra_lower = iv["contra"].lower()
            is_safe = all(cond not in contra_lower for cond in conditions)
            if is_safe:
                safe.append({
                    "id": iv["id"],
                    "intervention": iv["intervention"],
                    "type": iv["type"],
                    "category": iv["category"],
                    "evidence": iv["evidence"],
                    "hps_delta": iv["hps_delta"],
                    "duration": iv["duration"],
                    "contra": iv["contra"],
                    "priority": iv["priority"],
                    "credits": iv["credits"],
                    "pillar_code": code,
                    "pillar_name": gap["pillar_name"],
                })
        pillar_interventions[code] = safe

    return pillar_interventions


def estimate_biological_age(hps_score, chronological_age, sex="M"):
    """Estimate biological age from HPS score using logarithmic regression model."""
    # Higher HPS = younger biological age
    # At HPS=500 (median), bio_age ≈ chrono_age
    # At HPS=1000, bio_age ≈ chrono_age - 15
    # At HPS=0, bio_age ≈ chrono_age + 10
    offset = -15.0 * (hps_score / 1000.0) + 10.0 * (1 - hps_score / 1000.0)
    bio_age = max(18, chronological_age + offset)
    return round(bio_age, 1)


def predict_biological_age_trajectory(hps_score, chronological_age, interventions_selected, sex="M"):
    """Predict biological age trajectory over 12 months with selected interventions."""
    current_bio_age = estimate_biological_age(hps_score, chronological_age, sex)

    # Estimate cumulative HPS gain from selected interventions
    total_delta_low = 0
    total_delta_high = 0
    for iv in interventions_selected:
        delta_str = iv.get("hps_delta", "+0")
        parts = delta_str.replace("+", "").split("-")
        try:
            low = int(parts[0].strip().split(" ")[0])
            high = int(parts[-1].strip().split(" ")[0]) if len(parts) > 1 else low
        except (ValueError, IndexError):
            low, high = 5, 15
        total_delta_low += low
        total_delta_high += high

    # Conservative estimate
    avg_delta = (total_delta_low + total_delta_high) / 2
    projected_hps = min(1000, hps_score + avg_delta)

    trajectory = []
    for month in range(0, 13):
        # Logarithmic improvement curve
        if month == 0:
            month_hps = hps_score
        else:
            progress = math.log(month + 1) / math.log(13)
            month_hps = hps_score + avg_delta * progress

        month_hps = min(1000, month_hps)
        chrono = chronological_age + (month / 12)
        bio = estimate_biological_age(month_hps, chrono, sex)
        trajectory.append({
            "month": month,
            "hps": round(month_hps),
            "chronological_age": round(chrono, 1),
            "biological_age": round(bio, 1),
            "age_gap": round(chrono - bio, 1),
        })

    return {
        "current_biological_age": current_bio_age,
        "current_chronological_age": chronological_age,
        "projected_biological_age_12m": trajectory[-1]["biological_age"],
        "projected_hps_12m": round(projected_hps),
        "max_age_gap_achievable": trajectory[-1]["age_gap"],
        "trajectory": trajectory,
    }


# Keep backward compat
def select_protocols(gaps, managed_conditions=None):
    """Legacy protocol selection."""
    selected = []
    for gap in gaps[:3]:
        code = gap["pillar_code"]
        candidates = [i for i in INTERVENTION_LIBRARY if i["pillar"] == code and i["priority"] == "must_do"]
        if candidates:
            p = candidates[0]
            selected.append({
                "domain": p["domain"], "protocol": p["intervention"], "evidence": p["evidence"],
                "delta": p["hps_delta"], "duration": p["duration"], "contra": p["contra"],
                "priority_pillar": gap["pillar_name"], "gap_score": gap["gap_score"]
            })
    return selected


async def generate_ai_roadmap(hps_result, user_profile):
    """Generate personalized longevity roadmap using Claude AI"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return _generate_fallback_roadmap(hps_result, user_profile)

        gaps = compute_priority_gaps(hps_result["pillars"])
        interventions = select_interventions(gaps, hps_result["pillars"], user_profile.get("managed_conditions"))
        protocols = select_protocols(gaps, user_profile.get("managed_conditions"))

        # Flatten all interventions for the prompt
        all_ivs = []
        for code, ivs in interventions.items():
            all_ivs.extend(ivs)

        age = user_profile.get('age', 35)
        sex = user_profile.get('sex', 'M')
        bio_age_data = predict_biological_age_trajectory(
            hps_result['hps_final'], age, all_ivs, sex
        )

        prompt = f"""You are the AgeReboot Health Performance Coach. Generate a personalized longevity roadmap briefing.

ATHLETE PROFILE:
- Age: {age}, Sex: {sex}
- HPS: {hps_result['hps_final']}/1000 ({hps_result['tier']['tier']})
- Biological Age Estimate: {bio_age_data['current_biological_age']} (chrono: {age})
- Confidence Interval: ±{hps_result['confidence_interval']} pts ({hps_result['n_metrics_tested']} metrics)
- Managed Conditions: {', '.join(user_profile.get('managed_conditions', [])) or 'None'}

PILLAR BREAKDOWN:
{chr(10).join(f"- {v['name']}: {v['score']}/{v['max_points']} pts ({v['percentage']}%)" for v in hps_result['pillars'].values())}

TOP PRIORITY GAPS:
{chr(10).join(f"- {g['pillar_name']}: Gap Score {g['gap_score']} (Current {g['current_pct']}% → Target {g['target_pct']}%)" for g in gaps[:3])}

Write a concise performance briefing (300-400 words) with:
1. Current status assessment
2. Key risk areas and opportunities
3. 12-month outlook with projected biological age improvement
4. Top 3 immediate actions

Use competitive, data-precise language. No wellness platitudes. This is a performance briefing."""

        chat = LlmChat(
            api_key=api_key,
            session_id=f"roadmap-{user_profile.get('id', 'unknown')}",
            system_message="You are the AgeReboot longevity performance coach. Speak with precision, competitive urgency, and scientific authority."
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")

        response = await chat.send_message(UserMessage(text=prompt))
        return {
            "ai_narrative": response,
            "gaps": gaps,
            "protocols": protocols,
            "interventions": interventions,
            "biological_age": bio_age_data,
            "generated": True,
        }
    except Exception as e:
        logger.error(f"AI roadmap generation failed: {e}")
        return _generate_fallback_roadmap(hps_result, user_profile)


def _generate_fallback_roadmap(hps_result, user_profile):
    """Algorithmic fallback roadmap without AI"""
    gaps = compute_priority_gaps(hps_result["pillars"])
    interventions = select_interventions(gaps, hps_result["pillars"], user_profile.get("managed_conditions"))
    protocols = select_protocols(gaps, user_profile.get("managed_conditions"))

    age = user_profile.get('age', 35)
    sex = user_profile.get('sex', 'M')

    all_ivs = []
    for code, ivs in interventions.items():
        all_ivs.extend(ivs)

    bio_age_data = predict_biological_age_trajectory(
        hps_result['hps_final'], age, all_ivs, sex
    )

    phases = [
        {"phase": "Phase 0 — Baseline", "timeline": "Days 1-14", "objective": "Complete onboarding and establish full baseline",
         "target_delta": "0 (baseline only)", "actions": ["Complete full core biomarker panel", "Set up wearable device integration", "Complete cognitive baseline assessment", "Establish HPS baseline with confidence interval"]},
        {"phase": "Phase 1 — Foundation", "timeline": "Days 15-90", "objective": "Build sleep, nutrition, and basic movement habits",
         "target_delta": "+30-60 pts", "actions": ["Implement sleep hygiene protocol", "Begin Mediterranean diet framework", "Start Zone 2 cardio (3x/week)", "Initiate Vitamin D + Omega-3 supplementation"]},
        {"phase": "Phase 2 — Performance", "timeline": "Days 91-180", "objective": "Layer physical and metabolic optimisation",
         "target_delta": "+50-90 pts", "actions": ["Progressive resistance training programme", "HRV biofeedback integration", "Cognitive training protocol", "6-month lab panel + body composition"]},
        {"phase": "Phase 3 — Optimisation", "timeline": "Days 181-365", "objective": "Advanced protocol stack and competition readiness",
         "target_delta": "+80-130 pts", "actions": ["Advanced supplement protocol", "Stress mastery programme", "Competition entry preparation", "Annual comprehensive biomarker review"]},
    ]

    return {
        "ai_narrative": None,
        "gaps": gaps,
        "protocols": protocols,
        "interventions": interventions,
        "biological_age": bio_age_data,
        "phases": phases,
        "generated": False,
    }
