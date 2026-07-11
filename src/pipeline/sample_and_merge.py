import os
import glob
import pandas as pd
import numpy as np
from src.pipeline.config import RAW_DIR, PROCESSED_DIR, COLUMNS_TO_KEEP

def clean_and_sample(filepath, target_samples=None):
    print(f"Processing and cleaning {filepath}...")
    
    # 1. Drop completely (or almost) missing columns (accomplished via usecols)
    df = pd.read_csv(filepath, usecols=lambda c: c in COLUMNS_TO_KEEP, low_memory=False)
    
    # Drop exact duplicates
    df.drop_duplicates(inplace=True)
    
    # 2. Add / Impute missing data
    # Fill delay columns with 0 (since BTS logs them as NaN when there is no delay)
    delay_cols = ['CarrierDelay', 'WeatherDelay', 'NASDelay', 'SecurityDelay', 'LateAircraftDelay']
    existing_delays = [c for c in delay_cols if c in df.columns]
    if existing_delays:
        df[existing_delays] = df[existing_delays].fillna(0)
        
    # Fill CancellationCode
    if 'CancellationCode' in df.columns:
        df['CancellationCode'] = df['CancellationCode'].fillna('N/A')
        
    # Fill missing Tail_Number
    if 'Tail_Number' in df.columns:
        df['Tail_Number'] = df['Tail_Number'].fillna('UNKNOWN')
        
    # Filter out invalid operational rows (flights that are active but have missing times)
    if 'Cancelled' in df.columns and 'Diverted' in df.columns:
        critical_cols = ['DepTime', 'ArrTime', 'ActualElapsedTime']
        existing_crit = [col for col in critical_cols if col in df.columns]
        is_cancelled_or_diverted = (df['Cancelled'] == 1) | (df['Diverted'] == 1)
        has_valid_times = df[existing_crit].notnull().all(axis=1)
        df = df[is_cancelled_or_diverted | has_valid_times]
        
    # 3. Consistency of Datatypes (Prepare types before merging)
    # Ensure binary fields are boolean
    if 'Cancelled' in df.columns:
        df['Cancelled'] = df['Cancelled'].astype(bool)
    if 'Diverted' in df.columns:
        df['Diverted'] = df['Diverted'].astype(bool)
        
    # Standardize string fields (remove whitespace)
    string_cols = ['Marketing_Airline_Network', 'Operating_Airline', 'Origin', 'Dest', 'Tail_Number', 'CancellationCode']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
    if 'FlightDate' in df.columns:
        df['FlightDate'] = pd.to_datetime(df['FlightDate'])
        
    if target_samples is not None:
        # Stratify by Carrier and Delay status to keep rich representation of delays
        df['IsDelayedOrCancelled'] = (df['DepDelay'] > 0) | (df['ArrDelay'] > 0) | (df['Cancelled'] == True)
        
        grouped = df.groupby(['Marketing_Airline_Network', 'IsDelayedOrCancelled'], observed=True)
        sampled_chunks = []
        total_len = len(df)
        
        for _, group in grouped:
            group_n = int(round((len(group) / total_len) * target_samples))
            group_n = max(min(group_n, len(group)), min(150, len(group)))
            sampled_chunks.append(group.sample(n=group_n, random_state=42))
            
        sampled_df = pd.concat(sampled_chunks)
        
        if len(sampled_df) > target_samples:
            sampled_df = sampled_df.sample(n=target_samples, random_state=42)
        elif len(sampled_df) < target_samples:
            remaining = df.drop(sampled_df.index)
            needed = target_samples - len(sampled_df)
            sampled_df = pd.concat([sampled_df, remaining.sample(n=needed, random_state=42)])
            
        sampled_df.drop('IsDelayedOrCancelled', axis=1, inplace=True)
        return sampled_df
    else:
        return df

def run_sampling_and_merging():
    pattern = os.path.join(RAW_DIR, "Flights_2022_*.csv")
    csv_files = [f for f in glob.glob(pattern) if 'sampled' not in f]
    csv_files = sorted(csv_files, key=lambda x: int(os.path.basename(x).split('_')[-1].split('.')[0]))
    
    if not csv_files:
        print(f"No monthly CSV files found in {RAW_DIR}. Skipping sampling.")
        # If the parquet already exists, we will reuse it.
        expected_pq = os.path.join(PROCESSED_DIR, "Flights_2022_full_7M.parquet")
        if os.path.exists(expected_pq):
            print(f"Found existing full Parquet file: {expected_pq}. Reusing it.")
            return expected_pq
        else:
            raise FileNotFoundError(f"No CSVs in {RAW_DIR} and no full Parquet in {PROCESSED_DIR}.")
            
    all_sampled = []
    for filepath in csv_files:
        sampled_month = clean_and_sample(filepath, target_samples=None)
        all_sampled.append(sampled_month)

    print("Combining all months...")
    final_df = pd.concat(all_sampled, ignore_index=True)
    
    # 4. Find and remove Outliers (After Merging)
    print("Finding and handling outliers...")
    
    # A. Physical impossibilities (e.g. AirTime <= 0 for active flights)
    active_flights = (final_df['Cancelled'] == False) & (final_df['Diverted'] == False)
    invalid_rows = active_flights & (
        (final_df['AirTime'] <= 0) | 
        (final_df['TaxiOut'] <= 0) | 
        (final_df['TaxiIn'] <= 0) | 
        (final_df['ActualElapsedTime'] <= 0)
    )
    print(f"Removing {invalid_rows.sum()} rows with physically impossible values (AirTime/TaxiOut/TaxiIn <= 0)...")
    final_df = final_df[~invalid_rows]
    
    # B. Speed validation (Average flight speed must be reasonable for commercial jets)
    active_flights = (final_df['Cancelled'] == False) & (final_df['Diverted'] == False)
    speed_mph = final_df['Distance'] / (final_df['AirTime'] / 60.0)
    impossible_speed = active_flights & (final_df['Distance'] > 100) & ((speed_mph > 750) | (speed_mph < 60))
    print(f"Removing {impossible_speed.sum()} rows with impossible flight speeds (>750 mph or <60 mph)...")
    final_df = final_df[~impossible_speed]
    
    # C. Statistical Outliers (Z-score > 5 for taxi times)
    for col in ['TaxiOut', 'TaxiIn', 'ActualElapsedTime']:
        col_mean = final_df[col].mean()
        col_std = final_df[col].std()
        z_scores = (final_df[col] - col_mean) / col_std
        outliers = active_flights & (z_scores.abs() > 5)
        print(f"Removing {outliers.sum()} statistical outliers (Z-score > 5) from column '{col}'...")
        final_df = final_df[~outliers]

    # Optimize data types to save RAM
    for col in final_df.select_dtypes(include=['float64']).columns:
        final_df[col] = pd.to_numeric(final_df[col], downcast='float')
    for col in final_df.select_dtypes(include=['int64']).columns:
        final_df[col] = pd.to_numeric(final_df[col], downcast='integer')
        
    cat_cols = ['Marketing_Airline_Network', 'Operating_Airline', 'Origin', 'Dest', 'Tail_Number', 'CancellationCode']
    for col in cat_cols:
        if col in final_df.columns:
            final_df[col] = final_df[col].astype('category')

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    csv_out = os.path.join(PROCESSED_DIR, "Flights_2022_full_7M.csv")
    pq_out = os.path.join(PROCESSED_DIR, "Flights_2022_full_7M.parquet")
    
    print(f"Saving merged data to {csv_out}...")
    final_df.to_csv(csv_out, index=False)
    
    print(f"Saving merged data to {pq_out}...")
    final_df.to_parquet(pq_out, compression='snappy')
    print("Sampling and merging completed successfully!")
    return pq_out

if __name__ == "__main__":
    run_sampling_and_merging()
