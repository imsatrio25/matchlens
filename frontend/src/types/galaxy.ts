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
