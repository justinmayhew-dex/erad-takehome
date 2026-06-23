import pandas as pd
import os

def parse_csv_statement(raw_path, processed_path, args):
  print('Mock Parsing...') 
  df = load_csv(raw_path, args)
  df = clean_csv(df)
  print(df) 
  save_clean(df, processed_path)
  return df

def load_csv(raw_path, args):
    if args.file.endswith(('.xlsx', '.xls')):
        return pd.read_excel(raw_path)
    else:
        return pd.read_csv(raw_path)

def clean_csv(df):
    # Clean up column names just in case there are accidental whitespaces
    df.columns = df.columns.str.strip().str.lower()
    
    if 'date' in df.columns:
        s_date = df['date'].astype(str).str.strip()
        
        # 2. Force conversion with strict formatting rules
        temp_date = pd.to_datetime(s_date, errors='coerce', format='mixed')
        
        # 3. Track parsing anomalies safely
        failed_date_mask = temp_date.isna() & (s_date != '') & (s_date != 'nan') & (s_date != 'none')
        
        if failed_date_mask.any():
            corrupted_dates = df[failed_date_mask]
            for idx, row in corrupted_dates.iterrows():
                print(
                    f"Parsing Failure in column 'date' at CSV Row {idx + 2}: "
                    f"Could not convert raw date '{row['date']}' to a standard timestamp."
                )
        
        # 4. Bind it back to the dataframe
        df['date'] = temp_date    
    else:
        raise("Critical Error: 'date' column missing from data input.")

    for col in ['amount', 'balance_after']:
        if df[col].dtype == 'object':
            #Strip symbols like $ 
            df[col] = df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)

            #Force into float 64 (or int64 if every row is integer)
            temp_numeric = pd.to_numeric(df[col], errors='coerce')
            
            #Check for any nan values after coercing into numbers
            failed_mask = temp_numeric.isna() & (s != '') & (s != 'nan')
            
            if failed_mask.any():
                corrupted_rows = df[failed_mask]
                for idx, row in corrupted_rows.iterrows():
                    logging.warning(
                        f"Parsing Failure in column '{col}' at CSV Row {idx + 2}: "
                        f"Could not convert raw value '{row[col]}' to numeric format."
                    )
            df[col] = temp_numeric

    clean_df = df.dropna(subset=['date', 'amount', 'balance_after']).reset_index(drop=True)
    clean_df['date'] = pd.to_datetime(clean_df['date'])
    clean_df = clean_df.sort_values(by='date').reset_index(drop=True)

    return clean_df

def save_clean(df, processed_path):
    try:
        # Check dir exists if not create it
        output_dir = os.path.dirname(processed_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        # Write to the destination path
        df.to_csv(processed_path, index=False)
        print(f"Successfully wrote clean statement data to: {processed_path}")
        
    except IOError as e:
        print(f"File System Error: Failed to write output to {processed_path}. Details: {e}")

    except Exception as e:
        print(f"Unexpected error while exporting data: {e}")
