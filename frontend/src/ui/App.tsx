import React, { useEffect, useMemo, useState } from "react";
import ChaosExplorer from "../modules/ChaosExplorer";
import WeirdShapes from "../modules/WeirdShapes";

type FreezeAll = { datasets: { dataset: string; data_csv_bytes?: number }[]; claims_path: string; };
type Claim = { dataset: string; claim: string; pass: boolean };

async function fetchJSON<T>(path: string): Promise<T | null> {
  try { const r = await fetch(path, { cache: "no-cache" }); if (!r.ok) return null; return (await r.json()) as T; }
  catch { return null; }
}
async function fetchNDJSON(path: string): Promise<Claim[]> {
  try { const r = await fetch(path, { cache: "no-cache" }); if (!r.ok) return []; const text = await r.text();
        return text.split(/\r?\n/).filter(Boolean).map(l => JSON.parse(l)); }
  catch { return []; }
}

export default function App() {
  const [freeze, setFreeze] = useState<FreezeAll | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [moduleKey, setModuleKey] = useState<"shapes"|"chaos">("chaos");

  useEffect(() => {
    fetchJSON<FreezeAll>("/discover/out/freeze_all.json").then(setFreeze);
    fetchNDJSON("/claims_all.ndjson").then(setClaims);
  }, []);

  const rollup = useMemo(() => {
    const by = new Map<string, { pass: number; total: number }>();
    for (const c of claims) {
      const s = by.get(c.dataset) ?? { pass: 0, total: 0 };
      s.total++; if (c.pass) s.pass++; by.set(c.dataset, s);
    }
    return by;
  }, [claims]);

  return (
    <div style={{padding:16, fontFamily:"system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial"}}>
      <h2 style={{marginTop:0}}>Interactive Mathematical Lab</h2>

      <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:16}}>
        <div style={{border:"1px solid #eee", borderRadius:12, padding:12}}>
          <h3>Frozen Datasets</h3>
          {!freeze && <div>Loading…</div>}
          {freeze && (
            <ul style={{listStyle:"none", padding:0, margin:0}}>
              {freeze.datasets.map(d => {
                const s = rollup.get(d.dataset) ?? { pass: 0, total: 0 };
                const ok = s.total>0 && s.pass===s.total;
                return (
                  <li key={d.dataset} style={{display:"flex", justifyContent:"space-between", alignItems:"center", padding:"6px 0"}}>
                    <button onClick={() => setSelectedDataset(d.dataset)} style={{padding:"6px 10px"}}>{d.dataset}</button>
                    <span style={{color: ok ? "#065f46" : "#991b1b"}}>{s.pass}/{s.total} checks</span>
                  </li>
                );
              })}
            </ul>
          )}
          <div style={{color:"#6b7280", fontSize:12, marginTop:8}}>
            Claims source: <code>{freeze?.claims_path ?? "claims_all.ndjson"}</code>
          </div>
        </div>

        <div style={{border:"1px solid #eee", borderRadius:12, padding:12}}>
          <h3>Modules</h3>
          <div style={{display:"flex", gap:8, flexWrap:"wrap"}}>
            <button onClick={()=>setModuleKey("chaos")} disabled={moduleKey==="chaos"}>Module 5: Chaos Explorer</button>
            <button onClick={()=>setModuleKey("shapes")} disabled={moduleKey==="shapes"}>Module 1: Weird Shapes</button>
          </div>
          <div style={{marginTop:8, color:"#6b7280", fontSize:12}}>
            Selected dataset: {selectedDataset ?? "—"}
          </div>
        </div>
      </div>

      <div style={{marginTop:16, border:"1px solid #eee", borderRadius:12, padding:12}}>
        {moduleKey==="chaos" && (<><h3 style={{marginTop:0}}>Module 5: Chaos Explorer</h3><ChaosExplorer/></>)}
        {moduleKey==="shapes" && (<><h3 style={{marginTop:0}}>Module 1: Weird Shapes</h3><WeirdShapes/></>)}
      </div>
    </div>
  );
}