import pytest
from backend.db import get_db_connection, init_db

def test_db_connection_and_tables():
    conn = get_db_connection()
    assert conn is not None
    init_db()
    
    with conn.cursor() as cur:
        # Check that tables exist in PostgreSQL with snake_case naming
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('players', 'player_season_stats', 'market_value_history', 'galaxy_nodes', 'player_career_trajectories');
        """)
        tables = [row[0] for row in cur.fetchall()]
        assert 'players' in tables
        assert 'player_season_stats' in tables
        assert 'market_value_history' in tables
        assert 'galaxy_nodes' in tables
        assert 'player_career_trajectories' in tables
    conn.close()
