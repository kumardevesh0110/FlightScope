import os
import duckdb
import pandas as pd
import networkx as nx
from functools import lru_cache
from src.pipeline.config import DB_PATH, PROCESSED_DIR

AIRPORTS_CSV_PATH = os.path.join(PROCESSED_DIR, "airports.csv")

def get_db_connection():
    """Establishes a read-only connection to the DuckDB database."""
    return duckdb.connect(DB_PATH, read_only=True)

def get_airlines():
    """Returns a list of unique marketing airlines for filters."""
    conn = get_db_connection()
    try:
        query = """
            SELECT DISTINCT Marketing_Airline_Network 
            FROM flights 
            ORDER BY Marketing_Airline_Network
        """
        df = conn.execute(query).df()
        return df['Marketing_Airline_Network'].dropna().tolist()
    finally:
        conn.close()

def _build_where_clause(airport=None, airline=None, season=None, month=None, date=None, day_of_week=None, dep_hour=None, day_of_month=None):
    """Helper to construct WHERE clause filters dynamically using positional parameters."""
    conditions = []
    params = []
    
    if airport:
        conditions.append("Origin = ?")
        params.append(airport)
        
    if airline:
        conditions.append("Marketing_Airline_Network = ?")
        params.append(airline)
        
    if season:
        # Season mapping: 1=Winter, 2=Spring, 3=Summer, 4=Fall
        season_map = {"Winter": 1, "Spring": 2, "Summer": 3, "Fall": 4}
        if season in season_map:
            conditions.append("Season = ?")
            params.append(season_map[season])
            
    if month is not None:
        conditions.append("Month = ?")
        params.append(int(month))
        
    if date:
        conditions.append("CAST(FlightDate AS STRING) = ?")
        params.append(date)
        
    if day_of_week is not None:
        conditions.append("DayOfWeek = ?")
        params.append(int(day_of_week))
        
    if dep_hour is not None:
        conditions.append("DepHour = ?")
        params.append(int(dep_hour))
        
    if day_of_month is not None:
        conditions.append("DayofMonth = ?")
        params.append(int(day_of_month))
            
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    return where_clause, tuple(params)

@lru_cache(maxsize=128)
def _get_airport_delay_summary_cached(airline, season, metric, month, day_of_week, dep_hour, day_of_month):
    """Cached internal version of get_airport_delay_summary"""
    """
    Returns a summary of flights grouped by Origin airport.
    Joins with airports.csv to get lat/lon coordinates.
    """
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airline=airline, season=season, month=month, day_of_week=day_of_week, dep_hour=dep_hour, day_of_month=day_of_month)
        
        # Determine the database metric to aggregate
        db_metric = metric
        if metric not in ['DepDelay', 'ArrDelay', 'TaxiOut', 'TaxiIn', 'Cancelled']:
            db_metric = 'DepDelay'
            
        if db_metric == 'Cancelled':
            agg_expr = "MEAN(CASE WHEN Cancelled = true THEN 1.0 ELSE 0.0 END) * 100"
        else:
            agg_expr = f"AVG(CAST({db_metric} AS FLOAT))"

        # Replace backslashes in paths with forward slashes for DuckDB read_csv on Windows
        safe_path = AIRPORTS_CSV_PATH.replace('\\', '/')

        query = f"""
            SELECT 
                f.Origin AS faa,
                MAX(a.name) AS name,
                MAX(a.lat) AS lat,
                MAX(a.lon) AS lon,
                COUNT(*) AS flight_count,
                {agg_expr} AS avg_metric
            FROM flights f
            JOIN read_csv('{safe_path}') a ON f.Origin = a.faa
            {where_clause}
            GROUP BY f.Origin
            HAVING MAX(a.lat) IS NOT NULL AND MAX(a.lon) IS NOT NULL
        """
        df = conn.execute(query, list(params)).df()
        return df
    finally:
        conn.close()

def get_airport_delay_summary(airline=None, season=None, metric='DepDelay', month=None, day_of_week=None, dep_hour=None, day_of_month=None):
    df = _get_airport_delay_summary_cached(airline, season, metric, month, day_of_week, dep_hour, day_of_month)
    return df.copy()

@lru_cache(maxsize=128)
def _get_temporal_delay_data_cached(airport, airline, season, metric):
    """
    Returns aggregated metrics for:
    1. DayOfWeek vs DepHour (Hourly grid)
    2. Month vs DayofMonth (Monthly grid)
    """
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airport=airport, airline=airline, season=season)
        
        db_metric = metric
        if metric not in ['DepDelay', 'ArrDelay', 'TaxiOut', 'TaxiIn', 'Cancelled']:
            db_metric = 'DepDelay'
            
        if db_metric == 'Cancelled':
            agg_expr = "MEAN(CASE WHEN Cancelled = true THEN 1.0 ELSE 0.0 END) * 100"
        else:
            agg_expr = f"AVG(CAST({db_metric} AS FLOAT))"

        q_hourly = f"""
            WITH base AS (
                SELECT 
                    DayOfWeek,
                    DepHour,
                    Marketing_Airline_Network,
                    COUNT(*) as flight_count,
                    MEAN(CASE WHEN Cancelled = true THEN 1.0 ELSE 0.0 END) * 100 as cancel_rate,
                    {agg_expr} AS avg_val
                FROM flights
                {where_clause}
                GROUP BY DayOfWeek, DepHour, Marketing_Airline_Network
            )
            SELECT DayOfWeek, DepHour, SUM(flight_count) as flight_count, 
                   AVG(cancel_rate) as cancel_rate, 
                   SUM(avg_val * flight_count)/SUM(flight_count) as avg_val,
                   arg_max(Marketing_Airline_Network, avg_val) as worst_airline
            FROM base
            GROUP BY DayOfWeek, DepHour
        """
        df_hourly = conn.execute(q_hourly, list(params)).df()
        
        # Query 2: Month vs DayofMonth
        q_monthly = f"""
            WITH base AS (
                SELECT 
                    Month,
                    DayofMonth,
                    Marketing_Airline_Network,
                    COUNT(*) as flight_count,
                    MEAN(CASE WHEN Cancelled = true THEN 1.0 ELSE 0.0 END) * 100 as cancel_rate,
                    {agg_expr} AS avg_val
                FROM flights
                {where_clause}
                GROUP BY Month, DayofMonth, Marketing_Airline_Network
            )
            SELECT Month, DayofMonth, SUM(flight_count) as flight_count,
                   AVG(cancel_rate) as cancel_rate,
                   SUM(avg_val * flight_count)/SUM(flight_count) as avg_val,
                   arg_max(Marketing_Airline_Network, avg_val) as worst_airline
            FROM base
            GROUP BY Month, DayofMonth
        """
        df_monthly = conn.execute(q_monthly, list(params)).df()
        
        return df_hourly, df_monthly
    finally:
        conn.close()

def get_temporal_delay_data(airport=None, airline=None, season=None, metric='DepDelay'):
    h, m = _get_temporal_delay_data_cached(airport, airline, season, metric)
    return h.copy(), m.copy()

@lru_cache(maxsize=128)
def get_overall_kpis(airport=None, airline=None, season=None):
    """Returns overall summary statistics for KPI cards."""
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airport=airport, airline=airline, season=season)
        
        query = f"""
            SELECT 
                COUNT(*) AS total_flights,
                AVG(CAST(DepDelay AS FLOAT)) AS avg_dep_delay,
                AVG(CAST(ArrDelay AS FLOAT)) AS avg_arr_delay,
                MEAN(CASE WHEN Cancelled = true THEN 1.0 ELSE 0.0 END) * 100 AS cancellation_rate
            FROM flights
            {where_clause}
        """
        res = conn.execute(query, list(params)).fetchone()
        if res:
            return {
                "total_flights": int(res[0]) if res[0] is not None else 0,
                "avg_dep_delay": float(res[1]) if res[1] is not None else 0.0,
                "avg_arr_delay": float(res[2]) if res[2] is not None else 0.0,
                "cancellation_rate": float(res[3]) if res[3] is not None else 0.0
            }
        return {"total_flights": 0, "avg_dep_delay": 0.0, "avg_arr_delay": 0.0, "cancellation_rate": 0.0}
    finally:
        conn.close()

def get_airport_list():
    """Returns distinct (faa, name) pairs for airports present in the flights table, for dropdown options."""
    conn = get_db_connection()
    try:
        safe_path = AIRPORTS_CSV_PATH.replace('\\', '/')
        query = f"""
            SELECT DISTINCT f.Origin AS faa, MAX(a.name) AS name
            FROM flights f
            JOIN read_csv('{safe_path}') a ON f.Origin = a.faa
            GROUP BY f.Origin
            ORDER BY f.Origin
        """
        return conn.execute(query).df()
    finally:
        conn.close()

def get_network_data(airline=None, season=None, airport=None):
    """
    Returns edge list (Origin to Dest counts) and node attributes (Centrality metrics)
    using NetworkX. If airport is given, only routes originating from that airport are included.
    """
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airport=airport, airline=airline, season=season)
        
        # 1. Edge list: flights between Origin and Dest
        query_edges = f"""
            SELECT 
                Origin, 
                Dest, 
                CAST(COUNT(*) AS FLOAT) AS weight,
                AVG(CAST(DepDelay AS FLOAT)) AS avg_delay
            FROM flights
            {where_clause}
            GROUP BY Origin, Dest
        """
        df_edges = conn.execute(query_edges, params).df()
        
        # 2. Node metadata: airport coordinates and names
        safe_path = AIRPORTS_CSV_PATH.replace('\\', '/')
        query_nodes = f"""
            SELECT DISTINCT faa, name, lat, lon
            FROM read_csv('{safe_path}')
        """
        df_nodes = conn.execute(query_nodes).df()
        
        if df_edges.empty:
            return df_edges, pd.DataFrame(columns=['faa', 'name', 'lat', 'lon', 'degree', 'betweenness', 'pagerank'])
            
        # 3. Compute NetworkX centrality metrics
        G = nx.from_pandas_edgelist(
            df_edges, 
            source='Origin', 
            target='Dest', 
            edge_attr=['weight', 'avg_delay'], 
            create_using=nx.DiGraph()
        )
        
        # Centrality calculations
        degree = nx.degree_centrality(G)
        # Using weight for betweenness. Note: in networkx, higher weight = higher distance. 
        # But here weight is flight count. So we might need to invert it or just calculate unweighted.
        # Unweighted betweenness is often better for aviation networks where any connection is a hop.
        betweenness = nx.betweenness_centrality(G, weight=None)
        
        try:
            pagerank = nx.pagerank(G, weight='weight')
        except:
            pagerank = {n: 0 for n in G.nodes()}
            
        centrality_df = pd.DataFrame({
            'faa': list(G.nodes()),
            'degree': [degree.get(n, 0) for n in G.nodes()],
            'betweenness': [betweenness.get(n, 0) for n in G.nodes()],
            'pagerank': [pagerank.get(n, 0) for n in G.nodes()],
        })
        
        # Merge with airport metadata (only keep nodes that are in the graph)
        df_nodes = df_nodes.merge(centrality_df, on='faa', how='inner')
        
        return df_edges, df_nodes
    finally:
        conn.close()

def get_airline_kpis(airline=None, season=None, month=None):
    """Returns KPI summary (flights, avg arrival delay, on-time %, cancellation %) for the Airline Dashboard."""
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airline=airline, season=season, month=month)
        query = f"""
            SELECT
                COUNT(*) AS total_flights,
                AVG(CAST(ArrDelay AS FLOAT)) AS avg_arr_delay,
                MEAN(CASE WHEN CAST(ArrDelay AS FLOAT) > 15 THEN 1.0 ELSE 0.0 END) * 100 AS delayed_pct,
                MEAN(CASE WHEN Cancelled = true THEN 1.0 ELSE 0.0 END) * 100 AS cancellation_pct
            FROM flights
            {where_clause}
        """
        res = conn.execute(query, params).fetchone()
        if res and res[0]:
            delayed_pct = res[2] if res[2] is not None else 0.0
            return {
                "total_flights": int(res[0]),
                "avg_arr_delay": float(res[1]) if res[1] is not None else 0.0,
                "ontime_pct": round(100 - delayed_pct, 2),
                "cancellation_pct": float(res[3]) if res[3] is not None else 0.0
            }
        return {"total_flights": 0, "avg_arr_delay": 0.0, "ontime_pct": 0.0, "cancellation_pct": 0.0}
    finally:
        conn.close()

def get_airline_ranking(season=None, month=None, top_n=15):
    """Returns the top N airlines by flight volume, for the ranking bar chart."""
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(season=season, month=month)
        query = f"""
            SELECT Marketing_Airline_Network AS Airline, COUNT(*) AS Flights
            FROM flights
            {where_clause}
            GROUP BY Marketing_Airline_Network
            ORDER BY Flights DESC
            LIMIT {int(top_n)}
        """
        return conn.execute(query, params).df()
    finally:
        conn.close()

def get_airline_delay_causes(airport=None, airline=None, season=None, month=None, day_of_week=None, dep_hour=None, day_of_month=None):
    """Returns total delay-minutes by cause, for the delay-cause pie chart."""
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airport=airport, airline=airline, season=season, month=month, day_of_week=day_of_week, dep_hour=dep_hour, day_of_month=day_of_month)
        query = f"""
            SELECT
                SUM(CAST(CarrierDelay AS FLOAT)) AS CarrierDelay,
                SUM(CAST(WeatherDelay AS FLOAT)) AS WeatherDelay,
                SUM(CAST(NASDelay AS FLOAT)) AS NASDelay,
                SUM(CAST(SecurityDelay AS FLOAT)) AS SecurityDelay,
                SUM(CAST(LateAircraftDelay AS FLOAT)) AS LateAircraftDelay
            FROM flights
            {where_clause}
        """
        res = conn.execute(query, params).fetchone()
        causes = ["CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay"]
        if not res:
            return {c: 0.0 for c in causes}
        return {c: (float(res[i]) if res[i] is not None else 0.0) for i, c in enumerate(causes)}
    finally:
        conn.close()

def get_airline_volume_delay_scatter(season=None, month=None):
    """Returns per-airline flight volume vs average arrival delay, for the scatter chart."""
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(season=season, month=month)
        query = f"""
            SELECT
                Marketing_Airline_Network AS Airline,
                COUNT(*) AS Flights,
                AVG(CAST(ArrDelay AS FLOAT)) AS AverageDelay
            FROM flights
            {where_clause}
            GROUP BY Marketing_Airline_Network
        """
        return conn.execute(query, params).df()
    finally:
        conn.close()

def get_airline_monthly_trend(airline=None, season=None):
    """Returns monthly flight volume and average delay, for the monthly trend line chart."""
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airline=airline, season=season)
        query = f"""
            SELECT Month, COUNT(*) AS Flights, AVG(CAST(ArrDelay AS FLOAT)) AS AvgDelay
            FROM flights
            {where_clause}
            GROUP BY Month
            ORDER BY Month
        """
        return conn.execute(query, params).df()
    finally:
        conn.close()

def get_airline_top_airports(airline=None, season=None, month=None, top_n=30):
    """Returns the top N origin airports by flight count, with coordinates, for the airport map."""
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airline=airline, season=season, month=month)
        safe_path = AIRPORTS_CSV_PATH.replace('\\', '/')
        query = f"""
            SELECT
                f.Origin AS faa,
                MAX(a.name) AS name,
                MAX(a.lat) AS lat,
                MAX(a.lon) AS lon,
                COUNT(*) AS flights
            FROM flights f
            JOIN read_csv('{safe_path}') a ON f.Origin = a.faa
            {where_clause}
            GROUP BY f.Origin
            HAVING MAX(a.lat) IS NOT NULL AND MAX(a.lon) IS NOT NULL
            ORDER BY flights DESC
            LIMIT {int(top_n)}
        """
        return conn.execute(query, params).df()
    finally:
        conn.close()

def get_pca_sample(airline=None, season=None, month=None, sample_size=5000):
    """
    Returns a random sample of pre-computed PCA-reduced flight records for the
    High-Dimensional Analytics scatter plot, filtered by the given criteria.
    """
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airline=airline, season=season, month=month)
        base_condition = "PCA_1 IS NOT NULL AND PCA_2 IS NOT NULL"
        if where_clause:
            where_clause = where_clause + f" AND {base_condition}"
        else:
            where_clause = f" WHERE {base_condition}"

        query = f"""
            SELECT PCA_1, PCA_2, Origin_Dep_Congestion, Marketing_Airline_Network, ArrDelay
            FROM flights
            {where_clause}
            USING SAMPLE {int(sample_size)}
        """
        return conn.execute(query, params).df()
    finally:
        conn.close()

def get_delay_causes(airline=None, season=None, month=None, date=None):
    """
    Returns the total minutes for each of the 5 main delay causes,
    grouped by Delay Severity (Minor < 45m, Major >= 45m).
    """
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airline=airline, season=season, month=month, date=date)
        
        query = f"""
            SELECT 
                CASE WHEN CAST(ArrDelayMinutes AS FLOAT) >= 45 THEN 'Major' ELSE 'Minor' END AS Severity,
                SUM(CAST(CarrierDelay AS FLOAT)) AS CarrierDelay,
                SUM(CAST(WeatherDelay AS FLOAT)) AS WeatherDelay,
                SUM(CAST(NASDelay AS FLOAT)) AS NASDelay,
                SUM(CAST(SecurityDelay AS FLOAT)) AS SecurityDelay,
                SUM(CAST(LateAircraftDelay AS FLOAT)) AS LateAircraftDelay
            FROM flights
            {where_clause}
            GROUP BY CASE WHEN CAST(ArrDelayMinutes AS FLOAT) >= 45 THEN 'Major' ELSE 'Minor' END
        """
        df = conn.execute(query, params).df()
        
        result = {
            'Minor': {"CarrierDelay": 0, "WeatherDelay": 0, "NASDelay": 0, "SecurityDelay": 0, "LateAircraftDelay": 0},
            'Major': {"CarrierDelay": 0, "WeatherDelay": 0, "NASDelay": 0, "SecurityDelay": 0, "LateAircraftDelay": 0}
        }
        
        if not df.empty:
            for _, row in df.iterrows():
                sev = row['Severity']
                if sev in result:
                    result[sev]["CarrierDelay"] = row["CarrierDelay"] if pd.notna(row["CarrierDelay"]) else 0
                    result[sev]["WeatherDelay"] = row["WeatherDelay"] if pd.notna(row["WeatherDelay"]) else 0
                    result[sev]["NASDelay"] = row["NASDelay"] if pd.notna(row["NASDelay"]) else 0
                    result[sev]["SecurityDelay"] = row["SecurityDelay"] if pd.notna(row["SecurityDelay"]) else 0
                    result[sev]["LateAircraftDelay"] = row["LateAircraftDelay"] if pd.notna(row["LateAircraftDelay"]) else 0
                    
        return result
    finally:
        conn.close()
