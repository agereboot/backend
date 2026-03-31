"""
HPS Engine v3.2 — 9-Step Scoring Algorithm + CA Pillar
Implements the complete HPS computation pipeline with the
Cognitive Assessment (CA) specification v3.2.
"""
import math
from scipy import stats as scipy_stats
from .normative import BIOMARKER_DEFINITIONS, PILLAR_CONFIG, get_normative
from .questionnaire_scoring import compute_ca_score


def step1_percentile_score(value, biomarker_code, age, sex):
    """Step 1: Age-Sex-Adjusted Percentile Score P(m,i)"""
    defn = BIOMARKER_DEFINITIONS.get(biomarker_code)
    if not defn:
        return 50.0
    mu, sigma = get_normative(biomarker_code, age, sex)
    if sigma == 0:
        sigma = 1.0
    direction = defn["direction"]

    if direction == "higher_better":
        z = (value - mu) / sigma
        p = scipy_stats.norm.cdf(z) * 100
    elif direction == "lower_better":
        z = (value - mu) / sigma
        p = (1 - scipy_stats.norm.cdf(z)) * 100
    elif direction == "optimal_range":
        opt_center = (defn["optimal_low"] + defn["optimal_high"]) / 2
        sigma_range = (defn["optimal_high"] - defn["optimal_low"]) / 2
        if sigma_range == 0:
            sigma_range = 1.0
        d = abs(value - opt_center) / sigma_range
        p = max(0, 100 - 50 * d * d)
    else:
        p = 50.0

    return min(100.0, max(0.0, p))


def step2_bias_correction(percentile, age, sex, ethnicity="ALL", managed_conditions=None):
    """Step 2: Multi-Factor Bias Correction (delta1-delta6)"""
    delta = 0.0
    # delta1: ethnicity correction (simplified)
    ethnicity_adj = {"SOUTH_ASIAN": 2.0, "EAST_ASIAN": 1.0, "AFRICAN": 1.5, "HISPANIC": 1.0, "ALL": 0.0}
    delta += ethnicity_adj.get(ethnicity, 0.0)

    # delta3: HSBC - managed disease correction
    if managed_conditions:
        delta += len(managed_conditions) * 3.0

    adjusted = min(100.0, max(0.0, percentile + delta))
    return adjusted


def step3_pillar_weighted_score(biomarker_scores, pillar_code):
    """Step 3: Coverage-weighted pillar score"""
    pillar_metrics = {k: v for k, v in BIOMARKER_DEFINITIONS.items() if v["pillar"] == pillar_code}
    tested = {}
    for code, defn in pillar_metrics.items():
        if code in biomarker_scores:
            tested[code] = (biomarker_scores[code], defn["weight"])

    if not tested:
        return 0.0, 0.0

    weighted_sum = sum(score * weight for score, weight in tested.values())
    weight_sum = sum(weight for _, weight in tested.values())
    coverage = len(tested) / max(len(pillar_metrics), 1)

    return weighted_sum / weight_sum if weight_sum > 0 else 0.0, coverage


def step4_scale_to_max(pillar_score_pct, pillar_code):
    """Step 4: Scale pillar score to max points"""
    max_pts = PILLAR_CONFIG[pillar_code]["max_points"]
    return (pillar_score_pct / 100.0) * max_pts


def step5_coverage_confidence_multiplier(coverage_ratio):
    """Step 5: CCM based on total coverage"""
    if coverage_ratio >= 0.70:
        return 1.00
    elif coverage_ratio >= 0.50:
        return 0.95
    return 0.90


def step6_improvement_bonus(current_values, prior_values):
    """Step 6: Improvement Bonus from delta tracked metrics"""
    if not prior_values:
        return 0.0
    deltas = []
    for code, curr in current_values.items():
        if code in prior_values and prior_values[code] != 0:
            defn = BIOMARKER_DEFINITIONS.get(code)
            if not defn:
                continue
            if defn["direction"] == "lower_better":
                d = (prior_values[code] - curr) / abs(prior_values[code]) * 100
            else:
                d = (curr - prior_values[code]) / abs(prior_values[code]) * 100
            deltas.append(d)

    if not deltas:
        return 0.0
    avg_delta = sum(deltas) / len(deltas)

    if avg_delta >= 30:
        return 60
    elif avg_delta >= 20:
        return 40
    elif avg_delta >= 10:
        return 20
    elif avg_delta >= 5:
        return 10
    return 0


def step7_compliance_multiplier(adherence_pct):
    """Step 7: Compliance Multiplier"""
    if adherence_pct >= 90:
        return 1.05
    elif adherence_pct >= 75:
        return 1.03
    elif adherence_pct >= 50:
        return 1.00
    return 0.95


def step9_confidence_interval(n_metrics):
    """Step 9: Confidence Interval CI = +/- k / sqrt(|T|)"""
    k = 150
    if n_metrics <= 0:
        return 150
    return round(k / math.sqrt(n_metrics), 1)


def get_performance_tier(hps):
    """Map HPS to longevity-themed performance tier (Dopamine Architecture v1.0)"""
    if hps >= 800:
        return {"tier": "CENTENARIAN", "color": "#D97706", "description": "Peak biological optimization — on track for 100+", "level": 7, "next_threshold": 1000}
    elif hps >= 750:
        return {"tier": "MASTERY", "color": "#A855F7", "description": "Elite health mastery across all domains", "level": 6, "next_threshold": 800}
    elif hps >= 700:
        return {"tier": "RESILIENCE", "color": "#0F9F8F", "description": "High resilience — biological age reversed", "level": 5, "next_threshold": 750}
    elif hps >= 600:
        return {"tier": "LONGEVITY", "color": "#4F46E5", "description": "Longevity pathway activated — qualified performer", "level": 4, "next_threshold": 700}
    elif hps >= 450:
        return {"tier": "VITALITY", "color": "#7B35D8", "description": "Building vitality — momentum growing", "level": 3, "next_threshold": 600}
    elif hps >= 300:
        return {"tier": "FOUNDATION", "color": "#F59E0B", "description": "Establishing health foundation", "level": 2, "next_threshold": 450}
    return {"tier": "AWAKENING", "color": "#EF4444", "description": "Health journey begins — every step counts", "level": 1, "next_threshold": 300}


def get_alert_level(pillar_scores):
    """Cross-System Alert Logic"""
    below_40 = [p for p, score in pillar_scores.items() if score < 40]
    below_20 = [p for p, score in pillar_scores.items() if score < 20]

    if below_20:
        return {"level": "RED", "message": f"Clinical priority: {', '.join(below_20)} in pathological zone", "color": "#EF4444"}
    if len(below_40) >= 2:
        return {"level": "ORANGE", "message": f"Cross-system ageing: {', '.join(below_40)} below threshold", "color": "#F97316"}
    if below_40:
        return {"level": "YELLOW", "message": f"Watch: {', '.join(below_40)} needs attention", "color": "#EAB308"}
    return {"level": "GREEN", "message": "All systems healthy", "color": "#10B981"}


def compute_hps(biomarker_data, age, sex, ethnicity="ALL", managed_conditions=None,
                prior_values=None, adherence_pct=75, ca_data=None,
                education_years=16):
    """
    Complete 9-Step HPS Computation Pipeline (v3.2 with CA Pillar)
    Returns full breakdown with pillar scores, final HPS, CI, and alerts.

    ca_data: optional dict with Cognitive Assessment instrument scores.
    """
    # Step 1 & 2: Percentile + bias correction per metric
    adjusted_scores = {}
    for code, value in biomarker_data.items():
        if code not in BIOMARKER_DEFINITIONS:
            continue
        raw_pct = step1_percentile_score(value, code, age, sex)
        adj_pct = step2_bias_correction(raw_pct, age, sex, ethnicity, managed_conditions)
        adjusted_scores[code] = adj_pct

    # Steps 3-4: Pillar scores
    pillar_results = {}
    total_coverage_metrics = 0
    total_possible_metrics = 0
    hps_base = 0.0
    pillar_pct_scores = {}

    for pillar_code, config in PILLAR_CONFIG.items():
        # CA pillar: use dedicated questionnaire scoring if ca_data provided
        if pillar_code == "CA" and ca_data:
            ca_result = compute_ca_score(ca_data, age, sex, education_years)
            ca_pct = ca_result["ca_composite"]
            ca_scaled = ca_result["hps_cognitive"]
            ca_present = ca_result["present_count"]
            ca_total = ca_result["total_mandatory"]

            total_coverage_metrics += ca_present
            total_possible_metrics += ca_total

            pillar_results[pillar_code] = {
                "name": config["name"],
                "score": round(ca_scaled, 1),
                "max_points": config["max_points"],
                "percentage": round(ca_pct, 1),
                "coverage": round((ca_present / max(ca_total, 1)) * 100, 1),
                "color": config["color"],
                "metrics_tested": ca_present,
                "metrics_total": ca_total,
                "ca_detail": {
                    "instrument_scores": ca_result.get("instrument_scores", {}),
                    "clinical_flags": ca_result.get("clinical_flags", {}),
                    "cross_alerts": ca_result.get("cross_alerts", []),
                    "ca_band": ca_result.get("ca_band", ""),
                    "ccm": ca_result.get("ccm", 1.0),
                },
            }
            pillar_pct_scores[pillar_code] = ca_pct
            hps_base += ca_scaled
            continue

        # Standard pillar scoring for non-CA pillars (and CA fallback)
        pct_score, coverage = step3_pillar_weighted_score(adjusted_scores, pillar_code)
        scaled = step4_scale_to_max(pct_score, pillar_code)

        pillar_metrics_count = len([v for v in BIOMARKER_DEFINITIONS.values() if v["pillar"] == pillar_code])
        tested_count = len([k for k, v in BIOMARKER_DEFINITIONS.items() if v["pillar"] == pillar_code and k in adjusted_scores])

        total_coverage_metrics += tested_count
        total_possible_metrics += pillar_metrics_count

        pillar_results[pillar_code] = {
            "name": config["name"],
            "score": round(scaled, 1),
            "max_points": config["max_points"],
            "percentage": round(pct_score, 1),
            "coverage": round(coverage * 100, 1),
            "color": config["color"],
            "metrics_tested": tested_count,
            "metrics_total": pillar_metrics_count,
        }
        pillar_pct_scores[pillar_code] = pct_score
        hps_base += scaled

    # Step 5: CCM
    coverage_ratio = total_coverage_metrics / max(total_possible_metrics, 1)
    ccm = step5_coverage_confidence_multiplier(coverage_ratio)
    hps_base *= ccm

    # Step 6: Improvement Bonus
    ib = step6_improvement_bonus(biomarker_data, prior_values) if prior_values else 0

    # Step 7: Compliance Multiplier
    cm = step7_compliance_multiplier(adherence_pct)

    # Step 8: Final HPS
    hps_final = min(1000, (hps_base + ib) * cm)

    # Step 9: Confidence Interval
    n_metrics = len(adjusted_scores) + (ca_data and 1 or 0)
    ci = step9_confidence_interval(n_metrics)

    # Alert logic
    alert = get_alert_level(pillar_pct_scores)
    tier = get_performance_tier(hps_final)

    return {
        "hps_final": round(hps_final, 1),
        "hps_base": round(hps_base, 1),
        "pillars": pillar_results,
        "improvement_bonus": ib,
        "compliance_multiplier": cm,
        "coverage_ratio": round(coverage_ratio, 3),
        "ccm": ccm,
        "confidence_interval": ci,
        "n_metrics_tested": n_metrics,
        "tier": tier,
        "alert": alert,
        "algorithm_version": "HPS_ENGINE_v3.2.1_CA",
        "metric_scores": {k: round(v, 1) for k, v in adjusted_scores.items()},
    }
