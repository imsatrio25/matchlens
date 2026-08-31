import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import urllib.parse
from backend.config import DATABASE_URL

def ensure_database_exists():
    url = urllib.parse.urlparse(DATABASE_URL)
    db_name = url.path.lstrip('/') or 'matchlens'
    user = url.username or 'satrio'
    password = url.password or ''
    host = url.hostname or 'localhost'
    port = url.port or 5432

    # Connect to default postgres to create database if missing
    try:
        conn = psycopg2.connect(
            dbname='postgres',
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}';")
            if not cur.fetchone():
                cur.execute(f"CREATE DATABASE {db_name};")
        conn.close()
    except Exception as e:
        # If postgres default database check fails, attempt direct connection
        pass

def get_db_connection():
    ensure_database_exists()
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            team VARCHAR(255) NOT NULL,
            position VARCHAR(64) NOT NULL,
            current_market_value_eur BIGINT DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS player_season_stats (
            id SERIAL PRIMARY KEY,
            player_id VARCHAR(64) REFERENCES players(player_id) ON DELETE CASCADE,
            season VARCHAR(16) NOT NULL,
            appearances INT DEFAULT 0,
            minutes_played INT DEFAULT 0,
            goals_per_90 NUMERIC(6,3) DEFAULT 0,
            assists_per_90 NUMERIC(6,3) DEFAULT 0,
            xg_per_90 NUMERIC(6,3) DEFAULT 0,
            xa_per_90 NUMERIC(6,3) DEFAULT 0,
            shots_per_90 NUMERIC(6,3) DEFAULT 0,
            shots_on_target_pct NUMERIC(5,2) DEFAULT 0,
            key_passes_per_90 NUMERIC(6,3) DEFAULT 0,
            through_balls_per_90 NUMERIC(6,3) DEFAULT 0,
            successful_dribbles_per_90 NUMERIC(6,3) DEFAULT 0,
            forward_passes_per_90 NUMERIC(6,3) DEFAULT 0,
            pass_completion_pct NUMERIC(5,2) DEFAULT 0,
            touches_in_box_per_90 NUMERIC(6,3) DEFAULT 0,
            tackles_won_per_90 NUMERIC(6,3) DEFAULT 0,
            interceptions_per_90 NUMERIC(6,3) DEFAULT 0,
            recoveries_per_90 NUMERIC(6,3) DEFAULT 0,
            aerial_duels_won_pct NUMERIC(5,2) DEFAULT 0,
            losses_of_possession_per_90 NUMERIC(6,3) DEFAULT 0,
            UNIQUE (player_id, season)
        );

        CREATE TABLE IF NOT EXISTS market_value_history (
            id SERIAL PRIMARY KEY,
            player_id VARCHAR(64) REFERENCES players(player_id) ON DELETE CASCADE,
            valuation_date DATE NOT NULL,
            market_value_eur BIGINT NOT NULL,
            club VARCHAR(255) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS galaxy_nodes (
            player_id VARCHAR(64) PRIMARY KEY REFERENCES players(player_id) ON DELETE CASCADE,
            coord_x NUMERIC(8,4) NOT NULL,
            coord_y NUMERIC(8,4) NOT NULL,
            coord_z NUMERIC(8,4) NOT NULL,
            cluster_id INT NOT NULL,
            cluster_label VARCHAR(128) NOT NULL,
            actual_market_value_eur BIGINT NOT NULL,
            predicted_market_value_eur BIGINT NOT NULL,
            value_residual_eur BIGINT NOT NULL,
            value_efficiency_score NUMERIC(5,2) NOT NULL,
            is_undervalued_gem BOOLEAN DEFAULT FALSE,
            nearest_neighbors JSONB NOT NULL DEFAULT '[]'::jsonb,
            radar_percentiles JSONB NOT NULL DEFAULT '{}'::jsonb
        );

        CREATE TABLE IF NOT EXISTS player_career_trajectories (
            id SERIAL PRIMARY KEY,
            player_id VARCHAR(64) REFERENCES players(player_id) ON DELETE CASCADE,
            season VARCHAR(16) NOT NULL,
            season_order INT NOT NULL,
            coord_x NUMERIC(8,4) NOT NULL,
            coord_y NUMERIC(8,4) NOT NULL,
            coord_z NUMERIC(8,4) NOT NULL,
            market_value_eur BIGINT NOT NULL,
            minutes_played INT NOT NULL,
            xg_per_90 NUMERIC(6,3) DEFAULT 0,
            xa_per_90 NUMERIC(6,3) DEFAULT 0
        );
        """)
        conn.commit()
    conn.close()
