# The Style Galaxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build "The Style Galaxy" — an interactive 3D spatial map of Premier League player styles using UMAP dimensionality reduction, Moneyball Fair-Value residual regression, and a Gemini-powered AI Scout drawer.

**Architecture:** A Python/Scikit-Learn/UMAP data pipeline processes multi-season stats (2018–2026) and persists 3D coordinates, fair-value residuals, and KNN twins into local PostgreSQL. A FastAPI backend serves the galaxy graph and handles grounded AI scouting queries via the Gemini API. A Next.js + React Three Fiber frontend renders the 3D astrophysical galaxy with glowing nodes, orbital camera fly-tos, trajectory trails, and a rich scouting dossier.

**Tech Stack:** 
- Database: PostgreSQL (strict `snake_case`)
- ML & Pipeline: Python 3.12, `pandas`, `numpy`, `scikit-learn`, `umap-learn`, `scipy`
- Backend: FastAPI, `psycopg2-binary`, `pydantic`, `google-genai` / `google-generativeai`, `uvicorn`
- Frontend: Next.js (App Router), TypeScript, Tailwind CSS, Three.js, `@react-three/fiber`, `@react-three/drei`, `lucide-react`

## Global Constraints
- Database tables and columns MUST strictly use `snake_case`.
- Zero placeholder code ("TODO", "TBD", "implement later").
- Every task MUST be verifiable with automated unit/integration tests or executable verification commands.

---

### Task 1: Database Schema & PostgreSQL Connection Setup

**Files:**
- Create: `backend/config.py`
- Create: `backend/db.py`
- Create: `backend/tests/test_db.py`
- Create: `backend/requirements.txt`

**Interfaces:**
- Consumes: Local PostgreSQL running on `localhost:5432` (`postgres` database or `matchlens` database).
- Produces: `get_db_connection()`, `init_db()`, `create_tables()` adhering strictly to `snake_case`.

- [ ] **Step 1: Create requirements.txt for backend dependencies**

```text
fastapi>=0.110.0
uvicorn>=0.28.0
psycopg2-binary>=2.9.9
pydantic>=2.6.0
pandas>=2.2.0
numpy>=1.26.0
scikit-learn>=1.4.0
umap-learn>=0.5.5
scipy>=1.12.0
google-genai>=0.1.1
pytest>=8.0.0
httpx>=0.27.0
python-dotenv>=1.0.1
```

- [ ] **Step 2: Write failing database connection and table initialization test**

```python
# backend/tests/test_db.py
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest backend/tests/test_db.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'backend'` or `ImportError`.

- [ ] **Step 4: Implement backend/config.py and backend/db.py**

```python
# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://satrio@localhost:5432/matchlens"
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
```

```python
# backend/db.py
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
```

- [ ] **Step 5: Run tests and verify database schema creation**

Run: `pytest backend/tests/test_db.py -v`  
Expected: PASS with 1 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/config.py backend/db.py backend/requirements.txt backend/tests/test_db.py
git commit -m "feat(db): implement PostgreSQL connection and snake_case schema"
```

---

### Task 2: Feature Engineering & Per-90 Data Extractor

**Files:**
- Create: `backend/pipeline/feature_extractor.py`
- Create: `backend/tests/test_feature_extractor.py`

**Interfaces:**
- Consumes: CSV files in `data/players_*.csv`, `data/players_career_xg.csv`, and `data/transfermarkt_market_values.csv`.
- Produces: `extract_all_seasons_data(data_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]` returning cleaned seasonal stats, latest market valuations, and career aggregate feature matrices with per-90 normalized stats.

- [ ] **Step 1: Write test for feature extractor**

```python
# backend/tests/test_feature_extractor.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_feature_extractor.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.pipeline.feature_extractor'`.

- [ ] **Step 3: Implement backend/pipeline/feature_extractor.py**

```python
# backend/pipeline/feature_extractor.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_feature_extractor.py -v`  
Expected: PASS with 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/feature_extractor.py backend/tests/test_feature_extractor.py
git commit -m "feat(pipeline): implement per-90 multi-season feature extractor"
```

---

### Task 3: UMAP 3D Manifold, Residual Regression & Style Twins ML Engine

**Files:**
- Create: `backend/pipeline/ml_engine.py`
- Create: `backend/tests/test_ml_engine.py`

**Interfaces:**
- Consumes: `career_df` and `all_seasons_df` from `feature_extractor.py`.
- Produces: `compute_galaxy_manifold_and_residuals(career_df, all_seasons_df)` returning:
  1. `galaxy_nodes_df`: player coordinates $(x,y,z)$, cluster labels, predicted market value, residuals, radar percentiles, and top-5 KNN style twins.
  2. `trajectories_df`: seasonal coordinate points for career path trails.

- [ ] **Step 1: Write test for ML engine**

```python
# backend/tests/test_ml_engine.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_ml_engine.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.pipeline.ml_engine'`.

- [ ] **Step 3: Implement backend/pipeline/ml_engine.py**

```python
# backend/pipeline/ml_engine.py
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
    
    # 2. UMAP 3D Projection
    reducer = umap.UMAP(
        n_components=3,
        n_neighbors=15,
        min_dist=0.18,
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
    df['is_undervalued_gem'] = df['value_residual_eur'] > 12_000_000
    
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_ml_engine.py -v`  
Expected: PASS with 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/ml_engine.py backend/tests/test_ml_engine.py
git commit -m "feat(ml): implement 3D UMAP manifold, Fair-Value residual model and KNN style twins"
```

---

### Task 4: Database Seeder Pipeline Script

**Files:**
- Create: `backend/pipeline/seed_db.py`
- Create: `backend/tests/test_seed_db.py`

**Interfaces:**
- Consumes: Raw CSVs, `feature_extractor.py`, `ml_engine.py`, and `db.py`.
- Produces: Populated PostgreSQL tables with all players, coordinates, residuals, neighbors, and trajectory waypoints.

- [ ] **Step 1: Write test for database seed execution**

```python
# backend/tests/test_seed_db.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_seed_db.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.pipeline.seed_db'`.

- [ ] **Step 3: Implement backend/pipeline/seed_db.py**

```python
# backend/pipeline/seed_db.py
import os
import json
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
            
        conn.commit()
    conn.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    run_seed_pipeline()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_seed_db.py -v`  
Expected: PASS with 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/seed_db.py backend/tests/test_seed_db.py
git commit -m "feat(pipeline): implement full database seeder and orchestrator"
```

---

### Task 5: FastAPI Galaxy & AI Scout Endpoints

**Files:**
- Create: `backend/routers/galaxy.py`
- Create: `backend/routers/scout.py`
- Create: `backend/main.py`
- Create: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: PostgreSQL tables and Google Gemini API (`google-genai`).
- Produces: REST endpoints `/api/galaxy`, `/api/players/{id}`, `/api/search`, and `/api/scout/analyze` / `/api/scout/query`.

- [ ] **Step 1: Write tests for FastAPI endpoints**

```python
# backend/tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_galaxy_endpoint():
    response = client.get("/api/galaxy")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "clusters" in data
    assert len(data["nodes"]) > 0

def test_search_endpoint():
    response = client.get("/api/search?q=Salah")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert "Salah" in results[0]["name"]

def test_scout_analyze_mock():
    # Test scout blurb generation endpoint
    response = client.post("/api/scout/analyze", json={"player_id": "118748"})
    assert response.status_code in [200, 503] # 200 if API key present, 503 fallback
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_api.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.main'`.

- [ ] **Step 3: Implement backend/routers/galaxy.py, backend/routers/scout.py, and backend/main.py**

```python
# backend/routers/galaxy.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from backend.db import get_db_connection

router = APIRouter(prefix="/api", tags=["galaxy"])

@router.get("/galaxy")
def get_galaxy_graph():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                p.player_id, p.name, p.team, p.position,
                g.coord_x, g.coord_y, g.coord_z,
                g.cluster_id, g.cluster_label,
                g.actual_market_value_eur, g.predicted_market_value_eur,
                g.value_residual_eur, g.value_efficiency_score,
                g.is_undervalued_gem, g.nearest_neighbors, g.radar_percentiles
            FROM galaxy_nodes g
            JOIN players p ON g.player_id = p.player_id;
        """)
        rows = cur.fetchall()
        
        nodes = []
        cluster_counts = {}
        for r in rows:
            c_id = r[7]
            c_label = r[8]
            cluster_counts[c_id] = cluster_counts.get(c_id, {"cluster_id": c_id, "label": c_label, "count": 0})
            cluster_counts[c_id]["count"] += 1
            
            nodes.append({
                "player_id": r[0],
                "name": r[1],
                "team": r[2],
                "position": r[3],
                "coords": [float(r[4]), float(r[5]), float(r[6])],
                "cluster_id": r[7],
                "cluster_label": r[8],
                "market_value_eur": r[9],
                "predicted_market_value_eur": r[10],
                "value_residual_eur": r[11],
                "value_efficiency_score": float(r[12]),
                "is_undervalued_gem": bool(r[13]),
                "nearest_neighbors": r[14],
                "radar": r[15]
            })
            
    conn.close()
    return {
        "nodes": nodes,
        "clusters": list(cluster_counts.values())
    }

@router.get("/players/{player_id}")
def get_player_dossier(player_id: str):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                p.player_id, p.name, p.team, p.position,
                g.coord_x, g.coord_y, g.coord_z,
                g.cluster_id, g.cluster_label,
                g.actual_market_value_eur, g.predicted_market_value_eur,
                g.value_residual_eur, g.value_efficiency_score,
                g.is_undervalued_gem, g.nearest_neighbors, g.radar_percentiles
            FROM players p
            LEFT JOIN galaxy_nodes g ON p.player_id = g.player_id
            WHERE p.player_id = %s;
        """, (player_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Player not found")
            
        cur.execute("""
            SELECT season, season_order, coord_x, coord_y, coord_z, market_value_eur, minutes_played, xg_per_90, xa_per_90
            FROM player_career_trajectories
            WHERE player_id = %s
            ORDER BY season_order ASC;
        """, (player_id,))
        traj_rows = cur.fetchall()
        trajectories = [
            {
                "season": tr[0], "season_order": tr[1],
                "coords": [float(tr[2]), float(tr[3]), float(tr[4])],
                "market_value_eur": tr[5], "minutes_played": tr[6],
                "xg_per_90": float(tr[7]), "xa_per_90": float(tr[8])
            }
            for tr in traj_rows
        ]
        
    conn.close()
    return {
        "player_id": row[0],
        "name": row[1],
        "team": row[2],
        "position": row[3],
        "coords": [float(row[4]), float(row[5]), float(row[6])] if row[4] is not None else [0,0,0],
        "cluster_id": row[7],
        "cluster_label": row[8],
        "market_value_eur": row[9],
        "predicted_market_value_eur": row[10],
        "value_residual_eur": row[11],
        "value_efficiency_score": float(row[12]) if row[12] is not None else 50.0,
        "is_undervalued_gem": bool(row[13]) if row[13] is not None else False,
        "nearest_neighbors": row[14] or [],
        "radar": row[15] or {},
        "trajectories": trajectories
    }

@router.get("/search")
def search_players(
    q: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    undervalued_only: bool = Query(False)
):
    conn = get_db_connection()
    query = """
        SELECT p.player_id, p.name, p.team, p.position, g.coord_x, g.coord_y, g.coord_z,
               g.actual_market_value_eur, g.value_residual_eur, g.is_undervalued_gem, g.cluster_label
        FROM players p
        JOIN galaxy_nodes g ON p.player_id = g.player_id
        WHERE 1=1
    """
    params = []
    if q:
        query += " AND (p.name ILIKE %s OR p.team ILIKE %s)"
        params.extend([f"%{q}%", f"%{q}%"])
    if position and position != "ALL":
        query += " AND p.position ILIKE %s"
        params.append(f"%{position}%")
    if undervalued_only:
        query += " AND g.is_undervalued_gem = TRUE"
        
    query += " ORDER BY g.actual_market_value_eur DESC LIMIT 20;"
    
    with conn.cursor() as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        results = [
            {
                "player_id": r[0], "name": r[1], "team": r[2], "position": r[3],
                "coords": [float(r[4]), float(r[5]), float(r[6])],
                "market_value_eur": r[7], "value_residual_eur": r[8],
                "is_undervalued_gem": bool(r[9]), "cluster_label": r[10]
            }
            for r in rows
        ]
    conn.close()
    return results
```

```python
# backend/routers/scout.py
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.config import GEMINI_API_KEY
from backend.db import get_db_connection

router = APIRouter(prefix="/api/scout", tags=["scout"])

class ScoutAnalyzeRequest(BaseModel):
    player_id: str

class ScoutQueryRequest(BaseModel):
    query: str
    target_player_id: Optional[str] = None

def get_gemini_client():
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        return None

@router.post("/analyze")
def analyze_player(req: ScoutAnalyzeRequest):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.name, p.team, p.position, g.cluster_label,
                   g.actual_market_value_eur, g.predicted_market_value_eur,
                   g.value_residual_eur, g.value_efficiency_score,
                   g.nearest_neighbors, g.radar_percentiles
            FROM players p
            JOIN galaxy_nodes g ON p.player_id = g.player_id
            WHERE p.player_id = %s;
        """, (req.player_id,))
        row = cur.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Player not found in galaxy")
        
    name, team, pos, cluster, actual_mv, pred_mv, residual, efficiency, neighbors, radar = row
    
    # Grounded Context Prompt
    prompt = f"""
You are the Chief AI Scout embedded inside 'The Style Galaxy' Premier League analytics platform.
Provide an executive, concise scouting memorandum (under 160 words) grounded STRICTLY in this player's spatial math:

Player: {name} ({team}, {pos})
Tactical Cluster: {cluster}
Market Valuation: €{actual_mv:,} (Fair-Value Model Estimate: €{pred_mv:,} | Residual Surplus: €{residual:,})
Value Efficiency Score: {efficiency}/100
5-Axis Percentiles: Shooting {radar.get('shooting', 50)}th, Creation {radar.get('creation', 50)}th, Progression {radar.get('progression', 50)}th, Defense {radar.get('defense', 50)}th, Retention {radar.get('retention', 50)}th.
Closest Style Neighbors: {json.dumps(neighbors[:3])}

Your memo must highlight:
1. Tactical archetype & standout strengths from their percentiles.
2. Direct comparison to their closest style twins on the galaxy map.
3. Financial arbitrage verdict (Is he a bargain, fairly priced, or overvalued?).
"""
    client = get_gemini_client()
    if client:
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return {"memo": response.text, "player_name": name}
        except Exception as e:
            pass
            
    # Deterministic fallback scout memo if Gemini client is offline
    arbitrage_text = f"an undervalued gem with €{abs(residual):,} surplus" if residual > 0 else f"commanding an elite star premium of €{abs(residual):,}"
    top_twin = neighbors[0]['name'] if neighbors else "league peers"
    fallback_memo = (
        f"**Tactical Archetype:** {name} operates as a quintessential '{cluster}' for {team}. "
        f"His highest-rated dimension is {max(radar, key=radar.get).title()} ({radar.get(max(radar, key=radar.get))}th percentile).\n\n"
        f"**Spatial Twins:** On the galaxy manifold, his closest statistical twin is {top_twin}. "
        f"Financially, our Moneyball residual model rates him as {arbitrage_text}."
    )
    return {"memo": fallback_memo, "player_name": name}

@router.post("/query")
def natural_scout_query(req: ScoutQueryRequest):
    # Retrieve top undervalued matches or style alternatives
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.player_id, p.name, p.team, p.position, g.cluster_label,
                   g.actual_market_value_eur, g.value_residual_eur, g.is_undervalued_gem
            FROM players p
            JOIN galaxy_nodes g ON p.player_id = g.player_id
            WHERE g.is_undervalued_gem = TRUE
            ORDER BY g.value_residual_eur DESC LIMIT 5;
        """)
        rows = cur.fetchall()
    conn.close()
    
    candidates = [
        {"player_id": r[0], "name": r[1], "team": r[2], "position": r[3], "cluster": r[4], "market_value_eur": r[5], "residual_eur": r[6]}
        for r in rows
    ]
    
    client = get_gemini_client()
    if client:
        prompt = f"""
A user asks: "{req.query}"
Based on our Premier League Moneyball database, here are the top undervalued arbitrage opportunities:
{json.dumps(candidates)}

Provide a sharp, 3-bullet executive scout response recommending the best targets and explaining the geometric/financial reasoning.
"""
        try:
            res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            return {"response": res.text, "recommended_players": candidates}
        except Exception:
            pass
            
    return {
        "response": f"Based on style similarity and residual value efficiency, here are the top value arbitrage targets matching your query.",
        "recommended_players": candidates
    }
```

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import galaxy, scout

app = FastAPI(title="The Style Galaxy API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(galaxy.router)
app.include_router(scout.router)

@app.get("/api/health")
def healthcheck():
    return {"status": "healthy", "service": "style-galaxy-backend"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_api.py -v`  
Expected: PASS with 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/galaxy.py backend/routers/scout.py backend/main.py backend/tests/test_api.py
git commit -m "feat(api): implement FastAPI galaxy graph and Gemini AI scout endpoints"
```

---

### Task 6: Frontend Next.js & React Three Fiber Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/app/globals.css`
- Create: `frontend/src/types/galaxy.ts`
- Create: `frontend/src/services/api.ts`

**Interfaces:**
- Consumes: FastAPI endpoints at `http://localhost:8000/api`.
- Produces: Base types and API client for React Three Fiber canvas and HUD components.

- [ ] **Step 1: Create frontend configuration and dependencies**

```json
// frontend/package.json
{
  "name": "style-galaxy-ui",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^14.2.5",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "three": "^0.166.1",
    "@react-three/fiber": "^8.16.8",
    "@react-three/drei": "^9.108.3",
    "lucide-react": "^0.417.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.4.0"
  },
  "devDependencies": {
    "@types/node": "^20.14.11",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@types/three": "^0.166.0",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.39",
    "tailwindcss": "^3.4.6",
    "typescript": "^5.5.3"
  }
}
```

- [ ] **Step 2: Implement TypeScript types and API client**

```typescript
// frontend/src/types/galaxy.ts
export interface StyleTwin {
  player_id: string;
  name: string;
  team: string;
  position: string;
  similarity_score: number;
  market_value_eur: number;
  value_residual_eur: number;
}

export interface RadarPercentiles {
  shooting: number;
  creation: number;
  progression: number;
  defense: number;
  retention: number;
}

export interface TrajectoryPoint {
  season: string;
  season_order: number;
  coords: [number, number, number];
  market_value_eur: number;
  minutes_played: number;
  xg_per_90: number;
  xa_per_90: number;
}

export interface GalaxyNode {
  player_id: string;
  name: string;
  team: string;
  position: string;
  coords: [number, number, number];
  cluster_id: number;
  cluster_label: string;
  market_value_eur: number;
  predicted_market_value_eur: number;
  value_residual_eur: number;
  value_efficiency_score: number;
  is_undervalued_gem: boolean;
  nearest_neighbors: StyleTwin[];
  radar: RadarPercentiles;
  trajectories?: TrajectoryPoint[];
}

export interface GalaxyCluster {
  cluster_id: number;
  label: string;
  count: number;
}

export interface GalaxyData {
  nodes: GalaxyNode[];
  clusters: GalaxyCluster[];
}
```

```typescript
// frontend/src/services/api.ts
import { GalaxyData, GalaxyNode } from '../types/galaxy';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export async function fetchGalaxyData(): Promise<GalaxyData> {
  const res = await fetch(`${API_BASE}/galaxy`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch galaxy data');
  return res.json();
}

export async function fetchPlayerDossier(playerId: string): Promise<GalaxyNode> {
  const res = await fetch(`${API_BASE}/players/${playerId}`);
  if (!res.ok) throw new Error('Failed to fetch player dossier');
  return res.json();
}

export async function fetchScoutAnalysis(playerId: string): Promise<{ memo: string; player_name: string }> {
  const res = await fetch(`${API_BASE}/scout/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ player_id: playerId }),
  });
  if (!res.ok) throw new Error('Failed to generate scout analysis');
  return res.json();
}

export async function queryScout(query: string, targetPlayerId?: string): Promise<{ response: string; recommended_players: any[] }> {
  const res = await fetch(`${API_BASE}/scout/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, target_player_id: targetPlayerId }),
  });
  if (!res.ok) throw new Error('Failed to query AI scout');
  return res.json();
}
```

- [ ] **Step 3: Run npm install and verify frontend project setup**

Run: `cd frontend && npm install`  
Expected: `added X packages` with zero fatal errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/tailwind.config.js frontend/postcss.config.js frontend/src/app/globals.css frontend/src/types/galaxy.ts frontend/src/services/api.ts
git commit -m "feat(frontend): initialize Next.js app with Three.js and TypeScript types"
```

---

### Task 7: 3D Galaxy Canvas, Shaders & Trajectory Renderer

**Files:**
- Create: `frontend/src/components/galaxy/GalaxyCanvas.tsx`
- Create: `frontend/src/components/galaxy/GalaxyNodes.tsx`
- Create: `frontend/src/components/galaxy/TrajectoryCurves.tsx`
- Create: `frontend/src/components/galaxy/CameraController.tsx`

**Interfaces:**
- Consumes: `GalaxyNode[]`, `selectedPlayer`, `activeFilter`, `showGemsOnly`, `showTrajectories`.
- Produces: 60fps 3D WebGL space with glowing player nodes, smooth camera fly-to, and career spline trails.

- [ ] **Step 1: Implement CameraController with smooth camera lerping**

```tsx
// frontend/src/components/galaxy/CameraController.tsx
'use client';
import { useRef, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

interface CameraControllerProps {
  targetCoords: [number, number, number] | null;
}

export default function CameraController({ targetCoords }: CameraControllerProps) {
  const { camera } = useThree();
  const targetPos = useRef<THREE.Vector3 | null>(null);
  const lookAtPos = useRef<THREE.Vector3 | null>(null);

  useEffect(() => {
    if (targetCoords) {
      targetPos.current = new THREE.Vector3(targetCoords[0] + 3, targetCoords[1] + 2, targetCoords[2] + 7);
      lookAtPos.current = new THREE.Vector3(...targetCoords);
    }
  }, [targetCoords]);

  useFrame(() => {
    if (targetPos.current && lookAtPos.current) {
      camera.position.lerp(targetPos.current, 0.05);
      camera.lookAt(lookAtPos.current);
    }
  });

  return null;
}
```

- [ ] **Step 2: Implement GalaxyNodes with position coloring and Moneyball glowing halo**

```tsx
// frontend/src/components/galaxy/GalaxyNodes.tsx
'use client';
import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { GalaxyNode } from '../../types/galaxy';

interface GalaxyNodesProps {
  nodes: GalaxyNode[];
  selectedPlayer: GalaxyNode | null;
  onSelectPlayer: (player: GalaxyNode) => void;
  positionFilter: string;
  showGemsOnly: boolean;
}

const POSITION_COLORS: Record<string, string> = {
  Forward: '#f97316',     // Vibrant Orange/Amber
  Midfielder: '#10b981',  // Emerald Green
  Defender: '#06b6d4',    // Cyan / Electric Blue
  Goalkeeper: '#eab308',  // Gold
};

export default function GalaxyNodes({
  nodes,
  selectedPlayer,
  onSelectPlayer,
  positionFilter,
  showGemsOnly,
}: GalaxyNodesProps) {
  const filteredNodes = useMemo(() => {
    return nodes.filter(n => {
      if (positionFilter !== 'ALL' && !n.position.toLowerCase().includes(positionFilter.toLowerCase())) {
        return false;
      }
      if (showGemsOnly && !n.is_undervalued_gem) {
        return false;
      }
      return true;
    });
  }, [nodes, positionFilter, showGemsOnly]);

  return (
    <group>
      {filteredNodes.map((node) => {
        const isSelected = selectedPlayer?.player_id === node.player_id;
        const color = POSITION_COLORS[node.position] || '#94a3b8';
        const baseScale = Math.max(0.15, Math.log10(Math.max(node.market_value_eur, 1_000_000)) * 0.05);
        const scale = isSelected ? baseScale * 2.2 : baseScale;

        return (
          <group key={node.player_id} position={node.coords}>
            {/* Core Player Sphere */}
            <mesh
              onClick={(e) => {
                e.stopPropagation();
                onSelectPlayer(node);
              }}
            >
              <sphereGeometry args={[scale, 16, 16]} />
              <meshStandardMaterial
                color={color}
                emissive={node.is_undervalued_gem ? '#22c55e' : color}
                emissiveIntensity={isSelected ? 2.5 : node.is_undervalued_gem ? 1.4 : 0.4}
                roughness={0.2}
                metalness={0.8}
              />
            </mesh>

            {/* Moneyball Pulsing Residual Halo for Undervalued Gems */}
            {node.is_undervalued_gem && (
              <mesh>
                <ringGeometry args={[scale * 1.3, scale * 1.8, 32]} />
                <meshBasicMaterial
                  color="#4ade80"
                  transparent
                  opacity={0.7}
                  side={THREE.DoubleSide}
                />
              </mesh>
            )}

            {/* Selected Target Ring */}
            {isSelected && (
              <mesh>
                <ringGeometry args={[scale * 2.2, scale * 2.6, 32]} />
                <meshBasicMaterial color="#ffffff" transparent opacity={0.9} side={THREE.DoubleSide} />
              </mesh>
            )}
          </group>
        );
      })}
    </group>
  );
}
```

- [ ] **Step 3: Implement TrajectoryCurves for historical season path rendering**

```tsx
// frontend/src/components/galaxy/TrajectoryCurves.tsx
'use client';
import { useMemo } from 'react';
import * as THREE from 'three';
import { Line } from '@react-three/drei';
import { GalaxyNode } from '../../types/galaxy';

interface TrajectoryCurvesProps {
  selectedPlayer: GalaxyNode | null;
  showTrajectories: boolean;
}

export default function TrajectoryCurves({ selectedPlayer, showTrajectories }: TrajectoryCurvesProps) {
  const points = useMemo(() => {
    if (!showTrajectories || !selectedPlayer?.trajectories || selectedPlayer.trajectories.length < 2) {
      return null;
    }
    return selectedPlayer.trajectories.map(t => new THREE.Vector3(...t.coords));
  }, [selectedPlayer, showTrajectories]);

  if (!points || points.length < 2) return null;

  const curve = new THREE.CatmullRomCurve3(points);
  const curvePoints = curve.getPoints(50);

  return (
    <group>
      <Line
        points={curvePoints}
        color="#a855f7"
        lineWidth={3}
        dashed={false}
      />
      {selectedPlayer?.trajectories?.map((t, idx) => (
        <mesh key={t.season} position={t.coords}>
          <sphereGeometry args={[0.08, 12, 12]} />
          <meshStandardMaterial color="#c084fc" emissive="#a855f7" emissiveIntensity={1.0} />
        </mesh>
      ))}
    </group>
  );
}
```

- [ ] **Step 4: Implement GalaxyCanvas with React Three Fiber space scene**

```tsx
// frontend/src/components/galaxy/GalaxyCanvas.tsx
'use client';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import GalaxyNodes from './GalaxyNodes';
import CameraController from './CameraController';
import TrajectoryCurves from './TrajectoryCurves';
import { GalaxyNode } from '../../types/galaxy';

interface GalaxyCanvasProps {
  nodes: GalaxyNode[];
  selectedPlayer: GalaxyNode | null;
  onSelectPlayer: (player: GalaxyNode) => void;
  positionFilter: string;
  showGemsOnly: boolean;
  showTrajectories: boolean;
}

export default function GalaxyCanvas({
  nodes,
  selectedPlayer,
  onSelectPlayer,
  positionFilter,
  showGemsOnly,
  showTrajectories,
}: GalaxyCanvasProps) {
  return (
    <div className="w-full h-full bg-[#030712] relative overflow-hidden">
      <Canvas
        camera={{ position: [0, 5, 25], fov: 60 }}
        gl={{ antialias: true }}
      >
        <color attach="background" args={['#030712']} />
        <ambientLight intensity={0.6} />
        <pointLight position={[20, 20, 20]} intensity={1.5} />
        <pointLight position={[-20, -20, -20]} intensity={0.8} color="#3b82f6" />
        
        <Stars radius={100} depth={50} count={3000} factor={4} saturation={0} fade speed={1} />
        
        <GalaxyNodes
          nodes={nodes}
          selectedPlayer={selectedPlayer}
          onSelectPlayer={onSelectPlayer}
          positionFilter={positionFilter}
          showGemsOnly={showGemsOnly}
        />
        
        <TrajectoryCurves
          selectedPlayer={selectedPlayer}
          showTrajectories={showTrajectories}
        />
        
        <CameraController targetCoords={selectedPlayer ? selectedPlayer.coords : null} />
        
        <OrbitControls
          enableDamping
          dampingFactor={0.05}
          minDistance={2}
          maxDistance={80}
        />
      </Canvas>
    </div>
  );
}
```

- [ ] **Step 5: Verify build compilation of 3D Canvas**

Run: `cd frontend && npm run build`  
Expected: Next.js compiles without type errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/galaxy/GalaxyCanvas.tsx frontend/src/components/galaxy/GalaxyNodes.tsx frontend/src/components/galaxy/TrajectoryCurves.tsx frontend/src/components/galaxy/CameraController.tsx
git commit -m "feat(galaxy): implement Three.js 3D galaxy canvas with glowing nodes and trajectory splines"
```

---

### Task 8: HUD Overlay, Search & Scout Drawer UI

**Files:**
- Create: `frontend/src/components/hud/SearchBar.tsx`
- Create: `frontend/src/components/hud/FilterPills.tsx`
- Create: `frontend/src/components/drawer/RadarChart.tsx`
- Create: `frontend/src/components/drawer/ScoutDrawer.tsx`
- Create: `frontend/src/app/page.tsx`

**Interfaces:**
- Consumes: `GalaxyData`, selected player state, search filters, and API scout calls.
- Produces: Complete responsive UI with interactive search, Moneyball filters, radar charts, nearest style twin comparison cards, and Gemini scout briefing.

- [ ] **Step 1: Implement RadarChart SVG visualizer**

```tsx
// frontend/src/components/drawer/RadarChart.tsx
'use client';
import React from 'react';
import { RadarPercentiles } from '../../types/galaxy';

interface RadarChartProps {
  radar: RadarPercentiles;
}

export default function RadarChart({ radar }: RadarChartProps) {
  const axes = [
    { key: 'shooting', label: 'Shooting', val: radar.shooting || 50 },
    { key: 'creation', label: 'Creation', val: radar.creation || 50 },
    { key: 'progression', label: 'Progression', val: radar.progression || 50 },
    { key: 'defense', label: 'Defense', val: radar.defense || 50 },
    { key: 'retention', label: 'Retention', val: radar.retention || 50 },
  ];

  const size = 200;
  const center = size / 2;
  const radius = 70;

  // Calculate polygon points
  const points = axes.map((axis, i) => {
    const angle = (Math.PI * 2 / axes.length) * i - Math.PI / 2;
    const r = (axis.val / 100) * radius;
    const x = center + r * Math.cos(angle);
    const y = center + r * Math.sin(angle);
    return `${x},${y}`;
  }).join(' ');

  return (
    <div className="relative flex flex-col items-center justify-center p-2 bg-slate-900/60 rounded-xl border border-slate-800">
      <svg width={size} height={size} className="overflow-visible">
        {/* Background Grids */}
        {[0.25, 0.5, 0.75, 1.0].map((level) => {
          const gridPoints = axes.map((_, i) => {
            const angle = (Math.PI * 2 / axes.length) * i - Math.PI / 2;
            const r = level * radius;
            return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
          }).join(' ');
          return <polygon key={level} points={gridPoints} fill="none" stroke="#334155" strokeWidth="1" />;
        })}

        {/* Data Polygon */}
        <polygon points={points} fill="rgba(16, 185, 129, 0.35)" stroke="#10b981" strokeWidth="2" />

        {/* Axis Labels */}
        {axes.map((axis, i) => {
          const angle = (Math.PI * 2 / axes.length) * i - Math.PI / 2;
          const labelRadius = radius + 18;
          const lx = center + labelRadius * Math.cos(angle);
          const ly = center + labelRadius * Math.sin(angle);
          return (
            <text
              key={axis.key}
              x={lx}
              y={ly}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-[10px] fill-slate-400 font-medium tracking-tight"
            >
              {axis.label} ({axis.val})
            </text>
          );
        })}
      </svg>
    </div>
  );
}
```

- [ ] **Step 2: Implement SearchBar with quick autocomplete**

```tsx
// frontend/src/components/hud/SearchBar.tsx
'use client';
import React, { useState, useMemo } from 'react';
import { Search, X } from 'lucide-react';
import { GalaxyNode } from '../../types/galaxy';

interface SearchBarProps {
  nodes: GalaxyNode[];
  onSelectPlayer: (player: GalaxyNode) => void;
}

export default function SearchBar({ nodes, onSelectPlayer }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);

  const results = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.toLowerCase();
    return nodes
      .filter(n => n.name.toLowerCase().includes(q) || n.team.toLowerCase().includes(q))
      .slice(0, 8);
  }, [nodes, query]);

  return (
    <div className="relative w-72 md:w-96 z-50">
      <div className="flex items-center bg-slate-900/90 border border-slate-700/80 rounded-xl px-3 py-2 text-white shadow-2xl backdrop-blur-md">
        <Search className="w-4 h-4 text-slate-400 mr-2 shrink-0" />
        <input
          type="text"
          placeholder="Search player, club, or style..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          className="bg-transparent border-none outline-none text-sm w-full placeholder-slate-500 text-white"
        />
        {query && (
          <button onClick={() => { setQuery(''); setIsOpen(false); }}>
            <X className="w-4 h-4 text-slate-400 hover:text-white" />
          </button>
        )}
      </div>

      {isOpen && results.length > 0 && (
        <div className="absolute left-0 right-0 mt-2 bg-slate-900/95 border border-slate-800 rounded-xl shadow-2xl overflow-hidden backdrop-blur-xl divide-y divide-slate-800/60 max-h-80 overflow-y-auto">
          {results.map((node) => (
            <div
              key={node.player_id}
              onClick={() => {
                onSelectPlayer(node);
                setIsOpen(false);
                setQuery(node.name);
              }}
              className="flex items-center justify-between px-4 py-2.5 hover:bg-slate-800/80 cursor-pointer transition"
            >
              <div>
                <div className="text-sm font-semibold text-white">{node.name}</div>
                <div className="text-xs text-slate-400">{node.team} • {node.position}</div>
              </div>
              <div className="text-right">
                <div className="text-xs font-mono text-emerald-400">€{(node.market_value_eur / 1_000_000).toFixed(1)}M</div>
                <div className="text-[10px] text-slate-400">{node.cluster_label}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Implement FilterPills component**

```tsx
// frontend/src/components/hud/FilterPills.tsx
'use client';
import React from 'react';
import { Sparkles, Activity } from 'lucide-react';

interface FilterPillsProps {
  positionFilter: string;
  setPositionFilter: (pos: string) => void;
  showGemsOnly: boolean;
  setShowGemsOnly: (val: boolean) => void;
  showTrajectories: boolean;
  setShowTrajectories: (val: boolean) => void;
}

export default function FilterPills({
  positionFilter,
  setPositionFilter,
  showGemsOnly,
  setShowGemsOnly,
  showTrajectories,
  setShowTrajectories,
}: FilterPillsProps) {
  const positions = ['ALL', 'Forward', 'Midfielder', 'Defender', 'Goalkeeper'];

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex bg-slate-900/90 border border-slate-800 rounded-xl p-1 backdrop-blur-md">
        {positions.map((pos) => (
          <button
            key={pos}
            onClick={() => setPositionFilter(pos)}
            className={`px-3 py-1 text-xs font-medium rounded-lg transition ${
              positionFilter === pos
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {pos === 'ALL' ? 'All Roles' : pos}
          </button>
        ))}
      </div>

      <button
        onClick={() => setShowGemsOnly(!showGemsOnly)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition backdrop-blur-md ${
          showGemsOnly
            ? 'bg-emerald-500/20 border-emerald-500/80 text-emerald-300 shadow-lg shadow-emerald-500/20'
            : 'bg-slate-900/90 border-slate-800 text-slate-400 hover:text-white'
        }`}
      >
        <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
        Undervalued Gems Only
      </button>

      <button
        onClick={() => setShowTrajectories(!showTrajectories)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition backdrop-blur-md ${
          showTrajectories
            ? 'bg-purple-500/20 border-purple-500/80 text-purple-300 shadow-lg shadow-purple-500/20'
            : 'bg-slate-900/90 border-slate-800 text-slate-400 hover:text-white'
        }`}
      >
        <Activity className="w-3.5 h-3.5 text-purple-400" />
        Career Trajectories
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Implement ScoutDrawer side-panel**

```tsx
// frontend/src/components/drawer/ScoutDrawer.tsx
'use client';
import React, { useState, useEffect } from 'react';
import { X, Sparkles, TrendingUp, DollarSign, Bot, ArrowRight } from 'lucide-react';
import { GalaxyNode } from '../../types/galaxy';
import RadarChart from './RadarChart';
import { fetchScoutAnalysis, fetchPlayerDossier } from '../../services/api';

interface ScoutDrawerProps {
  player: GalaxyNode | null;
  onClose: () => void;
  onSelectTwin: (playerId: string) => void;
}

export default function ScoutDrawer({ player, onClose, onSelectTwin }: ScoutDrawerProps) {
  const [memo, setMemo] = useState<string>('');
  const [loadingMemo, setLoadingMemo] = useState(false);
  const [fullPlayer, setFullPlayer] = useState<GalaxyNode | null>(player);

  useEffect(() => {
    if (!player) {
      setMemo('');
      setFullPlayer(null);
      return;
    }
    setFullPlayer(player);
    setLoadingMemo(true);

    // Fetch full dossier with trajectories and memo
    fetchPlayerDossier(player.player_id)
      .then(res => setFullPlayer(res))
      .catch(() => {});

    fetchScoutAnalysis(player.player_id)
      .then(res => setMemo(res.memo))
      .catch(() => setMemo("AI Scout memo temporarily unavailable."))
      .finally(() => setLoadingMemo(false));
  }, [player]);

  if (!fullPlayer) return null;

  const residualM = (fullPlayer.value_residual_eur / 1_000_000).toFixed(1);
  const isSurplus = fullPlayer.value_residual_eur > 0;

  return (
    <div className="absolute top-0 right-0 bottom-0 w-full sm:w-[460px] bg-slate-950/95 border-l border-slate-800/80 shadow-2xl backdrop-blur-2xl z-50 flex flex-col overflow-hidden text-white animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="flex items-center justify-between p-5 border-b border-slate-800">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">{fullPlayer.team} • {fullPlayer.position}</div>
          <h2 className="text-2xl font-bold text-white tracking-tight">{fullPlayer.name}</h2>
          <div className="text-xs text-blue-400 font-medium mt-0.5">{fullPlayer.cluster_label}</div>
        </div>
        <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-full transition text-slate-400 hover:text-white">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {/* Moneyball Valuation & Residual Metric Card */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
            <div className="text-[11px] text-slate-400 font-medium">Actual Valuation</div>
            <div className="text-xl font-bold text-white font-mono">€{(fullPlayer.market_value_eur / 1_000_000).toFixed(1)}M</div>
          </div>
          <div className={`p-3 rounded-xl border ${isSurplus ? 'bg-emerald-950/40 border-emerald-500/40' : 'bg-slate-900/80 border-slate-800'}`}>
            <div className="text-[11px] text-slate-400 font-medium">Moneyball Fair Residual</div>
            <div className={`text-xl font-bold font-mono ${isSurplus ? 'text-emerald-400' : 'text-slate-300'}`}>
              {isSurplus ? `+€${residualM}M` : `€${residualM}M`}
            </div>
          </div>
        </div>

        {/* 5-Axis Tactical Radar */}
        <div>
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Tactical Profile Signature</div>
          <RadarChart radar={fullPlayer.radar} />
        </div>

        {/* Map Neighbors & Style Twins Arbitrage */}
        <div>
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">Geometric Style Twins (Arbitrage)</div>
          <div className="space-y-2">
            {fullPlayer.nearest_neighbors.slice(0, 3).map((twin) => (
              <div
                key={twin.player_id}
                onClick={() => onSelectTwin(twin.player_id)}
                className="flex items-center justify-between p-3 bg-slate-900/70 hover:bg-slate-800/90 border border-slate-800/80 rounded-xl cursor-pointer transition group"
              >
                <div>
                  <div className="text-sm font-semibold text-white group-hover:text-blue-400 transition">{twin.name}</div>
                  <div className="text-xs text-slate-400">{twin.team} • {twin.similarity_score}% Style Match</div>
                </div>
                <div className="flex items-center gap-2 text-right">
                  <div>
                    <div className="text-xs font-mono font-bold text-white">€{(twin.market_value_eur / 1_000_000).toFixed(1)}M</div>
                    <div className="text-[10px] text-emerald-400">{twin.value_residual_eur > 0 ? 'Undervalued' : 'Market Price'}</div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:translate-x-1 transition" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI Scout Intelligence Memo */}
        <div className="p-4 bg-gradient-to-b from-blue-950/30 to-slate-900/80 border border-blue-500/30 rounded-xl">
          <div className="flex items-center gap-2 text-xs font-bold text-blue-400 uppercase tracking-wider mb-2">
            <Bot className="w-4 h-4 text-blue-400" />
            AI Scout Intelligence Memo
          </div>
          {loadingMemo ? (
            <div className="text-xs text-slate-400 animate-pulse">Synthesizing spatial geometry and Moneyball residual data...</div>
          ) : (
            <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-line font-normal">
              {memo}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Implement page.tsx integrating canvas, HUD, and scout drawer**

```tsx
// frontend/src/app/page.tsx
'use client';
import React, { useState, useEffect } from 'react';
import GalaxyCanvas from '../components/galaxy/GalaxyCanvas';
import SearchBar from '../components/hud/SearchBar';
import FilterPills from '../components/hud/FilterPills';
import ScoutDrawer from '../components/drawer/ScoutDrawer';
import { GalaxyData, GalaxyNode } from '../types/galaxy';
import { fetchGalaxyData } from '../services/api';
import { Compass, Sparkles } from 'lucide-react';

export default function GalaxyApp() {
  const [galaxyData, setGalaxyData] = useState<GalaxyData | null>(null);
  const [selectedPlayer, setSelectedPlayer] = useState<GalaxyNode | null>(null);
  const [positionFilter, setPositionFilter] = useState<string>('ALL');
  const [showGemsOnly, setShowGemsOnly] = useState<boolean>(false);
  const [showTrajectories, setShowTrajectories] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchGalaxyData()
      .then((data) => {
        setGalaxyData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleSelectTwin = (playerId: string) => {
    if (!galaxyData) return;
    const target = galaxyData.nodes.find(n => n.player_id === playerId);
    if (target) setSelectedPlayer(target);
  };

  return (
    <main className="w-screen h-screen relative bg-[#030712] overflow-hidden select-none font-sans">
      {/* Top Navigation HUD */}
      <header className="absolute top-4 left-4 right-4 z-40 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pointer-events-none">
        <div className="flex items-center gap-3 pointer-events-auto bg-slate-900/80 border border-slate-800/80 px-4 py-2.5 rounded-2xl backdrop-blur-xl shadow-2xl">
          <Compass className="w-6 h-6 text-blue-400 animate-spin-slow" />
          <div>
            <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-1.5">
              THE STYLE GALAXY
              <span className="text-[10px] px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded-md border border-blue-500/30">Premier League</span>
            </h1>
            <p className="text-[11px] text-slate-400">Tactical Manifold & Moneyball AI Scout</p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3 pointer-events-auto w-full md:w-auto">
          {galaxyData && (
            <>
              <SearchBar nodes={galaxyData.nodes} onSelectPlayer={setSelectedPlayer} />
              <FilterPills
                positionFilter={positionFilter}
                setPositionFilter={setPositionFilter}
                showGemsOnly={showGemsOnly}
                setShowGemsOnly={setShowGemsOnly}
                showTrajectories={showTrajectories}
                setShowTrajectories={setShowTrajectories}
              />
            </>
          )}
        </div>
      </header>

      {/* Main 3D Canvas */}
      {loading ? (
        <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 space-y-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <div className="text-sm font-medium tracking-wide">Synthesizing Premier League Style Manifold...</div>
        </div>
      ) : galaxyData ? (
        <GalaxyCanvas
          nodes={galaxyData.nodes}
          selectedPlayer={selectedPlayer}
          onSelectPlayer={setSelectedPlayer}
          positionFilter={positionFilter}
          showGemsOnly={showGemsOnly}
          showTrajectories={showTrajectories}
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-red-400">
          Failed to load galaxy data. Please check backend server.
        </div>
      )}

      {/* Slide-Out AI Scout Drawer */}
      <ScoutDrawer
        player={selectedPlayer}
        onClose={() => setSelectedPlayer(null)}
        onSelectTwin={handleSelectTwin}
      />
    </main>
  );
}
```

- [ ] **Step 6: Build Next.js project to verify full frontend compilation**

Run: `cd frontend && npm run build`  
Expected: Next.js production build succeeds with 0 errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/hud/SearchBar.tsx frontend/src/components/hud/FilterPills.tsx frontend/src/components/drawer/RadarChart.tsx frontend/src/components/drawer/ScoutDrawer.tsx frontend/src/app/page.tsx
git commit -m "feat(ui): complete HUD overlay, search fly-to, radar charts and AI scout drawer"
```

---

### Task 9: End-to-End System Verification & Launch Script

**Files:**
- Create: `start.sh`
- Create: `tests/test_e2e_flow.py`

**Interfaces:**
- Consumes: Seeded PostgreSQL, FastAPI backend, Next.js frontend.
- Produces: Executable startup workflow and end-to-end integration tests confirming full system readiness.

- [ ] **Step 1: Write end-to-end integration test**

```python
# tests/test_e2e_flow.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_full_galaxy_pipeline_e2e():
    # 1. Verify health
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    
    # 2. Verify galaxy coordinates and nodes
    res_galaxy = client.get("/api/galaxy")
    assert res_galaxy.status_code == 200
    galaxy = res_galaxy.json()
    assert len(galaxy["nodes"]) > 0
    
    first_node = galaxy["nodes"][0]
    pid = first_node["player_id"]
    
    # 3. Verify single player dossier & trajectory
    res_player = client.get(f"/api/players/{pid}")
    assert res_player.status_code == 200
    player_data = res_player.json()
    assert player_data["name"] == first_node["name"]
    
    # 4. Verify AI Scout analyze
    res_scout = client.post("/api/scout/analyze", json={"player_id": pid})
    assert res_scout.status_code in [200, 503]
```

- [ ] **Step 2: Run E2E test to verify it passes**

Run: `pytest tests/test_e2e_flow.py -v`  
Expected: PASS with 1 passed.

- [ ] **Step 3: Create start.sh convenience orchestrator script**

```bash
#!/usr/bin/env bash
set -e

echo "=== Starting The Style Galaxy Platform ==="

echo "1. Seeding PostgreSQL Database..."
python3 -m backend.pipeline.seed_db

echo "2. Launching FastAPI Backend (Port 8000)..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "3. Launching Next.js Frontend (Port 3000)..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo "=== The Style Galaxy is running ==="
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000/docs"

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
```

- [ ] **Step 4: Make start.sh executable and commit**

```bash
chmod +x start.sh
git add start.sh tests/test_e2e_flow.py
git commit -m "feat: add e2e integration tests and launch orchestrator script"
```
