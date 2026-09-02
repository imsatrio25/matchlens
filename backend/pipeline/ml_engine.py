import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics.pairwise import cosine_similarity
import umap

FEATURE_COLUMNS = [
    'goals_per_90', 'assists_per_90', 'xg_per_90', 'xa_per_90',
    'shots_per_90', 'shots_on_target_pct', 'key_passes_per_90',
    'through_balls_per_90', 'successful_dribbles_per_90', 'forward_passes_per_90',
    'pass_completion_pct', 'touches_in_box_per_90', 'tackles_won_per_90',
    'interceptions_per_90', 'recoveries_per_90', 'aerial_duels_won_pct',
    'losses_of_possession_per_90'
]

CLUSTER_LABELS = {
    0: "Isolated Box Finishers",
    1: "Elite Inverted Creators & Wingers",
    2: "Deep-Lying Tempo Playmakers",
    3: "High-Energy Box-to-Box Engines",
    4: "Ball-Carrying Attacking Midfielders",
    5: "Aggressive Ball-Playing Center-Backs",
    6: "Overlapping / Dynamic Full-Backs",
    7: "Commanding Sweeper-Keepers"
}

def compute_galaxy_manifold_and_residuals(career_df: pd.DataFrame, season_df: pd.DataFrame):
    df = career_df.copy()
    X = df[FEATURE_COLUMNS].fillna(0).values
    
    # 1. Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 2. UMAP 3D Projection — native spread for airier voids (was 15/0.18 dense)
    reducer = umap.UMAP(
        n_components=3,
        n_neighbors=12,
        min_dist=0.45,
        metric='cosine',
        random_state=42
    )
    coords_3d = reducer.fit_transform(X_scaled)
    df['coord_x'] = np.round(coords_3d[:, 0], 4)
    df['coord_y'] = np.round(coords_3d[:, 1], 4)
    df['coord_z'] = np.round(coords_3d[:, 2], 4)
    
    # 3. Tactical Cluster Assignment
    # Rule/Position-assisted heuristic clustering based on primary dimensions
    cluster_ids = []
    for idx, row in df.iterrows():
        pos = str(row['position']).lower()
        if 'goalkeeper' in pos:
            c_id = 7
        elif 'defender' in pos:
            if row['tackles_won_per_90'] > 1.8 or row['aerial_duels_won_pct'] > 60:
                c_id = 5  # Ball-Playing CB
            else:
                c_id = 6  # Full-Back
        elif 'midfielder' in pos:
            if row['key_passes_per_90'] > 1.8 or row['goals_per_90'] > 0.3:
                c_id = 4  # Attacking Midfielder
            elif row['recoveries_per_90'] > 5.5:
                c_id = 3  # Box-to-Box
            else:
                c_id = 2  # Deep-Lying Playmaker
        else:  # Forward
            if row['touches_in_box_per_90'] > 5.5 and row['key_passes_per_90'] < 1.4:
                c_id = 0  # Box Finisher
            else:
                c_id = 1  # Inverted Winger / Creator
        cluster_ids.append(c_id)
        
    df['cluster_id'] = cluster_ids
    df['cluster_label'] = df['cluster_id'].map(CLUSTER_LABELS)
    
    # 4. Fair-Value Residual Regression Model
    mv_actual = df['market_value_eur'].values
    y_log = np.log1p(np.maximum(mv_actual, 1_000_000))
    
    reg_model = HistGradientBoostingRegressor(max_iter=150, random_state=42, min_samples_leaf=5)
    reg_model.fit(X_scaled, y_log)
    
    pred_log = reg_model.predict(X_scaled)
    pred_mv = np.expm1(pred_log)
    
    df['actual_market_value_eur'] = mv_actual.astype(int)
    df['predicted_market_value_eur'] = np.round(pred_mv).astype(int)
    df['value_residual_eur'] = df['predicted_market_value_eur'] - df['actual_market_value_eur']
    
    # Value efficiency score 0-100
    res_scaler = RobustScaler()
    res_scaled = res_scaler.fit_transform(df[['value_residual_eur']].values).flatten()
    df['value_efficiency_score'] = np.round(1.0 / (1.0 + np.exp(-res_scaled)) * 100, 1)
    # ponytail: fixed 12M threshold never triggered (max residual ~0.9M on 848 players) -> use top 15% residuals as gems
    gem_cutoff = float(df['value_residual_eur'].quantile(0.85))
    df['is_undervalued_gem'] = df['value_residual_eur'] >= gem_cutoff
    
    # 5. High-Dimensional Cosine Similarity Matrix (Top-5 Style Twins)
    sim_matrix = cosine_similarity(X_scaled)
    nearest_neighbors_list = []
    
    for i in range(len(df)):
        sim_scores = sim_matrix[i]
        # Sort descending, exclude self (index i)
        ranked_indices = np.argsort(sim_scores)[::-1]
        ranked_indices = [idx for idx in ranked_indices if idx != i][:5]
        
        twins = []
        for idx in ranked_indices:
            twin_row = df.iloc[idx]
            twins.append({
                "player_id": str(twin_row['player_id']),
                "name": str(twin_row['name']),
                "team": str(twin_row['team']),
                "position": str(twin_row['position']),
                "similarity_score": round(float(sim_scores[idx]) * 100, 1),
                "market_value_eur": int(twin_row['market_value_eur']),
                "value_residual_eur": int(twin_row['value_residual_eur'])
            })
        nearest_neighbors_list.append(twins)
        
    df['nearest_neighbors'] = nearest_neighbors_list
    
    # 6. Radar Percentiles for 5 Skill Pillars (Shooting, Creation, Progression, Defense, Retention)
    shooting_raw = df['goals_per_90'] * 0.5 + df['shots_per_90'] * 0.3 + df['shots_on_target_pct'] * 0.2
    creation_raw = df['assists_per_90'] * 0.5 + df['key_passes_per_90'] * 0.3 + df['through_balls_per_90'] * 0.2
    progression_raw = df['successful_dribbles_per_90'] * 0.5 + df['forward_passes_per_90'] * 0.5
    defense_raw = df['tackles_won_per_90'] * 0.4 + df['interceptions_per_90'] * 0.3 + df['recoveries_per_90'] * 0.3
    retention_raw = df['pass_completion_pct'] * 0.7 - df['losses_of_possession_per_90'] * 0.3
    
    def to_percentile(series):
        return np.round(series.rank(pct=True) * 100).astype(int)
        
    df['radar_shooting'] = to_percentile(shooting_raw)
    df['radar_creation'] = to_percentile(creation_raw)
    df['radar_progression'] = to_percentile(progression_raw)
    df['radar_defense'] = to_percentile(defense_raw)
    df['radar_retention'] = to_percentile(retention_raw)
    
    radar_list = []
    for _, row in df.iterrows():
        radar_list.append({
            "shooting": int(row['radar_shooting']),
            "creation": int(row['radar_creation']),
            "progression": int(row['radar_progression']),
            "defense": int(row['radar_defense']),
            "retention": int(row['radar_retention'])
        })
    df['radar_percentiles'] = radar_list
    
    # 7. Compute Historical Seasonal Trajectories
    season_trajectories = []
    seasons_sorted = sorted(season_df['season'].unique())
    season_order_map = {s: i for i, s in enumerate(seasons_sorted)}
    
    valid_pids = set(df['player_id'])
    filtered_seasons = season_df[season_df['player_id'].isin(valid_pids)].copy()
    
    if not filtered_seasons.empty:
        s_X = filtered_seasons[FEATURE_COLUMNS].fillna(0).values
        s_X_scaled = scaler.transform(s_X)
        s_coords = reducer.transform(s_X_scaled)
        
        filtered_seasons['coord_x'] = np.round(s_coords[:, 0], 4)
        filtered_seasons['coord_y'] = np.round(s_coords[:, 1], 4)
        filtered_seasons['coord_z'] = np.round(s_coords[:, 2], 4)
        filtered_seasons['season_order'] = filtered_seasons['season'].map(season_order_map)
        
        for _, s_row in filtered_seasons.iterrows():
            season_trajectories.append({
                "player_id": str(s_row['player_id']),
                "season": str(s_row['season']),
                "season_order": int(s_row['season_order']),
                "coord_x": float(s_row['coord_x']),
                "coord_y": float(s_row['coord_y']),
                "coord_z": float(s_row['coord_z']),
                "market_value_eur": int(df.loc[df['player_id'] == s_row['player_id'], 'market_value_eur'].values[0] if len(df.loc[df['player_id'] == s_row['player_id']]) > 0 else 0),
                "minutes_played": int(s_row['minutes_played']),
                "xg_per_90": float(s_row['xg_per_90']),
                "xa_per_90": float(s_row['xa_per_90'])
            })
            
    trajectories_df = pd.DataFrame(season_trajectories)
    return df, trajectories_df
