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
    
    actual_mv = int(actual_mv) if actual_mv is not None else 0
    pred_mv = int(pred_mv) if pred_mv is not None else 0
    residual = int(residual) if residual is not None else 0
    efficiency = float(efficiency) if efficiency is not None else 50.0
    if not isinstance(neighbors, list):
        neighbors = json.loads(neighbors) if isinstance(neighbors, str) else []
    if not isinstance(radar, dict):
        radar = json.loads(radar) if isinstance(radar, str) else {}
    
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
            
    # Deterministic fallback scout memo if Gemini client is offline or key missing
    arbitrage_text = f"an undervalued gem with €{abs(residual):,} surplus" if residual > 0 else f"commanding an elite star premium of €{abs(residual):,}"
    top_twin = neighbors[0].get('name', 'league peers') if (neighbors and isinstance(neighbors[0], dict)) else "league peers"
    best_dim = max(radar, key=radar.get) if radar else "performance"
    best_dim_val = radar.get(best_dim, 50) if radar else 50
    fallback_memo = (
        f"**Tactical Archetype:** {name} operates as a quintessential '{cluster}' for {team}. "
        f"His highest-rated dimension is {best_dim.title()} ({best_dim_val}th percentile).\n\n"
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
