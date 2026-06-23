import numpy as np

def calculate_credit_score(revenue_data: dict, risk_data: dict, runway_data: dict) -> dict:
    """
    Calculates a credit risk score from 100 down to 0 using an absolute 
    deduction penalty matrix based on underlying banking metrics.
    """
    score = 100.0
    penalties = {}

    # --- 1. NSF EVENTS PENALTY MATRIX (Max Deduct: 35) ---
    nsf_count = risk_data["risk_assessment"]["nsf_count"]
    if nsf_count == 0:
        nsf_deduction = 0
    elif 1 <= nsf_count <= 2:
        nsf_deduction = 15
    elif 3 <= nsf_count <= 4:
        nsf_deduction = 25
    else:  # 5+ NSFs
        nsf_deduction = 35
    
    score -= nsf_deduction
    penalties["nsf_events_penalty"] = -nsf_deduction

    # --- 2. STRESSED RUNWAY PENALTY MATRIX (Max Deduct: 25) ---
    stressed_runway = runway_data["stress_test_metrics"]["stressed_runway_months"]
    if stressed_runway >= 6.0:
        runway_deduction = 0
    elif 3.0 <= stressed_runway < 6.0:
        runway_deduction = 8
    elif 1.0 <= stressed_runway < 3.0:
        runway_deduction = 16
    else:  # < 1 Month
        runway_deduction = 25

    score -= runway_deduction
    penalties["stressed_runway_penalty"] = -runway_deduction

    # --- 3. NEGATIVE CASHFLOW MONTHS PENALTY MATRIX (Max Deduct: 20) ---
    # Extract net monthly flows from the timeline to see how many months are negative
    timeline = revenue_data.get("timeline", [])
    neg_months_count = sum(1 for month in timeline if month.get("net_flow", 0) < 0)
    
    if neg_months_count == 0:
        cashflow_deduction = 0
    elif neg_months_count == 1:
        cashflow_deduction = 7
    elif neg_months_count == 2:
        cashflow_deduction = 13
    else:  # 3+ Months
        cashflow_deduction = 20

    score -= cashflow_deduction
    penalties["negative_cashflow_months_penalty"] = -cashflow_deduction

    # --- 4. SUSTAINED LOW BALANCE PENALTY MATRIX (Max Deduct: 10) ---
    # Captures risk if the minimum balance drops below a threshold or if low balance days count spikes
    low_balance_days = risk_data["risk_assessment"]["low_balance_days_count"]
    min_balance = risk_data["risk_assessment"]["minimum_recorded_balance"]
    
    # Trigger if they actively spent time below a 5,000 baseline or if absolute minimum is critically low
    if low_balance_days >= 2 or min_balance < 5000:
        low_balance_deduction = 10
    elif low_balance_days == 1:
        low_balance_deduction = 5
    else:
        low_balance_deduction = 0

    score -= low_balance_deduction
    penalties["low_balance_cushion_penalty"] = -low_balance_deduction

    # --- 5. LATE/SKIPPED SALARY PAYMENTS MATRIX (Weighted Heavily - Max Deduct: 30) ---
    # Weight distribution: Skipped months are absolute auto-fails, late months are highly penalized.
    salary_report = risk_data.get("late_salaries_report", {})
    total_skipped = salary_report.get("total_skipped_months", 0)
    total_late = salary_report.get("total_late_months", 0)
    
    salary_deduction = 0
    if total_skipped > 0:
        salary_deduction += 20  # Immediate massive penalty for missing a full payroll cycle
    if total_late >= 2:
        salary_deduction += 10
    elif total_late == 1:
        salary_deduction += 5
        
    # Cap salary penalty to 30 max points to avoid dropping total score beneath structural zero bound
    salary_deduction = min(30, salary_deduction)
    score -= salary_deduction
    penalties["payroll_stress_penalty"] = -salary_deduction

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
