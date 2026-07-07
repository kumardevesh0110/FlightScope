import duckdb
import pandas as pd

class FlightDatabaseManager:
    def __init__(self, db_path: str = "data/Flights_2022_sampled_1.8M.parquet"):
        """
        Initializes the DuckDB connection to the Parquet file.
        Uses an in-memory view to query the file on disk efficiently.
        """
        self.db_path = db_path
        self.conn = duckdb.connect(database=':memory:')
        
        # Create a view pointing to the parquet file
        self.conn.execute(f"CREATE VIEW flights AS SELECT * FROM read_parquet('{self.db_path}')")

    def get_network_nodes(self, airline: str = None) -> pd.DataFrame:
        """
        Task 4.1: Air Traffic Network Explorer
        Aggregates flight volumes and average delays between Origin and Dest.
        """
        query = """
            SELECT 
                Origin, 
                Dest, 
                COUNT(*) as FlightCount,
                AVG(ArrDelay) as AvgArrDelay
            FROM flights
            WHERE Cancelled = false
        """
        if airline:
            query += f" AND Marketing_Airline_Network = '{airline}'"
            
        query += " GROUP BY Origin, Dest ORDER BY FlightCount DESC"
        return self.conn.execute(query).df()

    def get_airport_delays_by_month(self) -> pd.DataFrame:
        """
        Task 4.2: Airport Delay Heatmap
        Gets average arrival delays per airport per month to track seasonal patterns.
        """
        query = """
            SELECT 
                Origin,
                Month,
                AVG(DepDelay) as AvgDepDelay,
                COUNT(*) as TotalFlights
            FROM flights
            WHERE Cancelled = false
            GROUP BY Origin, Month
        """
        return self.conn.execute(query).df()

    def get_airline_performance(self) -> pd.DataFrame:
        """
        Task 4.3: Airline Performance Dashboard
        Benchmarks airlines on delays and cancellation rates.
        """
        query = """
            SELECT 
                Marketing_Airline_Network as Airline,
                COUNT(*) as TotalFlights,
                AVG(DepDelay) as AvgDepDelay,
                AVG(ArrDelay) as AvgArrDelay,
                (SUM(CAST(Cancelled AS INT)) * 100.0 / COUNT(*)) as CancellationRate
            FROM flights
            GROUP BY Marketing_Airline_Network
            ORDER BY TotalFlights DESC
        """
        return self.conn.execute(query).df()

    def get_delay_causes(self, airport: str = None) -> pd.DataFrame:
        """
        Task 4.4: Delay Cause Analysis
        Aggregates total minutes for each delay category for the Sankey Diagram.
        """
        query = """
            SELECT 
                Marketing_Airline_Network as Airline,
                SUM(CarrierDelay) as CarrierDelay,
                SUM(WeatherDelay) as WeatherDelay,
                SUM(NASDelay) as NASDelay,
                SUM(SecurityDelay) as SecurityDelay,
                SUM(LateAircraftDelay) as LateAircraftDelay
            FROM flights
            WHERE (CarrierDelay > 0 OR WeatherDelay > 0 OR NASDelay > 0 OR SecurityDelay > 0 OR LateAircraftDelay > 0)
        """
        if airport:
            query += f" AND (Origin = '{airport}' OR Dest = '{airport}')"
            
        query += " GROUP BY Marketing_Airline_Network"
        return self.conn.execute(query).df()

    def get_raw_sample(self, limit: int = 10000) -> pd.DataFrame:
        """
        Task 4.5: High-Dimensional Analytics
        Extracts a random sample of rows for PCA / Parallel Coordinates plots,
        as rendering 1.8M lines in a browser will crash it.
        """
        query = f"""
            SELECT 
                Marketing_Airline_Network, Origin, Dest, Distance, AirTime,
                DepDelay, ArrDelay, TaxiOut, TaxiIn
            FROM flights
            USING SAMPLE {limit}
        """
        return self.conn.execute(query).df()

    def close(self):
        """Safely closes the database connection."""
        self.conn.close()

# --- Execution Block ---
if __name__ == "__main__":
    # Test the connection when running the script directly
    try:
        db = FlightDatabaseManager()
        
        print("Testing Database Connection and Queries...\n")
        
        perf_df = db.get_airline_performance()
        print("--- Task 4.3: Airline Performance Snapshot ---")
        print(perf_df.head(), "\n")
        
        causes_df = db.get_delay_causes()
        print("--- Task 4.4: Delay Causes by Airline ---")
        print(causes_df.head(), "\n")
        
        db.close()
        print("All queries executed successfully. Backend is ready.")
        
    except duckdb.IOException:
        print("Error: Could not find the Parquet file. Make sure 'Flights_2022_sampled_1.8M.parquet' is in the '../data/' folder relative to this script.")