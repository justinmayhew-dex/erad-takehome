import pandas as pd

def calculate_stressed_runway(df: pd.DataFrame) -> dict:
    """
    Evaluates cash longevity by calculating baseline monthly cash dynamics 
    and projecting structural survival metrics under a 30% revenue shock.
    """
    # 1. Grab current cash position (the final recorded closing balance)
    current_balance = float(df['balance_after'].iloc[-1]) if not df.empty else 0.0
    
    # 2. Extract monthly dynamics using period casting
    df_copy = df.copy()
    df_copy['month'] = df_copy['date'].dt.to_period('M')
    
    # Inflows (Gross revenue baseline)
    inflows = df_copy[df_copy['amount'] > 0]
    monthly_inflows = inflows.groupby('month')['amount'].sum()
    avg_monthly_inflow = float(monthly_inflows.mean()) if not monthly_inflows.empty else 0.0
    
    # Outflows (Operational expenses baseline)
    outflows = df_copy[df_copy['amount'] < 0]
    monthly_outflows = outflows.groupby('month')['amount'].sum().abs()
    avg_monthly_outflow = float(monthly_outflows.mean()) if not monthly_outflows.empty else 0.0
    
    # 3. Baseline Net Burn Rate (Normal state)
    baseline_net_burn = avg_monthly_outflow - avg_monthly_inflow
    
    if baseline_net_burn <= 0:
        # Company is organically cash flow positive under normal conditions
        baseline_runway_months = 999.0  
    else:
        baseline_runway_months = round(current_balance / baseline_net_burn, 2)
        
    # Apply a structural 30% top-line revenue haircut
    stressed_inflow = avg_monthly_inflow * 0.70
    stressed_net_burn = avg_monthly_outflow - stressed_inflow
    
    if stressed_net_burn <= 0:
        stressed_runway_months = 999.0
    else:
        stressed_runway_months = round(current_balance / stressed_net_burn, 2)
        
    return {
        "cash_position": {
            "current_ending_balance": current_balance,
            "average_monthly_inflow": round(avg_monthly_inflow, 2),
            "average_monthly_outflow": round(avg_monthly_outflow, 2)
        },
        "baseline_metrics": {
            "net_monthly_burn": round(baseline_net_burn, 2),
            "runway_months": baseline_runway_months
        },
        "stress_test_metrics": {
            "revenue_shock_pct": 30.0,
            "stressed_net_monthly_burn": round(stressed_net_burn, 2),
            "stressed_runway_months": stressed_runway_months,
            "runway_reduction_months": None if baseline_runway_months == 999.0 else round(max(0, baseline_runway_months - stressed_runway_months), 2)
        }
    }
