import os
import pytest
from backend.pipeline.feature_extractor import extract_all_seasons_data

def test_feature_extraction():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
    season_df, mv_df, career_df = extract_all_seasons_data(data_dir)
    
    assert not season_df.empty
    assert not mv_df.empty
    assert not career_df.empty
    
    # Check essential columns exist
    required_cols = [
        'player_id', 'name', 'position', 'team', 'minutes_played',
        'goals_per_90', 'assists_per_90', 'xg_per_90', 'xa_per_90',
        'key_passes_per_90', 'successful_dribbles_per_90', 'tackles_won_per_90',
        'interceptions_per_90', 'pass_completion_pct'
    ]
    for col in required_cols:
        assert col in career_df.columns
        
    # Check that minutes played threshold is enforced (>= 450 minutes)
    assert (career_df['minutes_played'] >= 450).all()
