import React, { useMemo, useState, useEffect } from "react";
import Plotly from "plotly.js-dist-min";

function usePlot(id: string, spec: any) {
  useEffect(() => { Plotly.react(id, spec.data, spec.layout, {displayModeBar:false}); }, [id, spec]);
}

function logisticSeries(r: number, x0: number, n: number, burn: number) {
  const xs: number[] = []; let x = x0;
  for (let i=0;i<burn+n;i++) { x = r*x*(1-x); if (i>=burn) xs.push(x); }
  return xs;
}
function lyapunov(r: number, xs: number[]) {
  const s = xs.reduce((acc,x)=> acc + Math.log(Math.abs(r*(1-2*x))+1e-12), 0);
  return s / xs.length;
}
function shannonEntropy(xs: number[], bins=100) {
  const hist = new Array(bins).fill(0);
  xs.forEach(x => { let b = Math.min(bins-1, Math.max(0, Math.floor(x*bins))); hist[b]++; });
  const n = xs.length;
  const p = hist.map(h => h/n).filter(v => v>0);
  return -p.reduce((a,v)=> a + v*Math.log2(v), 0);
}

export default function ChaosExplorer() {
  const [r, setR] = useState(3.8);
  const [x0, setX0] = useState(0.123456);
  const [n, setN] = useState(2000);
  const [burn, setBurn] = useState(200);

  const xs = useMemo(() => logisticSeries(r,x0,n,burn), [r,x0,n,burn]);
  const lam = useMemo(() => lyapunov(r, xs), [r, xs]);
  const H = useMemo(() => shannonEntropy(xs, 128), [xs]);

  usePlot("orbit", { data: [{y: xs.slice(0,400), type:"scatter", mode:"lines"}],
                     layout: {height: 220, margin:{l:30,r:10,t:10,b:30}, yaxis:{range:[0,1]}}});
  usePlot("hist",  { data: [{x: xs, type:"histogram", nbinsx: 64}],
                     layout: {height: 220, margin:{l:30,r:10,t:10,b:30}, xaxis:{range:[0,1]}}});

  return (
    <div>
      <div style={{display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:8}}>
        <label>r<br/><input type="range" min="2.5" max="4.0" step="0.0005" value={r} onChange={e=>setR(parseFloat(e.target.value))}/><div>{r.toFixed(4)}</div></label>
        <label>x₀<br/><input type="range" min="0.001" max="0.999" step="0.001" value={x0} onChange={e=>setX0(parseFloat(e.target.value))}/><div>{x0.toFixed(3)}</div></label>
        <label>burn-in<br/><input type="range" min="0" max="2000" step="10" value={burn} onChange={e=>setBurn(parseInt(e.target.value))}/><div>{burn}</div></label>
        <label>N<br/><input type="range" min="500" max="10000" step="100" value={n} onChange={e=>setN(parseInt(e.target.value))}/><div>{n}</div></label>
      </div>
      <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginTop:12}}>
        <div id="orbit"></div>
        <div id="hist"></div>
      </div>
      <div style={{marginTop:8, display:"flex", gap:16}}>
        <div><strong>Lyapunov λ:</strong> {lam.toFixed(4)} <span style={{color:"#6b7280"}}>(λ&gt;0 ⇒ chaos)</span></div>
        <div><strong>Shannon H:</strong> {H.toFixed(3)} bits</div>
      </div>
    </div>
  );
}