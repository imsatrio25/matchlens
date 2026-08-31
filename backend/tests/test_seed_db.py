import pytest
from backend.db import get_db_connection
from backend.pipeline.seed_db import run_seed_pipeline

def test_run_seed_pipeline():
    run_seed_pipeline()
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM players;")
        player_count = cur.fetchone()[0]
        assert player_count > 100
        
        cur.execute("SELECT COUNT(*) FROM galaxy_nodes;")
        nodes_count = cur.fetchone()[0]
        assert nodes_count > 100
        
        cur.execute("SELECT COUNT(*) FROM player_career_trajectories;")
        traj_count = cur.fetchone()[0]
        assert traj_count > 100
    conn.close()
