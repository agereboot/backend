"""
HPS Engine v3.2 — Cognitive Assessment (CA) Pillar Scoring
Implements the CA specification from AgeReboot_CA_Final_Specification_v3.2.

8 Mandatory Instruments:
  PHQ-9, GAD-7, PSS-10, MoCA, NP Battery, Digital RT, RS-14, SF-36 MCS

5 Conditional Instruments:
  MMSE, Brain MRI, Cortisol AM, GDS-15, PCL-5

Algorithm version: HPS_ENGINE_v3.2_CA
"""
from scipy import stats as scipy_stats

# === Instrument Weights (mandatory, sum = 1.00) ===
CA_MANDATORY_WEIGHTS = {
    "phq9": 0.18,
    "gad7": 0.13,
    "pss10": 0.12,
    "moca": 0.20,
    "np_battery": 0.15,
    "digital_rt": 0.08,
    "rs14": 0.06,
    "sf36_mcs": 0.08,
}

CA_CONDITIONAL_WEIGHTS = {
    "mmse": 0.15,
    "brain_mri": 0.12,
    "cortisol_am_cond": 0.10,
    "gds15": 0.10,
    "pcl5": 0.10,
}

# === PHQ-9 Clinical Percentile Map (NHANES prevalence-based) ===
# Raw 0-27 -> Percentile (higher = better, i.e. less depressed)
PHQ9_PERCENTILE_MAP = {
    0: 98, 1: 95, 2: 92, 3: 88, 4: 84,
    5: 78, 6: 73, 7: 68, 8: 63, 9: 58,
    10: 50, 11: 44, 12: 39, 13: 34, 14: 29,
    15: 24, 16: 20, 17: 17, 18: 14, 19: 11,
    20: 9, 21: 7, 22: 6, 23: 5, 24: 4,
    25: 3, 26: 2, 27: 1,
}

# === GAD-7 Clinical Percentile Map ===
GAD7_PERCENTILE_MAP = {
    0: 98, 1: 94, 2: 90, 3: 85, 4: 80,
    5: 73, 6: 67, 7: 61, 8: 55, 9: 49,
    10: 42, 11: 36, 12: 31, 13: 26, 14: 21,
    15: 17, 16: 13, 17: 10, 18: 7, 19: 5,
    20: 3, 21: 1,
}

# === MoCA Normative Data (age-sex stratified means and SDs) ===
MOCA_NORMS = {
    "M": {
        "20-29": (27.5, 1.8), "30-39": (27.2, 1.9), "40-49": (26.8, 2.0),
        "50-59": (26.3, 2.2), "60-69": (25.5, 2.5), "70+": (24.2, 2.8),
    },
    "F": {
        "20-29": (27.8, 1.7), "30-39": (27.4, 1.8), "40-49": (27.0, 2.0),
        "50-59": (26.5, 2.1), "60-69": (25.7, 2.4), "70+": (24.5, 2.7),
    },
}

# === MMSE Normative Data (Crum 1993 age-adjusted norms) ===
MMSE_NORMS = {
    "M": {
        "60-69": (28.0, 2.0), "70+": (26.5, 2.8),
    },
    "F": {
        "60-69": (28.2, 1.9), "70+": (26.8, 2.6),
    },
}

# === RS-14 Normative Data (Wagnild norms) ===
RS14_NORM_MEAN = 76.4
RS14_NORM_SD = 11.1

# === SF-36 MCS population norms ===
SF36_MCS_NORM_MEAN = 75.0
SF36_MCS_NORM_SD = 20.0

# === NP Battery sub-test normative data (age-sex stratified) ===
NP_BATTERY_NORMS = {
    "stroop": {
        "M": {"20-29": (50, 10), "30-39": (48, 11), "40-49": (45, 12), "50-59": (42, 13), "60-69": (38, 14), "70+": (34, 15)},
        "F": {"20-29": (51, 10), "30-39": (49, 11), "40-49": (46, 12), "50-59": (43, 13), "60-69": (39, 14), "70+": (35, 15)},
    },
    "trail_making_b": {
        "M": {"20-29": (75, 20), "30-39": (80, 22), "40-49": (88, 25), "50-59": (95, 28), "60-69": (105, 32), "70+": (120, 38)},
        "F": {"20-29": (78, 21), "30-39": (83, 23), "40-49": (90, 26), "50-59": (98, 29), "60-69": (108, 33), "70+": (125, 40)},
    },
    "n_back": {
        "M": {"20-29": (82, 10), "30-39": (79, 11), "40-49": (75, 12), "50-59": (70, 13), "60-69": (64, 14), "70+": (58, 15)},
        "F": {"20-29": (83, 10), "30-39": (80, 11), "40-49": (76, 12), "50-59": (71, 13), "60-69": (65, 14), "70+": (59, 15)},
    },
    "cpt": {
        "M": {"20-29": (90, 8), "30-39": (88, 9), "40-49": (85, 10), "50-59": (81, 11), "60-69": (76, 12), "70+": (70, 14)},
        "F": {"20-29": (91, 8), "30-39": (89, 9), "40-49": (86, 10), "50-59": (82, 11), "60-69": (77, 12), "70+": (71, 14)},
    },
    "symbol_digit": {
        "M": {"20-29": (58, 9), "30-39": (55, 10), "40-49": (51, 10), "50-59": (47, 11), "60-69": (42, 12), "70+": (37, 13)},
        "F": {"20-29": (60, 9), "30-39": (57, 10), "40-49": (53, 10), "50-59": (49, 11), "60-69": (44, 12), "70+": (39, 13)},
    },
}

# === Digital RT Normative Data (age-sex, lower RT = better) ===
DIGITAL_RT_NORMS = {
    "simple_rt": {
        "M": {"20-29": (260, 35), "30-39": (270, 38), "40-49": (285, 42), "50-59": (300, 48), "60-69": (320, 55), "70+": (350, 65)},
        "F": {"20-29": (270, 38), "30-39": (280, 40), "40-49": (295, 44), "50-59": (310, 50), "60-69": (330, 58), "70+": (360, 68)},
    },
    "choice_rt": {
        "M": {"20-29": (340, 45), "30-39": (355, 48), "40-49": (375, 52), "50-59": (400, 58), "60-69": (430, 65), "70+": (470, 75)},
        "F": {"20-29": (350, 48), "30-39": (365, 50), "40-49": (385, 55), "50-59": (410, 60), "60-69": (440, 68), "70+": (480, 78)},
    },
    "go_nogo": {
        "M": {"20-29": (380, 50), "30-39": (395, 53), "40-49": (415, 58), "50-59": (440, 63), "60-69": (470, 70), "70+": (510, 80)},
        "F": {"20-29": (390, 52), "30-39": (405, 55), "40-49": (425, 60), "50-59": (450, 65), "60-69": (480, 72), "70+": (520, 82)},
    },
}

NP_SUB_WEIGHTS = {"stroop": 0.25, "trail_making_b": 0.20, "n_back": 0.25, "cpt": 0.15, "symbol_digit": 0.15}
RT_SUB_WEIGHTS = {"simple_rt": 0.35, "choice_rt": 0.35, "go_nogo": 0.30}

# === Clinical Flag Thresholds ===
CLINICAL_FLAGS = {
    "phq9": {"GREEN": (0, 4), "YELLOW": (5, 9), "ORANGE": (10, 14), "RED": (15, 27)},
    "gad7": {"GREEN": (0, 4), "YELLOW": (5, 9), "ORANGE": (10, 14), "RED": (15, 21)},
    "pss10": {"GREEN": (0, 13), "YELLOW": (14, 19), "ORANGE": (20, 26), "RED": (27, 40)},
    "moca": {"GREEN": (26, 30), "YELLOW": (22, 25), "ORANGE": (18, 21), "RED": (0, 17)},
    "rs14": {"GREEN": (73, 98), "YELLOW": (57, 72), "ORANGE": (40, 56), "RED": (14, 39)},
}


def _get_age_band(age):
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


def _z_to_percentile(z):
    return max(1.0, min(99.0, scipy_stats.norm.cdf(z) * 100))


def _get_clinical_flag(instrument, raw_score):
    thresholds = CLINICAL_FLAGS.get(instrument)
    if not thresholds:
        return "GREEN"
    for level in ["RED", "ORANGE", "YELLOW", "GREEN"]:
        lo, hi = thresholds[level]
        if lo <= raw_score <= hi:
            return level
    return "GREEN"


# === Per-Instrument Scoring Functions ===

def score_phq9(raw):
    """PHQ-9: Clinical Percentile Map. Raw 0-27."""
    raw = max(0, min(27, int(raw)))
    return PHQ9_PERCENTILE_MAP.get(raw, 50.0)


def score_gad7(raw):
    """GAD-7: Clinical Percentile Map. Raw 0-21."""
    raw = max(0, min(21, int(raw)))
    return GAD7_PERCENTILE_MAP.get(raw, 50.0)


def score_pss10(raw):
    """PSS-10: Linear Inversion. Raw 0-40. P = 98 - (raw/40)*96, clipped [2,98]."""
    raw = max(0, min(40, float(raw)))
    p = 98.0 - (raw / 40.0) * 96.0
    return max(2.0, min(98.0, p))


def score_moca(raw, age, sex, education_years=16):
    """MoCA v8.3: Population Percentile via Z-score. Raw 0-30.
    Education correction: +1 if education_years <= 12 (capped at 30)."""
    raw = max(0, min(30, float(raw)))
    if education_years <= 12:
        raw = min(30, raw + 1)
    age_band = _get_age_band(age)
    sex_key = sex if sex in ("M", "F") else "M"
    mu, sigma = MOCA_NORMS[sex_key].get(age_band, (26.0, 2.2))
    if sigma == 0:
        sigma = 1.0
    z = (raw - mu) / sigma
    return _z_to_percentile(z)


def score_np_battery(sub_scores, age, sex):
    """NP Battery: Weighted average of sub-test Z-score percentiles.
    sub_scores: dict like {"stroop": 48, "trail_making_b": 82, "n_back": 78, "cpt": 88, "symbol_digit": 52}
    For trail_making_b: lower is better (time in seconds)."""
    age_band = _get_age_band(age)
    sex_key = sex if sex in ("M", "F") else "M"
    weighted_sum = 0.0
    weight_sum = 0.0
    for test, score_val in sub_scores.items():
        if test not in NP_SUB_WEIGHTS or test not in NP_BATTERY_NORMS:
            continue
        mu, sigma = NP_BATTERY_NORMS[test][sex_key].get(age_band, (50, 12))
        if sigma == 0:
            sigma = 1.0
        if test == "trail_making_b":
            z = (mu - score_val) / sigma
        else:
            z = (score_val - mu) / sigma
        p = _z_to_percentile(z)
        w = NP_SUB_WEIGHTS[test]
        weighted_sum += p * w
        weight_sum += w
    return weighted_sum / weight_sum if weight_sum > 0 else 50.0


def score_digital_rt(sub_scores, age, sex):
    """Digital RT: Weighted average of sub-test Z-score percentiles.
    Lower RT = better, so Z is inverted.
    sub_scores: dict like {"simple_rt": 265, "choice_rt": 350, "go_nogo": 400}"""
    age_band = _get_age_band(age)
    sex_key = sex if sex in ("M", "F") else "M"
    weighted_sum = 0.0
    weight_sum = 0.0
    for test, rt_val in sub_scores.items():
        if test not in RT_SUB_WEIGHTS or test not in DIGITAL_RT_NORMS:
            continue
        mu, sigma = DIGITAL_RT_NORMS[test][sex_key].get(age_band, (300, 50))
        if sigma == 0:
            sigma = 1.0
        z = (mu - rt_val) / sigma
        p = _z_to_percentile(z)
        w = RT_SUB_WEIGHTS[test]
        weighted_sum += p * w
        weight_sum += w
    return weighted_sum / weight_sum if weight_sum > 0 else 50.0


def score_rs14(raw):
    """RS-14: Population Percentile via Z-score against Wagnild norms. Raw 14-98."""
    raw = max(14, min(98, float(raw)))
    z = (raw - RS14_NORM_MEAN) / RS14_NORM_SD
    return _z_to_percentile(z)


def score_sf36_mcs(item_sum):
    """SF-36 MCS: Domain Aggregation + Linear Normalisation.
    item_sum: sum of 6 mental component items (each scored 0-5), range 0-30.
    Normalise to 0-100, then Z-score against population norms."""
    item_sum = max(0, min(30, float(item_sum)))
    norm_0_100 = (item_sum / 30.0) * 100.0
    z = (norm_0_100 - SF36_MCS_NORM_MEAN) / SF36_MCS_NORM_SD
    return _z_to_percentile(z)


def score_mmse(raw, age, sex):
    """MMSE: Population Percentile via Z-score (Crum 1993 norms). Conditional."""
    raw = max(0, min(30, float(raw)))
    age_band = _get_age_band(age)
    sex_key = sex if sex in ("M", "F") else "M"
    norms = MMSE_NORMS.get(sex_key, {})
    mu, sigma = norms.get(age_band, norms.get("70+", (27.0, 2.5)))
    if sigma == 0:
        sigma = 1.0
    z = (raw - mu) / sigma
    return _z_to_percentile(z)


# === Coverage Confidence Multiplier ===

def compute_ccm(present_count, total_mandatory=8):
    """CCM based on coverage ratio of present mandatory instruments."""
    cr = present_count / total_mandatory
    if cr > 0.70:
        return 1.00
    elif cr >= 0.40:
        return 0.95
    return 0.90


# === Composite CA Score ===

def compute_ca_score(ca_data, age, sex, education_years=16):
    """
    Compute the full Cognitive Assessment pillar score.

    ca_data: dict with keys from CA_MANDATORY_WEIGHTS + optional conditional keys.
      Example:
      {
        "phq9": 4,                  # raw score
        "gad7": 3,                  # raw score
        "pss10": 12,                # raw score
        "moca": 27,                 # raw score
        "np_battery": {"stroop": 48, "trail_making_b": 82, ...},  # sub-scores
        "digital_rt": {"simple_rt": 265, "choice_rt": 350, ...},  # sub-scores (ms)
        "rs14": 78,                 # raw score
        "sf36_mcs": 22,             # sum of 6 mental items (0-30)
        # Conditional:
        "mmse": 28,                 # raw (triggered if age>=60 or moca<24)
      }

    Returns dict with composite score, HPS contribution, instrument details, flags.
    """
    instrument_scores = {}
    clinical_flags = {}

    # Score each mandatory instrument if present
    if "phq9" in ca_data and ca_data["phq9"] is not None:
        raw = ca_data["phq9"]
        instrument_scores["phq9"] = score_phq9(raw)
        clinical_flags["phq9"] = _get_clinical_flag("phq9", raw)

    if "gad7" in ca_data and ca_data["gad7"] is not None:
        raw = ca_data["gad7"]
        instrument_scores["gad7"] = score_gad7(raw)
        clinical_flags["gad7"] = _get_clinical_flag("gad7", raw)

    if "pss10" in ca_data and ca_data["pss10"] is not None:
        raw = ca_data["pss10"]
        instrument_scores["pss10"] = score_pss10(raw)
        clinical_flags["pss10"] = _get_clinical_flag("pss10", raw)

    if "moca" in ca_data and ca_data["moca"] is not None:
        raw = ca_data["moca"]
        instrument_scores["moca"] = score_moca(raw, age, sex, education_years)
        clinical_flags["moca"] = _get_clinical_flag("moca", raw)

    if "np_battery" in ca_data and ca_data["np_battery"]:
        instrument_scores["np_battery"] = score_np_battery(ca_data["np_battery"], age, sex)

    if "digital_rt" in ca_data and ca_data["digital_rt"]:
        instrument_scores["digital_rt"] = score_digital_rt(ca_data["digital_rt"], age, sex)

    if "rs14" in ca_data and ca_data["rs14"] is not None:
        raw = ca_data["rs14"]
        instrument_scores["rs14"] = score_rs14(raw)
        clinical_flags["rs14"] = _get_clinical_flag("rs14", raw)

    if "sf36_mcs" in ca_data and ca_data["sf36_mcs"] is not None:
        instrument_scores["sf36_mcs"] = score_sf36_mcs(ca_data["sf36_mcs"])

    # Handle conditional instruments
    conditional_scores = {}
    moca_raw = ca_data.get("moca")
    should_trigger_mmse = (age >= 60) or (moca_raw is not None and moca_raw < 24)

    if "mmse" in ca_data and ca_data["mmse"] is not None and should_trigger_mmse:
        conditional_scores["mmse"] = score_mmse(ca_data["mmse"], age, sex)

    # Compute coverage-weighted composite from mandatory instruments
    present_mandatory = {k: v for k, v in instrument_scores.items() if k in CA_MANDATORY_WEIGHTS}
    present_count = len(present_mandatory)

    if present_count == 0:
        return {
            "ca_composite": 0.0,
            "hps_cognitive": 0.0,
            "ccm": 0.90,
            "instrument_scores": {},
            "clinical_flags": {},
            "present_count": 0,
            "total_mandatory": 8,
            "ca_band": "SEVERE",
        }

    # Coverage-weighted average
    weighted_sum = sum(
        present_mandatory[k] * CA_MANDATORY_WEIGHTS[k]
        for k in present_mandatory
    )
    weight_sum = sum(CA_MANDATORY_WEIGHTS[k] for k in present_mandatory)
    c_ca = weighted_sum / weight_sum if weight_sum > 0 else 0.0

    # CCM
    ccm = compute_ccm(present_count)

    # HPS Cognitive contribution: C_CA * CCM * 1.50 -> [0, 150]
    hps_cognitive = min(150.0, c_ca * ccm * 1.50)

    # Clinical band
    if c_ca >= 90:
        ca_band = "ELITE"
    elif c_ca >= 75:
        ca_band = "HIGH"
    elif c_ca >= 60:
        ca_band = "GOOD"
    elif c_ca >= 45:
        ca_band = "MILD"
    elif c_ca >= 30:
        ca_band = "MODERATE"
    else:
        ca_band = "SEVERE"

    # Cross-instrument alerts
    alerts = []
    phq9_raw = ca_data.get("phq9")
    gad7_raw = ca_data.get("gad7")
    if phq9_raw is not None and gad7_raw is not None:
        if phq9_raw >= 10 and gad7_raw >= 10:
            alerts.append({"level": "HIGH", "message": "PHQ-9 and GAD-7 both elevated — mandatory clinical referral"})

    if moca_raw is not None and moca_raw < 18:
        alerts.append({"level": "HIGH", "message": "MoCA < 18 — lock score, notify care team, recommend neuropsych eval"})

    pss_raw = ca_data.get("pss10")
    if phq9_raw is not None and phq9_raw > 14 and pss_raw is not None and pss_raw > 26:
        alerts.append({"level": "HIGH", "message": "PHQ-9 > 14 + PSS > 26 — clinician referral + cortisol ordered"})

    rs14_raw = ca_data.get("rs14")
    if rs14_raw is not None and phq9_raw is not None:
        if rs14_raw < 40 and phq9_raw >= 10:
            alerts.append({"level": "MEDIUM", "message": "Low resilience + elevated depression — mental health coach recommended"})

    return {
        "ca_composite": round(c_ca, 1),
        "hps_cognitive": round(hps_cognitive, 1),
        "ccm": ccm,
        "instrument_scores": {k: round(v, 1) for k, v in instrument_scores.items()},
        "conditional_scores": {k: round(v, 1) for k, v in conditional_scores.items()},
        "clinical_flags": clinical_flags,
        "cross_alerts": alerts,
        "present_count": present_count,
        "total_mandatory": 8,
        "ca_band": ca_band,
    }
