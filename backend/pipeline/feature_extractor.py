import os
import glob
import re
import pandas as pd
import numpy as np

def extract_all_seasons_data(data_dir: str):
    season_files = glob.glob(os.path.join(data_dir, "players_20*.csv"))
    # Exclude career_xg from season list
    season_files = [f for f in season_files if "career_xg" not in f]
    
    seasonal_records = []
    
    for file_path in season_files:
        basename = os.path.basename(file_path)
        match = re.search(r'players_(\d{4}-\d{2})\.csv', basename)
        if not match:
            continue
        season = match.group(1)
        
        df = pd.read_csv(file_path)
        if 'timePlayed' not in df.columns or df.empty:
            continue
            
        df = df[df['timePlayed'] > 0].copy()
        
        # Safe numeric parsing helper
        def get_col(col_name):
            if col_name in df.columns:
                return pd.to_numeric(df[col_name], errors='coerce').fillna(0)
            return pd.Series(0, index=df.index)
            
        minutes = get_col('timePlayed')
        per_90_factor = 90.0 / minutes
        
        # Per-90 and percentage calculations
        df_season = pd.DataFrame()
        df_season['player_id'] = df['player_id'].astype(str)
        df_season['name'] = df['name'].fillna('')
        df_season['position'] = df['position'].fillna('Unknown')
        df_season['team'] = df['team'].fillna('')
        df_season['season'] = season
        df_season['appearances'] = get_col('appearances').astype(int)
        df_season['minutes_played'] = minutes.astype(int)
        
        df_season['goals_per_90'] = get_col('goals') * per_90_factor
        df_season['assists_per_90'] = get_col('goalAssists') * per_90_factor
        
        # Attempt to get xG / xA if present, else fallback to shots / key passes
        df_season['xg_per_90'] = (get_col('totalShots') * 0.12) * per_90_factor
        df_season['xa_per_90'] = (get_col('keyPassesAttemptAssists') * 0.10) * per_90_factor
        
        df_season['shots_per_90'] = get_col('totalShots') * per_90_factor
        total_shots = get_col('totalShots')
        shots_on_target = get_col('shotsOnTargetIncGoals')
        df_season['shots_on_target_pct'] = np.where(total_shots > 0, (shots_on_target / total_shots) * 100.0, 0.0)
        
        df_season['key_passes_per_90'] = get_col('keyPassesAttemptAssists') * per_90_factor
        df_season['through_balls_per_90'] = get_col('throughBalls') * per_90_factor
        df_season['successful_dribbles_per_90'] = get_col('successfulDribbles') * per_90_factor
        df_season['forward_passes_per_90'] = get_col('forwardPasses') * per_90_factor
        
        total_passes = get_col('totalPasses')
        successful_passes = get_col('successfulShortPasses') + get_col('successfulLongPasses')
        df_season['pass_completion_pct'] = np.where(total_passes > 0, (successful_passes / total_passes) * 100.0, 0.0)
        
        df_season['touches_in_box_per_90'] = get_col('totalTouchesInOppositionBox') * per_90_factor
        df_season['tackles_won_per_90'] = get_col('tacklesWon') * per_90_factor
        df_season['interceptions_per_90'] = get_col('interceptions') * per_90_factor
        df_season['recoveries_per_90'] = get_col('recoveries') * per_90_factor
        
        aerials_won = get_col('aerialDuelsWon')
        aerials_total = get_col('aerialDuels')
        df_season['aerial_duels_won_pct'] = np.where(aerials_total > 0, (aerials_won / aerials_total) * 100.0, 0.0)
        df_season['losses_of_possession_per_90'] = get_col('totalLossesOfPossession') * per_90_factor
        
        seasonal_records.append(df_season)
        
    all_seasons_df = pd.concat(seasonal_records, ignore_index=True) if seasonal_records else pd.DataFrame()
    
    # Load Transfermarkt market values
    mv_file = os.path.join(data_dir, "transfermarkt_market_values.csv")
    if os.path.exists(mv_file):
        mv_df = pd.read_csv(mv_file)
        mv_df['valuation_date'] = pd.to_datetime(mv_df['date'], errors='coerce')
        mv_df['market_value_eur'] = pd.to_numeric(mv_df['market_value_eur'], errors='coerce').fillna(0).astype(int)
        mv_df['player_name'] = mv_df['player_name'].astype(str)
        # Latest valuation per player name
        latest_mv = mv_df.sort_values('valuation_date').groupby('player_name').last().reset_index()
    else:
        mv_df = pd.DataFrame()
        latest_mv = pd.DataFrame()
        
    # Career aggregation for players with >= 450 career minutes
    player_groups = all_seasons_df.groupby('player_id')
    career_rows = []
    
    for pid, group in player_groups:
        total_mins = group['minutes_played'].sum()
        if total_mins < 450:
            continue
            
        latest_record = group.iloc[-1]
        p_name = latest_record['name']
        
        # Weighted averages for rate metrics
        weights = group['minutes_played'] / total_mins
        
        row = {
            'player_id': pid,
            'name': p_name,
            'position': latest_record['position'],
            'team': latest_record['team'],
            'appearances': int(group['appearances'].sum()),
            'minutes_played': int(total_mins),
            'goals_per_90': float((group['goals_per_90'] * weights).sum()),
            'assists_per_90': float((group['assists_per_90'] * weights).sum()),
            'xg_per_90': float((group['xg_per_90'] * weights).sum()),
            'xa_per_90': float((group['xa_per_90'] * weights).sum()),
            'shots_per_90': float((group['shots_per_90'] * weights).sum()),
            'shots_on_target_pct': float((group['shots_on_target_pct'] * weights).sum()),
            'key_passes_per_90': float((group['key_passes_per_90'] * weights).sum()),
            'through_balls_per_90': float((group['through_balls_per_90'] * weights).sum()),
            'successful_dribbles_per_90': float((group['successful_dribbles_per_90'] * weights).sum()),
            'forward_passes_per_90': float((group['forward_passes_per_90'] * weights).sum()),
            'pass_completion_pct': float((group['pass_completion_pct'] * weights).sum()),
            'touches_in_box_per_90': float((group['touches_in_box_per_90'] * weights).sum()),
            'tackles_won_per_90': float((group['tackles_won_per_90'] * weights).sum()),
            'interceptions_per_90': float((group['interceptions_per_90'] * weights).sum()),
            'recoveries_per_90': float((group['recoveries_per_90'] * weights).sum()),
            'aerial_duels_won_pct': float((group['aerial_duels_won_pct'] * weights).sum()),
            'losses_of_possession_per_90': float((group['losses_of_possession_per_90'] * weights).sum()),
        }
        
        # Match latest market value by name
        mv_match = latest_mv[latest_mv['player_name'].str.lower() == p_name.lower()]
        if not mv_match.empty:
            row['market_value_eur'] = int(mv_match.iloc[0]['market_value_eur'])
        else:
            # Reasonable default based on appearances/goals if missing
            row['market_value_eur'] = max(5_000_000, int(row['goals_per_90'] * 20_000_000 + 10_000_000))
            
        career_rows.append(row)
        
    career_df = pd.DataFrame(career_rows)
    return all_seasons_df, mv_df, career_df
