import pandas as pd

def analyze_revenue(df: pd.DataFrame):
    outflows = df[df['amount'] < 0].copy()
    inflows = df[df['amount'] > 0].copy()
    
    if outflows.empty:
        return {"total_inflows": 0.0, "total_outflows": 0.0, "monthly_average": 0.0, "confidence_score": "Low"}
    if inflows.empty:
        return {"total_inflows": 0.0, "total_outflows": 0.0, "monthly_average": 0.0, "confidence_score": "Low"}
        
    total_inflows = float(inflows['amount'].sum())
    total_outflows = float(outflows['amount'].sum())

    print(inflows['date']) 

    # Group by month using the index/date
    inflows['month'] = inflows['date'].dt.to_period('M')
    monthly_inflows = inflows.groupby('month')['amount'].sum()

    outflows['month'] = outflows['date'].dt.to_period('M')
    monthly_outflows = outflows.groupby('month')['amount'].sum()

    # Coefficient of Variation (Standard Deviation / Mean)
    monthly_mean_in = monthly_inflows.mean()
    monthly_std_in = monthly_inflows.std() if len(monthly_inflows) > 1 else 0.0

    monthly_mean_out = monthly_outflows.mean()
    monthly_std_out = monthly_outflows.std() if len(monthly_outflows) > 1 else 0.0

    cv_in = (monthly_std_in / monthly_mean_in) if monthly_mean_in > 0 else 999.0
    
    abs_mean_out = abs(monthly_mean_out)
    cv_out = (monthly_std_out / abs_mean_out) if abs_mean_out > 0 else 999.0
    

    return {
        "total_inflows": total_inflows,
        "total_outflows": total_outflows,
        "average_monthly_inflow": float(monthly_mean_in),
        "average_monthly_outflow": float(monthly_mean_out),
        "coefficient_of_inflow_variation": round(cv_in, 3),
        "coefficient_of_outflow_variation": round(cv_out, 3)
    }
