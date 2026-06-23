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
        
    salary_df = identify_salary_payments(df)

    late_salaries_report = detect_late_salaries(df, salary_df)

    return {
        "risk_assessment": {
            "nsf_count": int(nsf_count),
            "low_balance_days_count": int(low_balance_days),
            "nsf_by_month": nsf_monthly,
            "minimum_recorded_balance": float(df['balance_after'].min()),
            "risk_tier_assignment": risk_tier
        },
        "flagged_nsf_ledger": nsf_df[['date', 'description', 'amount', 'balance_after']].to_dict(orient='records'),
        "late_salaries_report": late_salaries_report
    }


def identify_salary_payments(df: pd.DataFrame):
    outflows = df[df['amount'] < 0].copy()
    
    salary_keywords = ['salary', 'payroll', 'wages', 'salaries', 'paym', 'transfer to']
    salary_pattern = '|'.join(salary_keywords)

    salary_df = outflows[outflows['description'].str.contains(salary_pattern, case=False, na=False)].copy()

    noise_keywords = ['fee', 'tax', 'supplier', 'invoice', 'software']
    noise_pattern = '|'.join(noise_keywords)
    salary_df = salary_df[~salary_df['description'].str.contains(noise_pattern, case=False, na=False)]
    
    return salary_df

def detect_late_salaries(full_statement_df: pd.DataFrame, salary_df: pd.DataFrame, ) -> dict:
    if salary_df.empty or full_statement_df.empty:
        return {"payroll_detected": False, "late_months": [], "skipped_months": []}

    # Ensure everything is sorted oldest to newest
    salary_df = salary_df.sort_values(by='date').reset_index(drop=True)
    full_statement_df = full_statement_df.sort_values(by='date').reset_index(drop=True)

    # 1. Establish the absolute historical baseline pay day
    salary_df['month'] = salary_df['date'].dt.to_period('M')
    monthly_payroll = salary_df.groupby('month')['date'].min().reset_index()
    median_day = int(monthly_payroll['date'].dt.day.median())

    # 2. Track consecutive payment intervals (Days between payroll runs)
    # This captures a "skipped month" that was actually just paid very late next month
    salary_df['days_since_last_payroll'] = salary_df['date'].diff().dt.days
    
    # 3. Generate the complete continuous timeline boundary
    start_month = full_statement_df['date'].min().to_period('M')
    end_month = full_statement_df['date'].max().to_period('M')
    all_months = pd.period_range(start=start_month, end=end_month, freq='M')

    late_incidents = []
    skipped_months = []
    processed_months = set(monthly_payroll['month'])

    # 4. Evaluate Month-by-Month Status
    for current_month in all_months:
        
        # Check if a payment explicitly landed inside this calendar month
        if current_month not in processed_months:
            
            # Look at the very next payroll run after this empty month
            next_payments = salary_df[salary_df['date'].dt.to_period('M') > current_month]
            
            if not next_payments.empty:
                first_next_pay = next_payments.iloc[0]
                days_gap = first_next_pay['days_since_last_payroll']
                
                # If they paid eventually, but the gap was massive (e.g., > 40 days)
                if pd.notna(days_gap) and days_gap > 40:
                    late_incidents.append({
                        "month": str(current_month),
                        "status": "Severely Delayed (Spilled into next month)",
                        "actual_payout_date": first_next_pay['date'].strftime('%Y-%m-%d'),
                        "days_between_cycles": int(days_gap)
                    })
                    continue
            
            # If there is no subsequent payment or the gap doesn't map, it's completely skipped
            skipped_months.append(str(current_month))
            continue

        # Normal tracking for payments that landed inside their target calendar month
        actual_date = monthly_payroll[monthly_payroll['month'] == current_month]['date'].iloc[0]
        
        try:
            expected_date = pd.Timestamp(year=current_month.year, month=current_month.month, day=median_day)
        except ValueError:
            expected_date = current_month.to_timestamp(how='end').normalize()

        days_delta = (actual_date - expected_date).days

        if days_delta > 5:
            late_incidents.append({
                "month": str(current_month),
                "status": "Delayed",
                "expected_date": expected_date.strftime('%Y-%m-%d'),
                "actual_payout_date": actual_date.strftime('%Y-%m-%d'),
                "days_delayed": int(days_delta)
            })

    return {
        "payroll_detected": True,
        "historical_median_pay_day": median_day,
        "total_skipped_months": len(skipped_months),
        "skipped_months_log": skipped_months,
        "total_late_months": len(late_incidents),
        "late_incidents_log": late_incidents
    }
