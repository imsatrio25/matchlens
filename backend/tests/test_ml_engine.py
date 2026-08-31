import os
import pytest
from backend.pipeline.feature_extractor import extract_all_seasons_data
from backend.pipeline.ml_engine import compute_galaxy_manifold_and_residuals

def test_ml_manifold_and_residuals():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
    season_df, mv_df, career_df = extract_all_seasons_data(data_dir)
    
    galaxy_nodes_df, trajectories_df = compute_galaxy_manifold_and_residuals(career_df, season_df)
    
    assert not galaxy_nodes_df.empty
    assert len(galaxy_nodes_df) == len(career_df)
    
    # Check 3D coordinates
    assert 'coord_x' in galaxy_nodes_df.columns
    assert 'coord_y' in galaxy_nodes_df.columns
    assert 'coord_z' in galaxy_nodes_df.columns
    
    # Check Moneyball residual fields
    assert 'predicted_market_value_eur' in galaxy_nodes_df.columns
    assert 'value_residual_eur' in galaxy_nodes_df.columns
    assert 'value_efficiency_score' in galaxy_nodes_df.columns
    assert 'is_undervalued_gem' in galaxy_nodes_df.columns
    
    # Check KNN twins and radar percentiles
    assert 'nearest_neighbors' in galaxy_nodes_df.columns
    assert 'radar_percentiles' in galaxy_nodes_df.columns
    sample_neighbors = galaxy_nodes_df.iloc[0]['nearest_neighbors']
    assert isinstance(sample_neighbors, list)
    assert len(sample_neighbors) > 0
    assert not trajectories_df.empty
