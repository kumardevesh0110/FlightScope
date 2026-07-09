import os
import duckdb
import pandas as pd
import networkx as nx
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

def _build_where_clause(airport=None, airline=None, season=None):
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
            
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    return where_clause, params

def get_airport_delay_summary(airline=None, season=None, metric='DepDelay'):
    """
    Returns a summary of flights grouped by Origin airport.
    Joins with airports.csv to get lat/lon coordinates.
    """
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airline=airline, season=season)
        
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
        df = conn.execute(query, params).df()
        return df
    finally:
        conn.close()

def get_temporal_delay_data(airport=None, airline=None, season=None, metric='DepDelay'):
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

        # Query 1: DayOfWeek vs DepHour
        q_hourly = f"""
            SELECT 
                DayOfWeek,
                DepHour,
                {agg_expr} AS avg_val
            FROM flights
            {where_clause}
            GROUP BY DayOfWeek, DepHour
        """
        df_hourly = conn.execute(q_hourly, params).df()
        
        # Query 2: Month vs DayofMonth
        q_monthly = f"""
            SELECT 
                Month,
                DayofMonth,
                {agg_expr} AS avg_val
            FROM flights
            {where_clause}
            GROUP BY Month, DayofMonth
        """
        df_monthly = conn.execute(q_monthly, params).df()
        
        return df_hourly, df_monthly
    finally:
        conn.close()

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
        res = conn.execute(query, params).fetchone()
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

def get_network_data(airline=None, season=None):
    """
    Returns edge list (Origin to Dest counts) and node attributes (Centrality metrics)
    using NetworkX.
    """
    conn = get_db_connection()
    try:
        where_clause, params = _build_where_clause(airline=airline, season=season)
        
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
