import React, { useMemo, useState, useEffect } from "react";
import Plotly from "plotly.js-dist-min";

function safeFunc(src: string) {
  try { return new Function("x", `"use strict"; return (${src});`) as (x:number)=>number; }
  catch { return (_:number)=>NaN; }
}
function riemann(f:(x:number)=>number, a:number, b:number, n:number) {
  const dx = (b-a)/n; let left=0,right=0,trap=0;
  for (let i=0;i<n;i++){const xl=a+i*dx,xr=a+(i+1)*dx,fl=f(xl),fr=f(xr);
    left+=fl*dx; right+=fr*dx; trap+=0.5*(fl+fr)*dx;}
  return { left, right, trap, dx };
}
function sampleSeries(f:(x:number)=>number, a:number, b:number, pts:number) {
  const xs:number[]=[], ys:number[]=[];
  for (let i=0;i<=pts;i++){const x=a+(b-a)*i/pts; let y=f(x); if(!isFinite(y)||Math.abs(y)>1e6)y=NaN; xs.push(x); ys.push(y);}
  return { xs, ys };
}
export default function WeirdShapes() {
  const [src,setSrc]=useState("Math.sin(1/x)"); const [a,setA]=useState(0.001);
  const [b,setB]=useState(1.0); const [n,setN]=useState(200);
  const f = useMemo(()=>safeFunc(src),[src]);
  const {left,right,trap,dx}=useMemo(()=>riemann(f,a,b,Math.max(1,n)),[f,a,b,n]);
  const series=useMemo(()=>sampleSeries(f,a,b,800),[f,a,b]);
  useEffect(()=>{const rects=[] as any[]; for(let i=0;i<n;i++){const xl=a+i*dx,xr=a+(i+1)*dx,fl=f(xl);
      rects.push({xref:"x",yref:"y",type:"rect",x0:xl,x1:xr,y0:Math.min(0,fl),y1:Math.max(0,fl),line:{width:0},fillcolor:"rgba(31,119,180,0.10)"});}
    const data:any[]=[{x:series.xs,y:series.ys,mode:"lines",name:"f(x)"},
      {x:Array.from({length:n},(_,i)=>a+i*dx),y:Array.from({length:n},(_,i)=>f(a+i*dx)),mode:"markers",name:"left points",marker:{size:4}}];
    Plotly.react("ws-plot", data, {height:280,margin:{l:40,r:10,t:10,b:35},shapes:rects,xaxis:{range:[a,b]}},{displayModeBar:false});
  },[a,b,n,dx,f,series]);
  return (<div>
    <div style={{display:"grid",gridTemplateColumns:"2fr 1fr 1fr 1fr",gap:8}}>
      <label>f(x)<input value={src} onChange={e=>setSrc(e.target.value)} style={{width:"100%"}}/></label>
      <label>a<input type="number" step="0.0005" value={a} onChange={e=>setA(parseFloat(e.target.value)||0)} style={{width:"100%"}}/></label>
      <label>b<input type="number" step="0.0005" value={b} onChange={e=>setB(parseFloat(e.target.value)||0)} style={{width:"100%"}}/></label>
      <label>n<input type="range" min="10" max="4000" step="10" value={n} onChange={e=>setN(parseInt(e.target.value)||10)} /><div>{n}</div></label>
    </div>
    <div id="ws-plot" style={{marginTop:8}}></div>
    <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:8,marginTop:8}}>
      <div><strong>Left:</strong> {Number.isFinite(left)? left.toFixed(6):"NaN"}</div>
      <div><strong>Right:</strong> {Number.isFinite(right)? right.toFixed(6):"NaN"}</div>
      <div><strong>Trap:</strong> {Number.isFinite(trap)? trap.toFixed(6):"NaN"}</div>
    </div>
  </div>);
}