import io
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import pandas as pd

# Import your existing analytics functions
from parser.csv_parser import clean_csv  # Using clean_csv directly on the in-memory dataframe
from analyzer.revenue import analyze_revenue
from analyzer.risk_flags import detect_risk_flags
from analyzer.runway import calculate_stressed_runway

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

app = FastAPI(
    title="SME Credit Underwriting Engine",
    description="Automated transaction stream analysis and stress testing service"
)

# --- Dynamic Risk Scoring Model ---
def compute_stress_profile(rev_data: dict, risk_data: dict, runway_data: dict) -> tuple[int, str, str]:
    """
    Computes an analytical stress score (0-100) and forward risk view
    based on behavioral markers and financial cushions.
    """
    score = 0
    reasons = []
    
    # 1. Critical Hard Flags (NSF Events)
    nsf_count = risk_data["risk_assessment"]["nsf_count"]
    if nsf_count > 0:
        score += min(nsf_count * 20, 40)  # Max out at 40 points for NSF
        reasons.append(f"Detected {nsf_count} structural NSF/bounced payment events")
        
    # 2. Structural Capital Drift (Negative Months)
    negative_months = sum(1 for m in rev_data["timeline"] if m["net_flow"] < 0)
    if negative_months > 0:
        score += min(negative_months * 15, 30)
        reasons.append(f"Account registered {negative_months} months of negative net cashflow")
        
    # 3. Capital Volatility (Coefficient of Inflow Variation)
    cv_in = rev_data.get("coefficient_of_inflow_variation", 0.0)
    if cv_in > 0.5:
        score += 15
        reasons.append("High top-line revenue volatility detected")
        
    # 4. Burn Rate Runway Threat (Stressed Environment)
    stressed_runway = runway_data["stress_test_metrics"]["stressed_runway_months"]
    if stressed_runway == 999.0:
        pass  # Cash positive
    elif stressed_runway < 2.0:
        score += 15
        reasons.append("Stressed runway falls below critical 2-month survival threshold")
    elif stressed_runway < 4.0:
        score += 10
        reasons.append("Moderate runway exhaustion threat under 30% revenue shock")
        
    # Cap the final integer limits
    stress_score = min(max(score, 0), 100)
    
    # 5. Determine Forward Risk View & Mapping
    if stress_score >= 70 or nsf_count > 3:
        forward_view = "decline"
    elif stress_score >= 45:
        forward_view = "high_risk"
    elif stress_score >= 20:
        forward_view = "moderate_risk"
    else:
        forward_view = "low_risk"
        
    # Synthesize the exact one-sentence justification
    if not reasons:
        justification = "The profile demonstrates exceptional cash generation stability, a secure liquidity cushion, and no operational stress markers."
    else:
        justification = f"Risk assessment driven by: {'; '.join(reasons)}."
        
    return stress_score, forward_view, justification


# --- API Endpoint Definition ---
@app.post("/analyse")
async def analyse_statement(file: UploadFile = File(...)):
    # Defensive extension filtering
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a standard CSV text file.")
        
    try:
        # Read file contents directly into an memory stream (avoids local disk writes)
        contents = await file.read()
        raw_df = pd.read_csv(io.BytesIO(contents))
        
        # 1. Clean and transform the dataframe in memory
        clean_df = clean_csv(raw_df)
        
        if clean_df.empty:
            raise HTTPException(status_code=422, detail="The provided transaction stream contains no valid historical records after data isolation.")
            
        # 2. Run the pipeline modules
        revenue_analysis = analyze_revenue(clean_df)
        risk_flag_analysis = detect_risk_flags(clean_df)
        runway_analysis = calculate_stressed_runway(clean_df)
        
        # 3. Compute underwriting rules dynamically
        stress_score, forward_view, justification = compute_stress_profile(
            revenue_analysis, risk_flag_analysis, runway_analysis
        )
        # 4. Generate the precise stress indicators list requested
        detected_indicators = []
        if risk_flag_analysis["risk_assessment"]["nsf_count"] > 0:
            detected_indicators.append("Bounced / Returned Payments Detected")
            
        negative_months = [m["month"] for m in revenue_analysis["timeline"] if m["net_flow"] < 0]
        if negative_months:
            detected_indicators.append(f"Negative Net Cashflow Months: {', '.join(negative_months)}")
            
        if risk_flag_analysis["risk_assessment"]["low_balance_days_count"] > 3:
            detected_indicators.append("Sustained Low-Balance Periods (Risk Threshold Breached)")
            
        # Build the final contract payload
        #
        return {
            "monthly_timeline": revenue_analysis["timeline"],
            "stress_indicators": detected_indicators if detected_indicators else ["No stress indicators triggered"],
            "stress_score": stress_score,
            "forward_view": forward_view,
            "justification": justification
        }
        
    except Exception as e:
        logging.error(f"Internal API Execution Fault: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during statement ingestion or structural parsing.")
