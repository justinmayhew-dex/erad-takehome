import pandas as pd

def detect_risk_flags(df: pd.DataFrame, low_balance_threshold: float = 5000.0) -> dict:
    # 1. Isolate strict credit risk events (NSF/Bounced)
    nsf_keywords = ['nsf', 'insufficient', 'returned', 'bounced', 'unpaid', 'overdraft']
    nsf_pattern = '|'.join(nsf_keywords)
    
    # Filter case-insensitive match on description
    nsf_df = df[df['description'].str.contains(nsf_pattern, case=False, na=False)].copy()
    # Deduplicate
    nsf_df = nsf_df[~nsf_df['description'].str.contains('fee|charge', case=False, na=False)].copy()
    
    # Group by month
    nsf_df['month'] = nsf_df['date'].dt.to_period('M')
    nsf_by_month = nsf_df.groupby('month').size().reset_index(name='nsf_count')
    nsf_monthly = nsf_by_month.to_dict(orient='records')

    # 2. Daily Closing Balance calculation
    daily_balances = df.groupby(df['date'].dt.date)['balance_after'].last()
    low_balance_days = (daily_balances < low_balance_threshold).sum()
    
    # 3. Assess Risk Grade dynamically for the report output
    nsf_count = len(nsf_df)
    if nsf_count == 0:
        risk_tier = "Low"
    elif 1 <= nsf_count <= 2:
        risk_tier = "Moderate"
    else:
        risk_tier = "High (Critical Underwriting Risk)"
        
    return {
        "risk_assessment": {
            "nsf_count": int(nsf_count),
            "low_balance_days_count": int(low_balance_days),
            "nsf_by_month": nsf_monthly,
            "minimum_recorded_balance": float(df['balance_after'].min()),
            "risk_tier_assignment": risk_tier
        },
        "flagged_nsf_ledger": nsf_df[['date', 'description', 'amount', 'balance_after']].to_dict(orient='records')
    }
