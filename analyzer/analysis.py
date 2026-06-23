import numpy as np

def calculate_credit_score(revenue_data: dict, risk_data: dict, runway_data: dict) -> dict:
    """
    Calculates a credit risk score from 100 down to 0 using an absolute 
    deduction penalty matrix based on underlying banking metrics.
    """
    score = 0.0
    penalties = {}

    # --- 1. NSF EVENTS PENALTY MATRIX (Max Deduct: 35) ---
    nsf_count = risk_data["risk_assessment"]["nsf_count"]
    if nsf_count == 0:
        nsf_score = 25
    elif 1 <= nsf_count <= 2:
        nsf_score = 15
    elif 3 <= nsf_count <= 4:
        nsf_score = 5
    else:  # 5+ NSFs
        nsf_score = 0
    
    score += nsf_score
    penalties["nsf_events_penalty"] = 25 - nsf_score

    # --- 2. STRESSED RUNWAY PENALTY MATRIX (Max Deduct: 25) ---
    stressed_runway = runway_data["stress_test_metrics"]["stressed_runway_months"]
    if stressed_runway >= 6.0:
        runway_score = 20
    elif 3.0 <= stressed_runway < 6.0:
        runway_score = 14
    elif 1.0 <= stressed_runway < 3.0:
        runway_score = 7
    else:  # < 1 Month
        runway_score = 0

    score += runway_score
    penalties["stressed_runway_penalty"] = 20 - runway_score

    # --- 3. NEGATIVE CASHFLOW MONTHS PENALTY MATRIX (Max Deduct: 20) ---
    # Extract net monthly flows from the timeline to see how many months are negative
    timeline = revenue_data.get("timeline", [])
    neg_months_count = sum(1 for month in timeline if month.get("net_flow", 0) < 0)
    
    if neg_months_count == 0:
        cashflow_score = 15
    elif neg_months_count == 1:
        cashflow_score = 10
    elif neg_months_count == 2:
        cashflow_score = 5
    else:  # 3+ Months
        cashflow_score = 0

    score += cashflow_score
    penalties["negative_cashflow_months_penalty"] = 15 - cashflow_score

    # --- 4. SUSTAINED LOW BALANCE PENALTY MATRIX (Max Deduct: 10) ---
    # Captures risk if the minimum balance drops below a threshold or if low balance days count spikes
    low_balance_days = risk_data["risk_assessment"]["low_balance_days_count"]
    min_balance = risk_data["risk_assessment"]["minimum_recorded_balance"]
    
    # Trigger if they actively spent time below a 5,000 baseline or if absolute minimum is critically low
    if low_balance_days >= 2 or min_balance < 5000:
        low_balance_score = 0
    elif low_balance_days == 1:
        low_balance_score = 5
    else:
        low_balance_score = 10

    score += low_balance_score
    penalties["low_balance_cushion_penalty"] = 10 - low_balance_score

    # --- 5. LATE/SKIPPED SALARY PAYMENTS MATRIX (Weighted Heavily - Max Deduct: 30) ---
    # Weight distribution: Skipped months are absolute auto-fails, late months are highly penalized.
    salary_report = risk_data.get("late_salaries_report", {})
    total_skipped = salary_report.get("total_skipped_months", 0)
    total_late = salary_report.get("total_late_months", 0)
    
    salary_score = 30
    if total_skipped > 0:
        salary_score -= 20  # Immediate massive penalty for missing a full payroll cycle
    if total_late >= 2:
        salary_score -= 10
    elif total_late == 1:
        salary_score -= 5
        
    # Cap salary penalty to 30 max points to avoid dropping total score beneath structural zero bound
    score += salary_score
    penalties["payroll_stress_penalty"] = 30 - salary_score

    # --- FINAL SCORE BOUNDING ---
    final_score = max(0.0, min(100.0, score))
    
    # Assign Credit Grade
    if final_score >= 80:
        grade = "low_risk"
    elif final_score >= 60:
        grade = "moderate_risk"
    elif final_score >= 40:
        grade = "high_risk"
    else:
        grade = "decline"

    return {
        "credit_score_summary": {
            "final_score": round(final_score, 1),
            "assigned_grade": grade,
            "underlying_risk_signals": {
                "detected_nsf_events": nsf_count,
                "negative_cashflow_months": neg_months_count,
                "payroll_anomalies_detected": total_skipped + total_late,
                "current_stressed_runway_months": stressed_runway
            }
        },
        "penalty_breakdown_ledger": penalties
    }
