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
