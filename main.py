import argparse
import os
import re
from parser.csv_parser import parse_csv_statement
from analyzer.revenue import analyze_revenue
from analyzer.risk_flags import detect_risk_flags
from analyzer.runway import calculate_stressed_runway 

def main(): 
    parser = argparse.ArgumentParser(description="Generate Credit Report")
    parser.add_argument('--file', required=True, help="Filename inside /data/raw")
    #parser.add_argument('--col', required=True, help="The name of the phone number column to clean")
    #parser.add_argument('--sheet', default=0, help="Sheet name or index")
    #parser.add_argument('--header', type=int, default=0, help="0-indexed row number for headers")
 
    args = parser.parse_args()
    
    raw_path = os.path.join('data', 'raw', args.file)
    # Changed output extension to .xlsx to preserve Excel structural integrity
    processed_path = os.path.join('data', 'processed', f"clean_{args.file}")
    
    print(f"Reading {raw_path}...")

    df = parse_csv_statement(raw_path, processed_path, args)
    
    revenue_analysis = analyze_revenue(df)
    risk_flag_analysis = detect_risk_flags(df)
    runway_analysis = calculate_stressed_runway(df)

    print(revenue_analysis)
    print(risk_flag_analysis)
    print(runway_analysis)

if __name__ == "__main__":
    main()
