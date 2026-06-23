import pandas as pd

def analyze_revenue(df: pd.DataFrame):
    inflows = df[df['amount'] > 0].copy()
    
    if inflows.empty:
        return {"total_revenue": 0.0, "monthly_average": 0.0, "confidence_score": "Low"}
        
    total_revenue = float(inflows['amount'].sum())
    print(inflows['date']) 

    # Group by month using the index/date
    inflows['month'] = inflows['date'].dt.to_period('M')
    monthly_sums = inflows.groupby('month')['amount'].sum()
    
    # Coefficient of Variation (Standard Deviation / Mean)
    monthly_mean = monthly_sums.mean()
    monthly_std = monthly_sums.std() if len(monthly_sums) > 1 else 0.0
    cv = (monthly_std / monthly_mean) if monthly_mean > 0 else 999.0
    
    return {
        "total_revenue_detected": total_revenue,
        "average_monthly_revenue": float(monthly_mean),
        "coefficient_of_variation": round(cv, 3)
    }
