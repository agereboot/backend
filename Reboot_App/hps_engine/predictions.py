"""
HPS Engine v3.0 — ML Prediction Layer
Simple trajectory prediction using linear regression.
"""
import numpy as np
from datetime import datetime, timezone, timedelta


def predict_hps_trajectory(history_scores, prediction_days=180):
    """
    Predict future HPS trajectory using weighted linear regression.
    Returns predicted HPS values at 30/90/180 day marks.
    """
    if not history_scores or len(history_scores) < 2:
        return None

    # Convert to time-series arrays
    timestamps = []
    scores = []
    for h in sorted(history_scores, key=lambda x: x.get("timestamp", "")):
        try:
            ts = datetime.fromisoformat(h["timestamp"].replace("Z", "+00:00"))
            timestamps.append(ts.timestamp())
            scores.append(h["hps_final"])
        except (ValueError, KeyError):
            continue

    if len(timestamps) < 2:
        return None

    x = np.array(timestamps)
    y = np.array(scores)

    # Normalize x to days from first measurement
    x_days = (x - x[0]) / 86400.0

    # Weighted linear regression (recent data weighted more)
    n = len(x_days)
    weights = np.linspace(0.5, 1.5, n)

    # Weighted least squares
    W = np.diag(weights)
    X = np.column_stack([np.ones(n), x_days])
    XtWX = X.T @ W @ X
    XtWy = X.T @ W @ y

    try:
        beta = np.linalg.solve(XtWX, XtWy)
    except np.linalg.LinAlgError:
        return None

    intercept, slope = beta[0], beta[1]

    # Predict at future points
    current_day = x_days[-1]
    predictions = []
    for days_ahead in [30, 90, 180]:
        future_day = current_day + days_ahead
        predicted = max(0, min(1000, intercept + slope * future_day))
        predictions.append({
            "days_ahead": days_ahead,
            "predicted_hps": round(predicted, 1),
            "date": (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat(),
        })

    # Compute trend metrics
    daily_change = slope
    monthly_change = slope * 30
    current_hps = y[-1]
    days_to_next_tier = None

    tier_thresholds = [250, 400, 550, 700, 850]
    if daily_change > 0:
        for threshold in tier_thresholds:
            if current_hps < threshold:
                days_needed = (threshold - current_hps) / daily_change
                days_to_next_tier = round(days_needed)
                break

    # R-squared for confidence
    y_pred = intercept + slope * x_days
    ss_res = np.sum(weights * (y - y_pred) ** 2)
    ss_tot = np.sum(weights * (y - np.average(y, weights=weights)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return {
        "predictions": predictions,
        "trend": {
            "daily_change": round(daily_change, 3),
            "monthly_change": round(monthly_change, 1),
            "direction": "improving" if daily_change > 0.05 else "declining" if daily_change < -0.05 else "stable",
            "r_squared": round(max(0, r_squared), 3),
            "confidence": "high" if r_squared > 0.7 else "moderate" if r_squared > 0.4 else "low",
        },
        "days_to_next_tier": days_to_next_tier,
        "data_points": len(timestamps),
    }


def compute_franchise_roi(avg_hps, member_count, avg_healthcare_cost_per_employee=8500):
    """
    Compute estimated ROI for franchise based on HPS levels.
    Based on WHO/ILO research: 10% HPS improvement → 3.4% healthcare cost reduction.
    Reference: Tata Group example from spec (34% reduction at 100% improvement).
    """
    # Baseline: avg HPS of 500 = no cost reduction
    # For each 100 HPS above 500 → 6.8% reduction
    hps_above_baseline = max(0, avg_hps - 400)
    reduction_pct = min(40, hps_above_baseline * 0.068)  # Cap at 40%

    annual_savings_per_employee = avg_healthcare_cost_per_employee * (reduction_pct / 100)
    total_savings = annual_savings_per_employee * member_count

    # Productivity gains: 10 HPS = 0.5% productivity gain
    productivity_gain_pct = min(15, hps_above_baseline * 0.05)

    # Absenteeism reduction: Higher HPS = fewer sick days
    avg_sick_days_baseline = 12
    sick_days_reduction = min(8, hps_above_baseline * 0.015)
    days_saved = sick_days_reduction * member_count

    return {
        "healthcare_cost_reduction_pct": round(reduction_pct, 1),
        "annual_savings_per_employee": round(annual_savings_per_employee),
        "total_annual_savings": round(total_savings),
        "productivity_gain_pct": round(productivity_gain_pct, 1),
        "sick_days_saved_total": round(days_saved),
        "sick_days_saved_per_employee": round(sick_days_reduction, 1),
        "roi_multiplier": round(total_savings / max(1, member_count * 500), 1),  # vs $500/yr program cost
        "avg_healthcare_cost_assumed": avg_healthcare_cost_per_employee,
        "member_count": member_count,
    }
