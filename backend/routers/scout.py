import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.config import OPENROUTER_API_KEY
from backend.db import get_db_connection

router = APIRouter(prefix="/api/scout", tags=["scout"])

class ScoutAnalyzeRequest(BaseModel):
    player_id: str

class ScoutQueryRequest(BaseModel):
    query: str
    target_player_id: Optional[str] = None

def call_openrouter(prompt: str) -> str | None:
    # ponytail: only Minimax M3 free via OpenRouter — no Gemini/deterministic fallback per user request
    if not OPENROUTER_API_KEY:
        return None
    try:
        import httpx
        # minimax m3 free is currently free on OpenRouter; try :free suffix first
        for model in ["minimax/minimax-m3:free", "minimax/minimax-m3", "minimax/minimax-m2.1:free", "minimax/minimax-m2.1"]:
            try:
                r = httpx.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://matchlens.local", "X-Title": "Style Galaxy"},
                    json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 420, "temperature": 0.7},
                    timeout=12,
                )
                if r.status_code == 200:
                    j = r.json()
                    txt = j["choices"][0]["message"]["content"]
                    if txt:
                        return txt
                else:
                    print(f"[scout] OpenRouter {model} {r.status_code}: {r.text[:500]}")
            except Exception as e:
                print(f"[scout] OpenRouter {model} failed: {e}")
                continue
    except Exception as e:
        print(f"[scout] OpenRouter call failed: {e}")
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
    # ponytail: only Minimax M3 free — no fallback per user request; 503 if OpenRouter blocked
    or_txt = call_openrouter(prompt)
    if or_txt:
        return {"memo": or_txt, "player_name": name}
    raise HTTPException(status_code=503, detail="Minimax M3 via OpenRouter unavailable — check OPENROUTER_API_KEY and enable Minimax provider at https://openrouter.ai/settings/privacy (set to All). Free model tried: minimax/minimax-m3:free")

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
    
    prompt = f"""
A user asks: "{req.query}"
Based on our Premier League Moneyball database, here are the top undervalued arbitrage opportunities:
{json.dumps(candidates)}

Provide a sharp, 3-bullet executive scout response recommending the best targets and explaining the geometric/financial reasoning.
"""
    or_txt = call_openrouter(prompt)
    if or_txt:
        return {"response": or_txt, "recommended_players": candidates}
    raise HTTPException(status_code=503, detail="Minimax M3 via OpenRouter unavailable — enable Minimax provider at https://openrouter.ai/settings/privacy. Tried minimax/minimax-m3:free")
