import { GalaxyData, GalaxyNode } from '../types/galaxy';

// ponytail: dynamic host so phone via Tailscale/LAN hits same backend without env rebuild
function getApiBase() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== 'undefined') {
    const h = window.location.hostname;
    if (h !== 'localhost' && h !== '127.0.0.1') return `http://${h}:5181/api`;
  }
  return 'http://localhost:5181/api';
}
const API_BASE = getApiBase();

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
