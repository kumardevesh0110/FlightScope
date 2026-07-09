import os
import duckdb
from src.pipeline.config import PROCESSED_DIR, DB_PATH

def build_duckdb_database(parquet_path=None):
    if parquet_path is None:
        parquet_path = os.path.join(PROCESSED_DIR, "processed_flights.parquet")
        
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Processed parquet file not found at {parquet_path}. Please run feature engineering first.")
        
    print(f"Initializing DuckDB database at {DB_PATH}...")
    
    # Establish connection
    conn = duckdb.connect(DB_PATH)
    
    print("Loading data into 'flights' table...")
    conn.execute(f"CREATE OR REPLACE TABLE flights AS SELECT * FROM read_parquet('{parquet_path}')")
    
    print("Creating indexes on search fields...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_origin ON flights(Origin)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dest ON flights(Dest)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_carrier ON flights(Operating_Airline)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_marketing_airline ON flights(Marketing_Airline_Network)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_month ON flights(Month)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON flights(FlightDate)")
    
    row_count = conn.execute("SELECT COUNT(*) FROM flights").fetchone()[0]
    print(f"Successfully loaded table 'flights' with {row_count} rows!")
    
    conn.close()
    print("Database setup complete.")
    return DB_PATH

if __name__ == "__main__":
    build_duckdb_database()
