import os
import json
import pandas as pd
import psycopg2.extras
from backend.db import init_db, get_db_connection
from backend.pipeline.feature_extractor import extract_all_seasons_data
from backend.pipeline.ml_engine import compute_galaxy_manifold_and_residuals

def run_seed_pipeline(data_dir=None):
    if data_dir is None:
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
        
    print("1. Initializing database schema...")
    init_db()
    
    print("2. Extracting seasonal and career features...")
    season_df, mv_df, career_df = extract_all_seasons_data(data_dir)
    
    print("3. Computing 3D UMAP manifold, Fair-Value residuals, and KNN twins...")
    galaxy_nodes_df, trajectories_df = compute_galaxy_manifold_and_residuals(career_df, season_df)
    
    print("4. Persisting into PostgreSQL database...")
    conn = get_db_connection()
    with conn.cursor() as cur:
        # Clear existing entries
        cur.execute("TRUNCATE TABLE player_career_trajectories, galaxy_nodes, market_value_history, player_season_stats, players CASCADE;")
        
        # 1. Insert Players
        player_records = [
            (str(row['player_id']), str(row['name']), str(row['team']), str(row['position']), int(row['market_value_eur']))
            for _, row in galaxy_nodes_df.iterrows()
        ]
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO players (player_id, name, team, position, current_market_value_eur)
            VALUES %s ON CONFLICT (player_id) DO UPDATE SET
                team = EXCLUDED.team,
                position = EXCLUDED.position,
                current_market_value_eur = EXCLUDED.current_market_value_eur;
            """,
            player_records
        )
        
        # 2. Insert Galaxy Nodes
        node_records = [
            (
                str(row['player_id']),
                float(row['coord_x']),
                float(row['coord_y']),
                float(row['coord_z']),
                int(row['cluster_id']),
                str(row['cluster_label']),
                int(row['actual_market_value_eur']),
                int(row['predicted_market_value_eur']),
                int(row['value_residual_eur']),
                float(row['value_efficiency_score']),
                bool(row['is_undervalued_gem']),
                json.dumps(row['nearest_neighbors']),
                json.dumps(row['radar_percentiles'])
            )
            for _, row in galaxy_nodes_df.iterrows()
        ]
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO galaxy_nodes (
                player_id, coord_x, coord_y, coord_z, cluster_id, cluster_label,
                actual_market_value_eur, predicted_market_value_eur, value_residual_eur,
                value_efficiency_score, is_undervalued_gem, nearest_neighbors, radar_percentiles
            ) VALUES %s;
            """,
            node_records
        )
        
        # 3. Insert Seasonal Stats
        valid_pids = set(galaxy_nodes_df['player_id'])
        season_records = [
            (
                str(row['player_id']), str(row['season']), int(row['appearances']), int(row['minutes_played']),
                float(row['goals_per_90']), float(row['assists_per_90']), float(row['xg_per_90']), float(row['xa_per_90']),
                float(row['shots_per_90']), float(row['shots_on_target_pct']), float(row['key_passes_per_90']),
                float(row['through_balls_per_90']), float(row['successful_dribbles_per_90']), float(row['forward_passes_per_90']),
                float(row['pass_completion_pct']), float(row['touches_in_box_per_90']), float(row['tackles_won_per_90']),
                float(row['interceptions_per_90']), float(row['recoveries_per_90']), float(row['aerial_duels_won_pct']),
                float(row['losses_of_possession_per_90'])
            )
            for _, row in season_df[season_df['player_id'].isin(valid_pids)].iterrows()
        ]
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO player_season_stats (
                player_id, season, appearances, minutes_played, goals_per_90, assists_per_90,
                xg_per_90, xa_per_90, shots_per_90, shots_on_target_pct, key_passes_per_90,
                through_balls_per_90, successful_dribbles_per_90, forward_passes_per_90,
                pass_completion_pct, touches_in_box_per_90, tackles_won_per_90,
                interceptions_per_90, recoveries_per_90, aerial_duels_won_pct, losses_of_possession_per_90
            ) VALUES %s ON CONFLICT (player_id, season) DO NOTHING;
            """,
            season_records
        )
        
        # 4. Insert Trajectories
        if not trajectories_df.empty:
            traj_records = [
                (
                    str(row['player_id']), str(row['season']), int(row['season_order']),
                    float(row['coord_x']), float(row['coord_y']), float(row['coord_z']),
                    int(row['market_value_eur']), int(row['minutes_played']),
                    float(row['xg_per_90']), float(row['xa_per_90'])
                )
                for _, row in trajectories_df.iterrows()
            ]
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO player_career_trajectories (
                    player_id, season, season_order, coord_x, coord_y, coord_z,
                    market_value_eur, minutes_played, xg_per_90, xa_per_90
                ) VALUES %s;
                """,
                traj_records
            )
            
        # 5. Insert Market Value History if present
        if not mv_df.empty:
            name_to_pid = {str(row['name']).lower(): str(row['player_id']) for _, row in galaxy_nodes_df.iterrows()}
            mv_records = []
            for _, row in mv_df.iterrows():
                p_name_lower = str(row.get('player_name', '')).lower()
                if p_name_lower in name_to_pid and pd.notna(row.get('valuation_date')):
                    val_date = pd.to_datetime(row['valuation_date']).date()
                    club = str(row.get('club', ''))
                    mv_records.append((
                        name_to_pid[p_name_lower],
                        val_date,
                        int(row['market_value_eur']),
                        club
                    ))
            if mv_records:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO market_value_history (
                        player_id, valuation_date, market_value_eur, club
                    ) VALUES %s;
                    """,
                    mv_records
                )
                
        conn.commit()
    conn.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    run_seed_pipeline()
