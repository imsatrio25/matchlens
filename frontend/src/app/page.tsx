'use client';
import { useEffect, useState, useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Line } from '@react-three/drei';
import * as THREE from 'three';
import { GalaxyData, GalaxyNode } from '../types/galaxy';
import { fetchGalaxyData, fetchPlayerDossier, fetchScoutAnalysis, queryScout } from '../services/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5181/api';
const NGROK_HDR = { 'ngrok-skip-browser-warning': 'true' } as const;

const CLUSTER_COLOR: Record<number, string> = {
  0: '#ef4444', // Isolated Box Finishers - red
  1: '#f97316', // Inverted Creators - orange
  2: '#a78bfa', // Deep-Lying Playmakers - violet
  3: '#22c55e', // Box-to-Box - emerald
  4: '#ec4899', // Ball-Carrying AM - pink
  5: '#3b82f6', // Ball-Playing CB - blue
  6: '#06b6d4', // Full-Backs - cyan
  7: '#eab308', // Sweeper-Keeper - gold
};

function colorForCluster(id: number, pos: string) {
  return CLUSTER_COLOR[id] ?? '#94a3b8';
}

// ponytail: single instanced mesh — centered + y-scaled + native UMAP 12/0.45 needs only 1.65x spread; size toggle + scrub morph
function GalaxyPoints({ nodes, selectedId, onSelect, searchHitId, recs, center, onHover, sizeBy, scrubSeason, trajMap }: { nodes: GalaxyNode[]; selectedId: string | null; onSelect: (id: string) => void; searchHitId: string | null; recs: string[]; center: [number, number, number]; onHover: (node: GalaxyNode | null, x: number, y: number) => void; sizeBy: 'mv'|'eff'; scrubSeason: number|null; trajMap: Record<string, {season_order:number, coords:[number,number,number]}[]> }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const glowRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const mvRange = useMemo(() => {
    if (!nodes.length) return [5e6, 110e6] as const;
    const vals = nodes.map(n => n.market_value_eur);
    return [Math.min(...vals), Math.max(...vals)] as const;
  }, [nodes]);

  useEffect(() => {
    if (!meshRef.current || !glowRef.current) return;
    const [minMV, maxMV] = mvRange;
    const logMin = Math.log10(minMV), logMax = Math.log10(maxMV);
    const SPREAD = 2.45; // ponytail: 2.45× + native 12/0.45 = full galaxy, each dot isolated (was 1.65, half-donut)
    nodes.forEach((n, i) => {
      let cx = n.coords[0], cy = n.coords[1], cz = n.coords[2];
      if (scrubSeason !== null && trajMap[n.player_id]) {
        const hit = trajMap[n.player_id].find(t => t.season_order === scrubSeason);
        if (hit) { cx = hit.coords[0]; cy = hit.coords[1]; cz = hit.coords[2]; }
      }
      const x = (cx - center[0]) * SPREAD;
      const y = (cy - center[1]) * 1.9 * SPREAD;
      const z = (cz - center[2]) * SPREAD;
      dummy.position.set(x, y, z);
      const normMV = (Math.log10(Math.max(n.market_value_eur, minMV)) - logMin) / Math.max(0.01, logMax - logMin);
      const base = sizeBy === 'eff'
        ? 0.13 + (n.value_efficiency_score/100)*0.38 + (n.is_undervalued_gem ? 0.05 : 0)
        : 0.14 + normMV * 0.22 + (n.is_undervalued_gem ? 0.13 : 0);
      const s = searchHitId === n.player_id ? base * 2.1 : selectedId === n.player_id ? base * 1.65 : base;
      dummy.scale.setScalar(s);
      dummy.updateMatrix();
      meshRef.current!.setMatrixAt(i, dummy.matrix);
      // color by cluster (8-way) for visible diversity, not just 4 positions
      const c = new THREE.Color(recs.includes(n.player_id) ? '#facc15' : searchHitId === n.player_id ? '#fff' : selectedId === n.player_id ? '#ffffff' : colorForCluster(n.cluster_id, n.position));
      if (n.is_undervalued_gem && !recs.includes(n.player_id) && searchHitId !== n.player_id) {
        // stronger emerald halo hint in dot itself
        c.lerp(new THREE.Color('#10b981'), 0.18);
      }
      meshRef.current!.setColorAt(i, c);
      // glow for gems
      dummy.scale.setScalar(n.is_undervalued_gem ? s * 1.55 : 0);
      dummy.updateMatrix();
      glowRef.current!.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
    glowRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) meshRef.current.instanceColor.needsUpdate = true;
  }, [nodes, selectedId, searchHitId, recs, dummy, center, mvRange, sizeBy, scrubSeason, trajMap]);

  const handleClick = (e: any) => {
    e.stopPropagation();
    const idx = e.instanceId;
    if (idx != null && nodes[idx]) onSelect(nodes[idx].player_id);
  };
  const handlePointerMove = (e: any) => {
    const idx = e.instanceId;
    if (idx != null && nodes[idx]) onHover(nodes[idx], e.clientX, e.clientY);
  };
  const handlePointerOut = () => onHover(null, 0, 0);

  return (
    <>
      <instancedMesh ref={glowRef} args={[undefined, undefined, nodes.length]} frustumCulled={false}>
        <sphereGeometry args={[1, 8, 8]} />
        <meshBasicMaterial transparent opacity={0.14} color="#10b981" depthWrite={false} />
      </instancedMesh>
      <instancedMesh ref={meshRef} args={[undefined, undefined, nodes.length]} onClick={handleClick} onPointerMove={handlePointerMove} onPointerOut={handlePointerOut} frustumCulled={false}>
        <sphereGeometry args={[1, 10, 10]} />
        <meshStandardMaterial roughness={0.35} metalness={0.05} />
      </instancedMesh>
    </>
  );
}

function Trajectory({ points, center }: { points: [number, number, number][]; center: [number, number, number] }) {
  if (points.length < 2) return null;
  const SPREAD = 2.45;
  const centered = points.map(p => [(p[0] - center[0]) * SPREAD, (p[1] - center[1]) * 1.9 * SPREAD, (p[2] - center[2]) * SPREAD] as [number, number, number]);
  return <Line points={centered} color="#38bdf8" lineWidth={2} dashed={false} transparent opacity={0.85} />;
}

// ponytail: WASD spaceship — one useFrame, no lib, just translates camera+target along view vectors
function SpaceshipWASD({ enabled, controlsRef }: { enabled: boolean; controlsRef: React.RefObject<any> }) {
  const { camera } = useThree();
  const keys = useRef<Record<string, boolean>>({});
  useEffect(() => {
    if (!enabled) return;
    const down = (e: KeyboardEvent) => { keys.current[e.key.toLowerCase()] = true; };
    const up = (e: KeyboardEvent) => { keys.current[e.key.toLowerCase()] = false; };
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    return () => { window.removeEventListener('keydown', down); window.removeEventListener('keyup', up); };
  }, [enabled]);
  useFrame((_, dt) => {
    if (!enabled || !controlsRef.current) return;
    const speed = 18 * dt * (keys.current['shift'] ? 2.2 : 1);
    const forward = new THREE.Vector3(); camera.getWorldDirection(forward);
    const right = new THREE.Vector3().crossVectors(forward, camera.up).normalize();
    const up = new THREE.Vector3().copy(camera.up).normalize();
    let moved = false;
    const delta = new THREE.Vector3();
    if (keys.current['w']) { delta.addScaledVector(forward, speed); moved = true; }
    if (keys.current['s']) { delta.addScaledVector(forward, -speed); moved = true; }
    if (keys.current['a']) { delta.addScaledVector(right, -speed); moved = true; }
    if (keys.current['d']) { delta.addScaledVector(right, speed); moved = true; }
    if (keys.current['q']) { delta.addScaledVector(up, -speed); moved = true; }
    if (keys.current['e']) { delta.addScaledVector(up, speed); moved = true; }
    if (moved) {
      camera.position.add(delta);
      controlsRef.current.target.add(delta);
      controlsRef.current.update();
    }
  });
  return null;
}

export default function StyleGalaxyPage() {
  const [data, setData] = useState<GalaxyData | null>(null);
  const [selected, setSelected] = useState<GalaxyNode | null>(null);
  const [memo, setMemo] = useState<string>('');
  const [memoLoading, setMemoLoading] = useState(false);
  const [q, setQ] = useState('');
  const [posFilter, setPosFilter] = useState('ALL');
  const [undervalued, setUndervalued] = useState(false);
  const [hitId, setHitId] = useState<string | null>(null);
  const [recs, setRecs] = useState<any[]>([]);
  const [showTraj, setShowTraj] = useState(true);
  const [err, setErr] = useState('');
  const [hover, setHover] = useState<{ node: GalaxyNode | null; x: number; y: number }>({ node: null, x: 0, y: 0 });
  const [showInfo, setShowInfo] = useState(false);
  const [sizeBy, setSizeBy] = useState<'mv'|'eff'>('mv');
  const [scrubSeason, setScrubSeason] = useState<number|null>(null);
  const [trajMap, setTrajMap] = useState<Record<string, {season_order:number, coords:[number,number,number], xg_per_90:number, season:string}[]>>({});
  const [wasd, setWasd] = useState(true);
  const controlsRef = useRef<any>(null);

  useEffect(() => {
    fetchGalaxyData().then(setData).catch((e) => setErr(e.message));
  }, []);
  useEffect(() => {
    fetch(`${API_BASE}/trajectories`, { headers: NGROK_HDR }).then(r=>r.json()).then(setTrajMap).catch(()=>{});
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.nodes.filter(n => {
      if (posFilter !== 'ALL' && !n.position.toLowerCase().includes(posFilter.toLowerCase())) return false;
      if (undervalued && !n.is_undervalued_gem) return false;
      return true;
    });
  }, [data, posFilter, undervalued]);

  const center = useMemo(() => {
    if (!data?.nodes.length) return [0, 0, 0] as [number, number, number];
    const xs = data.nodes.map(n => n.coords[0]), ys = data.nodes.map(n => n.coords[1]), zs = data.nodes.map(n => n.coords[2]);
    return [xs.reduce((a,b)=>a+b,0)/xs.length, ys.reduce((a,b)=>a+b,0)/ys.length, zs.reduce((a,b)=>a+b,0)/zs.length] as [number, number, number];
  }, [data]);

  const recIds = useMemo(() => recs.map((r: any) => r.player_id), [recs]);

  async function selectPlayer(id: string) {
    setMemo(''); setMemoLoading(true);
    try {
      const dossier: any = await fetchPlayerDossier(id);
      setSelected(dossier);
      if (controlsRef.current && dossier.coords) {
        const SPREAD = 2.45;
        const tx = (dossier.coords[0] - center[0]) * SPREAD;
        const ty = (dossier.coords[1] - center[1]) * 1.9 * SPREAD;
        const tz = (dossier.coords[2] - center[2]) * SPREAD;
        controlsRef.current.target.lerp(new THREE.Vector3(tx, ty, tz), 0.6);
        controlsRef.current.update();
      }
      const res = await fetchScoutAnalysis(id);
      setMemo(res.memo);
    } catch (e: any) { setMemo('Scout offline — showing geometry only. ' + e.message); }
    setMemoLoading(false);
  }

  async function doSearch(e?: any) {
    if (e) e.preventDefault();
    if (!q.trim()) return;
    // cheap alternative path -> use LLM scout query
    if (q.toLowerCase().includes('cheap') || q.toLowerCase().includes('alternative') || q.toLowerCase().includes('replace')) {
      try {
        const r = await queryScout(q);
        setRecs(r.recommended_players || []);
        if (r.recommended_players?.[0]) {
          setHitId(r.recommended_players[0].player_id);
          setSelected(null);
          setMemo(r.response);
        }
      } catch {}
      return;
    }
    // normal name/team search
    try {
      const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(q)}&position=${posFilter}${undervalued ? '&undervalued_only=true' : ''}`, { headers: NGROK_HDR });
      const arr = await res.json();
      if (arr[0]) {
        setHitId(arr[0].player_id);
        setRecs([]);
        if (controlsRef.current) {
          const SPREAD = 2.45;
          controlsRef.current.target.set((arr[0].coords[0] - center[0]) * SPREAD, (arr[0].coords[1] - center[1]) * 1.9 * SPREAD, (arr[0].coords[2] - center[2]) * SPREAD);
          controlsRef.current.update();
        }
      }
    } catch {}
  }

  const hitNode = data?.nodes.find(n => n.player_id === hitId) || null;

  return (
    <div className="w-screen h-screen bg-[#030712] text-slate-100 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-[56px] flex items-center gap-3 px-4 border-b border-white/10 shrink-0 bg-black/30 backdrop-blur">
        <div className="font-black tracking-tight text-lg">◆ Style Galaxy</div>
        <div className="text-xs text-white/50 hidden sm:block">UMAP style space — dots close = play alike</div>
        <button onClick={() => setShowInfo(v=>!v)} className="hidden sm:inline-flex items-center gap-1 bg-white/10 hover:bg-white/15 border border-white/15 rounded-full px-2.5 py-1 text-xs">ⓘ why here?</button>
        <form onSubmit={doSearch} className="ml-auto flex gap-2 items-center flex-1 max-w-[560px] justify-end">
          <input value={q} onChange={e => setQ(e.target.value)} placeholder='Try "Bukayo Saka" or "cheap alternative to Saka"' className="w-full max-w-[380px] bg-white/10 border border-white/15 rounded-full px-4 py-1.5 text-sm outline-none focus:border-white/30 placeholder:text-white/40" />
          <button type="submit" className="bg-white text-black rounded-full px-4 py-1.5 text-sm font-semibold hover:bg-slate-100">Fly</button>
        </form>
        <select value={posFilter} onChange={e => setPosFilter(e.target.value)} className="bg-white/10 border border-white/15 rounded-full px-3 py-1.5 text-xs">
          <option value="ALL">All</option><option value="Forward">FW</option><option value="Midfielder">MF</option><option value="Defender">DF</option><option value="Goalkeeper">GK</option>
        </select>
        <label className="flex items-center gap-1.5 text-xs cursor-pointer"><input type="checkbox" checked={undervalued} onChange={e => setUndervalued(e.target.checked)} /> gems</label>
        <label className="flex items-center gap-1.5 text-xs cursor-pointer"><input type="checkbox" checked={showTraj} onChange={e => setShowTraj(e.target.checked)} /> traj</label>
        <button onClick={()=> setSizeBy(sizeBy==='mv'?'eff':'mv')} className="bg-white/10 hover:bg-white/15 border border-white/15 rounded-full px-2.5 py-1 text-xs" title="Toggle dot sizing">{sizeBy==='mv'?'Size: MV':'Size: Efficiency'}</button>
        <label className="flex items-center gap-1.5 text-xs cursor-pointer"><input type="checkbox" checked={wasd} onChange={e=> setWasd(e.target.checked)} /> WASD</label>
      </div>

      {/* scrubber — ponytail: one range input morphs whole galaxy by season_order + auto-play */}
      <div className="h-[36px] flex items-center gap-2 px-4 border-b border-white/10 bg-black/20 shrink-0 text-xs">
        <span className="text-white/60">Season scrub</span>
        <input type="range" min={0} max={7} step={1} value={scrubSeason ?? 7} onChange={e=> setScrubSeason(parseInt(e.target.value))} className="flex-1 accent-cyan-400" />
        <span className="bg-white/10 rounded-full px-2 py-1 text-[11px]">{scrubSeason===null ? 'career' : ['2018-19','2019-20','2020-21','2021-22','2022-23','2023-24','2024-25','2025-26'][scrubSeason] ?? scrubSeason}</span>
        <button onClick={()=> setScrubSeason(s=> s===null?0:null)} className="bg-white/10 hover:bg-white/15 border border-white/10 rounded-full px-2.5 py-1">{scrubSeason===null ? '▶ morph' : '✕ career'}</button>
        <button onClick={()=> { let i=0; const id=setInterval(()=>{ setScrubSeason(i%8); i++; if(i>16) clearInterval(id); },650); }} className="bg-white text-black rounded-full px-2.5 py-1 font-semibold">play</button>
        <span className="text-white/40 hidden sm:inline">xG arc + dot drift per season</span>
      </div>
      <div className="flex flex-1 min-h-0">
        {/* Canvas */}
        <div className="flex-1 relative">
          {!data ? <div className="absolute inset-0 grid place-items-center text-white/60 text-sm">{err ? `API offline: ${err} — run python -m backend.pipeline.seed_db + uvicorn backend.main:app` : 'Loading galaxy…'}</div> : (
            <Canvas camera={{ position: [0, 18, 48], fov: 52 }} dpr={[1, 1.6]} onPointerMissed={() => { setHitId(null); }}>
              <color attach="background" args={['#030712']} />
              <ambientLight intensity={1.25} />
              <pointLight position={[16, 20, 16]} intensity={1.35} />
              <pointLight position={[-14, -12, -14]} intensity={0.55} color="#38bdf8" />
              <fog attach="fog" args={['#030712', 32, 86]} />
              <GalaxyPoints nodes={filtered} selectedId={selected?.player_id || null} onSelect={selectPlayer} searchHitId={hitId} recs={recIds} center={center} onHover={(n,x,y)=> setHover({node:n,x,y})} sizeBy={sizeBy} scrubSeason={scrubSeason} trajMap={trajMap} />
              <SpaceshipWASD enabled={wasd} controlsRef={controlsRef} />
              {showTraj && selected?.trajectories && selected.trajectories.length > 1 && (
                <Trajectory points={selected.trajectories.map(t => t.coords as [number, number, number])} center={center} />
              )}
              {hitNode && <Trajectory points={[]} center={center} />}
              {/* plane back — now labeled axes, not confusing grid */}
              <gridHelper args={[96, 24, '#1e3347', '#0f1e2e']} position={[0, -9.5, 0]} />
              <group position={[0, -9.4, 0]}>
                <Line points={[[-42,0,0],[42,0,0]]} color="#38bdf8" lineWidth={1} transparent opacity={0.7} />
                <Line points={[[0,0,-42],[0,0,42]]} color="#a78bfa" lineWidth={1} transparent opacity={0.7} />
              </group>
              <OrbitControls ref={controlsRef} enableDamping dampingFactor={0.08} minDistance={5} maxDistance={78} target={[0,0,0]} />
            </Canvas>
          )}
          {/* axis labels — plane is style space, not pitch */}
          <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-black/60 border border-white/15 rounded-full px-3 py-1.5 text-[11px] text-white/75 pointer-events-none flex gap-3">
            <span><span className="text-sky-400">— UMAP-1</span> Attack←→Defense</span><span className="text-white/20">·</span><span><span className="text-violet-400">— UMAP-2</span> Progression←→Retention</span><span className="text-white/20">·</span><span>Plane = style similarity (cosine)</span><span className="text-white/20">·</span><span className={wasd ? 'text-emerald-400':'text-white/40'}>WASD{wasd?' ON':''} + Q/E up/down + Shift boost + mouse orbit</span>
          </div>
          <div className="absolute bottom-3 right-3 bg-black/55 border border-white/10 rounded-full px-2.5 py-1 text-[10px] text-white/50">grid = UMAP space · X:U1 Y:U2 · dots above plane</div>
          {showInfo && (
            <div className="absolute top-14 left-1/2 -translate-x-1/2 bg-[#0b1220] border border-white/15 rounded-2xl px-5 py-4 text-xs leading-relaxed max-w-[560px] shadow-2xl z-10">
              <div className="font-bold text-white mb-1">Why dots land where they do</div>
              <p className="text-white/70">Each player = 17-dim per-90 vector → <code className="bg-white/10 px-1 rounded">StandardScaler</code> → UMAP <code className="bg-white/10 px-1 rounded">cosine n=12 min_dist 0.45</code> → 3D. <b className="text-white">Distance = style similarity</b>. Plane axes: <span className="text-sky-400">U1</span>=attack/defense, <span className="text-violet-400">U2</span>=progression/retention, height=U3. Dots float above plane; grid is only style-space reference. Cosine picks twins; HGB log1p predicts value; top15% residual=halo.</p>
              <div className="mt-2 flex gap-2 text-[11px]"><span className="bg-white/10 rounded-full px-2 py-1">Color = 8 heuristic clusters (e.g. Inverted Creators, Ball-Playing CBs)</span><span className="bg-white/10 rounded-full px-2 py-1">Size = market value + gem bonus</span></div>
              <button onClick={() => setShowInfo(false)} className="mt-3 text-xs underline text-white/60">close</button>
            </div>
          )}
          {/* hover tooltip — ponytail: one absolute div, no portal/lib */}
          {hover.node && (
            <div className="absolute pointer-events-none bg-black/85 border border-white/15 rounded-lg px-2.5 py-1.5 text-xs leading-tight shadow-xl" style={{ left: hover.x + 14, top: hover.y + 14, maxWidth: 220 }}>
              <div className="font-bold text-white">{hover.node.name} <span className="font-normal text-white/60">· {hover.node.team}</span></div>
              <div className="text-white/70 text-[11px]">{hover.node.position} · {hover.node.cluster_label} · €{(hover.node.market_value_eur/1e6).toFixed(1)}m {hover.node.is_undervalued_gem && <span className="text-emerald-400">◆ gem +€{(hover.node.value_residual_eur/1e6).toFixed(1)}m</span>}</div>
            </div>
          )}
          {/* legend — 8 cluster colors, removed plane */}
          <div className="absolute bottom-3 left-3 bg-black/70 border border-white/10 rounded-xl px-3 py-2.5 text-[11px] leading-3 space-y-1.5 max-w-[380px]">
            <div className="font-semibold text-white/90">Legend — color = tactical cluster · size = market value</div>
            <div className="flex gap-1.5 flex-wrap">{[
              ['#ef4444','Finishers'],['#f97316','Wingers'],['#a78bfa','Deep Play'],['#22c55e','Box2Box'],['#ec4899','Carrying AM'],['#3b82f6','CBs'],['#06b6d4','FBs'],['#eab308','GK']
            ].map(([c,l])=> <span key={l} className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full" style={{background:c}} /> {l}</span>)}</div>
            <div className="text-white/50">Big halo = undervalued gem (top 15% residual). Same-color big halo next to small solid = arbitrage. Yellow = Minimax pick.</div>
            <div className="text-white/40">{data ? `${filtered.length} dots${undervalued ? ' (gems only)' : ''} · ${data.clusters.length} clusters · 2.45× (native 12/0.45) · ${sizeBy==='mv'?'MV':'Eff'} · plane U1/U2` : ''}</div>
          </div>
          {recs.length > 0 && (
            <div className="absolute top-3 left-3 bg-amber-400 text-black rounded-xl px-3 py-2 text-xs max-w-[360px]">Scout picks: {recs.map((r: any) => `${r.name} (€${(r.market_value_eur/1e6).toFixed(1)}m)`).join(' · ')} <button onClick={() => setRecs([])} className="ml-2 underline">clear</button></div>
          )}
        </div>

        {/* Drawer */}
        <div className="w-[380px] shrink-0 border-l border-white/10 bg-[#0b1220] overflow-auto hidden lg:block">
          {!selected ? (
            <div className="p-6 text-sm text-white/60 space-y-3">
              <div className="text-white font-bold text-base">Welcome, Director.</div>
              <p>Every dot is a Premier League player. Dots close together play alike — UMAP on ~17 per-90 stats. Big cheap dots next to small expensive ones are your arbitrage.</p>
              <p className="text-white/80 font-medium">How to use:</p>
              <ul className="list-disc ml-4 space-y-1"><li>Drag to orbit, scroll to zoom.</li><li>Click any dot for radar + scout memo (grounded in cosine twins + residual).</li><li>Search “Saka” to fly there; “cheap alternative to Saka” lets the LLM highlight the nearest cheaper twin.</li><li>Toggle <b>gems</b> to glow only undervalued players (residual &gt; €12m).</li></ul>
              {data && <div className="pt-3 grid grid-cols-1 gap-1">{data.clusters.map(c => <div key={c.cluster_id} className="flex justify-between bg-white/5 rounded-full px-3 py-1 text-xs"><span>{c.label}</span><span className="text-white/50">{c.count}</span></div>)}</div>}
            </div>
          ) : (
            <div className="p-5 space-y-4">
              <div>
                <div className="text-xl font-black leading-none">{selected.name} <span className="font-normal text-white/50 text-sm">· {selected.team}</span></div>
                <div className="text-xs text-white/60 mt-1">{selected.position} · {selected.cluster_label} · €{(selected.market_value_eur/1e6).toFixed(1)}m <span className={selected.value_residual_eur > 0 ? 'text-emerald-400' : 'text-red-400'}>({selected.value_residual_eur > 0 ? '+' : ''}€{(selected.value_residual_eur/1e6).toFixed(1)}m vs fair)</span> · score {selected.value_efficiency_score}</div>
                <div className="mt-2 flex gap-2">{selected.is_undervalued_gem && <span className="bg-emerald-500 text-black text-[11px] font-bold px-2 py-0.5 rounded-full">UNDERVALUED GEM</span>}<span className="bg-white/10 text-xs px-2 py-0.5 rounded-full">pred €{(selected.predicted_market_value_eur/1e6).toFixed(1)}m</span></div>
              </div>
              {/* radar */}
              <div className="grid grid-cols-5 gap-1 text-center">
                {Object.entries(selected.radar || {}).map(([k, v]) => (
                  <div key={k} className="bg-white/5 rounded-lg py-2"><div className="text-[10px] uppercase tracking-wide text-white/50">{k.slice(0,4)}</div><div className="font-bold text-sm">{v as number}</div><div className="h-1 bg-white/10 rounded mt-1 mx-2"><div className="h-1 bg-white rounded" style={{ width: `${v}%` }} /></div></div>
                ))}
              </div>
              {/* twins */}
              <div><div className="text-xs font-bold tracking-wide mb-1">CLOSEST STYLE TWINS (cosine)</div><div className="space-y-1">{(selected.nearest_neighbors || []).slice(0, 5).map((t: any) => (
                <button key={t.player_id} onClick={() => selectPlayer(t.player_id)} className="w-full flex justify-between items-center bg-white/5 hover:bg-white/10 rounded-full px-3 py-1.5 text-xs text-left"><span>{t.name} · {t.team} <span className="text-white/40"> {t.similarity_score}%</span></span><span className="text-white/60">€{(t.market_value_eur/1e6).toFixed(1)}m</span></button>
              ))}</div></div>
              {/* trajectory list */}
              {selected.trajectories && selected.trajectories.length > 1 && (
                <div className="text-xs"><div className="font-bold tracking-wide mb-1">CAREER TRAJECTORY (UMAP drift)</div><div className="flex gap-1 flex-wrap">{selected.trajectories.map(t => <span key={t.season} className="bg-white/5 rounded-full px-2 py-1">{t.season} · xG {t.xg_per_90.toFixed(2)}</span>)}</div></div>
              )}
              {/* memo */}
              <div className="bg-white/[0.06] border border-white/10 rounded-xl p-3 text-sm leading-relaxed whitespace-pre-wrap">{memoLoading ? 'Scout is writing…' : memo || 'Click a twin or search to compare.'}</div>
              <button onClick={() => setSelected(null)} className="text-xs text-white/50 underline">← back to galaxy</button>
            </div>
          )}
        </div>
      </div>
      {/* mobile drawer */}
      {selected && (
        <div className="lg:hidden border-t border-white/10 bg-[#0b1220] max-h-[42vh] overflow-auto p-4 text-sm">
          <div className="font-bold">{selected.name} · {selected.team} — {selected.cluster_label}</div>
          <div className="text-xs text-white/60">€{(selected.market_value_eur/1e6).toFixed(1)}m · {memoLoading ? 'writing…' : memo.slice(0, 260)}</div>
          <button onClick={() => setSelected(null)} className="text-xs underline mt-2">close</button>
        </div>
      )}
    </div>
  );
}
