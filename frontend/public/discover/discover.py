import argparse, json, pathlib, math, re
import numpy as np, pandas as pd

def is_num(s): return pd.api.types.is_numeric_dtype(s)
def maybe_dt(s):
    if pd.api.types.is_datetime64_any_dtype(s): return s
    try: return pd.to_datetime(s, errors="raise")
    except: return None

def find_date_col(df):
    for cand in ["date","datetime","timestamp","time","pickup_datetime","tpep_pickup_datetime","Date","DATE"]:
        if cand in df.columns:
            dt = maybe_dt(df[cand])
            if dt is not None: return cand, dt
    for c in df.columns:
        dt = maybe_dt(df[c])
        if dt is not None: return c, dt
    return None, None

def daily_signal(df, dt_name, dt_vals):
    g = df.copy()
    g["_dt"] = dt_vals
    g = g.dropna(subset=["_dt"])
    g["_d"] = g["_dt"].dt.floor("D")
    num_cols = [c for c in g.columns if is_num(g[c]) and c not in ("_dt","_d")]
    if num_cols:
        y = g.groupby("_d")[num_cols[0]].mean().sort_index()
        label = f"mean({num_cols[0]})"
    else:
        y = g.groupby("_d").size().astype(float).sort_index()
        label = "daily_count"
    return y, label

def acf(x, max_lag=60):
    x = np.asarray(x, dtype=float)
    x = x - np.nanmean(x)
    n = len(x)
    if n == 0: return np.array([])
    ac = np.array([np.correlate(x[:n-l], x[l:])[0] for l in range(max_lag+1)], dtype=float)
    return ac / ac[0] if ac[0] != 0 else ac

def slope_strength(y):
    t = np.arange(len(y))
    coef = np.polyfit(t, y, 1)
    yhat = coef[0]*t + coef[1]
    ss_res = float(np.sum((y - yhat)**2))
    ss_tot = float(np.sum((y - np.mean(y))**2))
    r2 = 1.0 - ss_res/ss_tot if ss_tot>0 else 0.0
    return coef[0], r2

def gini(arr):
    x = np.sort(np.asarray(arr, dtype=float))
    if len(x)==0 or x.sum()==0: return 0.0
    n = len(x)
    return (2*np.sum((np.arange(1,n+1))*x)/(n*np.sum(x)) - (n+1)/n)

def pick_latlon(df):
    lat=lon=None
    for c in df.columns:
        lc=c.lower()
        if lat is None and lc in ("lat","latitude","pickup_latitude","y"): lat=c
        if lon is None and lc in ("lon","lng","longitude","pickup_longitude","x"): lon=c
    return lat, lon

def spatial_cluster_index(df):
    latc, lonc = pick_latlon(df)
    if not latc or not lonc: return None
    lat = pd.to_numeric(df[latc], errors="coerce")
    lon = pd.to_numeric(df[lonc], errors="coerce")
    m = pd.DataFrame({"lat":lat,"lon":lon}).dropna()
    m = m[(m.lat.between(-90,90)) & (m.lon.between(-180,180))]
    if len(m) < 500: return None
    n = 100
    H, _, _ = np.histogram2d(m["lat"], m["lon"], bins=n)
    return float(gini(H.ravel()))

def top_entropies(df, max_cols=12):
    def entropy_series(s, max_bins=64):
        s = s.dropna()
        if s.empty: return None
        if is_num(s):
            q = np.asarray(s)
            try:
                iqr = np.subtract(*np.nanpercentile(q,[75,25]))
                h = 2*iqr*(len(q)**(-1/3)) if iqr>0 else 0
                bins = max(8, min(max_bins, int((q.max()-q.min())/h))) if h>0 else 20
            except: bins = 20
            bins = max(8, min(max_bins, bins))
            counts,_ = np.histogram(q, bins=bins)
        else:
            counts = s.astype("object").value_counts(dropna=True).values
        p = counts / (counts.sum() if counts.sum()>0 else 1)
        p = p[p>0]
        return float(-(p*np.log2(p)).sum())
    ents = {}
    for c in df.columns:
        try:
            e = entropy_series(df[c])
            if e is not None: ents[c] = round(e,4)
        except: pass
    return dict(sorted(ents.items(), key=lambda kv: kv[1], reverse=True)[:max_cols])

def join_weather(slug, y, date_index):
    base = pathlib.Path("datasets/out")
    if slug.startswith("chicago_crimes"):
        w_csv = base/"noaa_chicago_daily"/"data.csv"
    elif slug.startswith("tlc_yellow"):
        w_csv = base/"noaa_central_park_daily"/"data.csv"
    else:
        return None
    if not w_csv.exists(): return None
    w = pd.read_csv(w_csv, parse_dates=["date"]).set_index("date").sort_index()
    df = pd.DataFrame({"y": y.values}, index=date_index)
    cols = [c for c in ["tmax_c","tmin_c","prcp_mm"] if c in w.columns]
    j = df.join(w[cols], how="inner")
    if len(j)<10: return None
    corr = {k: float(np.corrcoef(j["y"], j[k])[0,1]) for k in cols}
    return {"weather_join_rows": int(len(j)), "pearson_r": corr}

def weekly_strength(y):
    ac = acf(y, max_lag=60)
    r7  = float(ac[7])  if len(ac)>7  else 0.0
    r14 = float(ac[14]) if len(ac)>14 else 0.0
    r30 = float(ac[30]) if len(ac)>30 else 0.0
    return {"acf_lag7": round(r7,3), "acf_lag14": round(r14,3), "acf_lag30": round(r30,3)}

def confidence(score, hi=0.6, mid=0.35):
    return "high" if score>=hi else ("medium" if score>=mid else "low")

def analyze_one(csv_path):
    slug = pathlib.Path(csv_path).parent.name
    df = pd.read_csv(csv_path, low_memory=False)
    claims = []

    dt_name, dt_vals = find_date_col(df)
    if dt_name:
        y, label = daily_signal(df, dt_name, dt_vals)
        if len(y)>=21:
            ac = weekly_strength(y.values)
            if ac["acf_lag7"]>=0.35:
                claims.append({
                    "slug": slug,
                    "type": "seasonality",
                    "statement": f"Weekly seasonality present in daily series ({label}).",
                    "evidence": ac,
                    "confidence": confidence(ac["acf_lag7"])
                })
            m = y.values.astype(float)
            b, r2 = slope_strength(m)
            if abs(b) > 0 and r2>=0.15:
                claims.append({
                    "slug": slug,
                    "type": "trend",
                    "statement": f"Monotone trend detected in daily series ({label}).",
                    "evidence": {"slope_per_day": float(b), "r2": round(r2,3)},
                    "confidence": confidence(r2, hi=0.5, mid=0.25)
                })
            wj = join_weather(slug, y, y.index)
            if wj and wj.get("pearson_r"):
                maxk = max(wj["pearson_r"], key=lambda k: abs(wj["pearson_r"][k]))
                r    = wj["pearson_r"][maxk]
                claims.append({
                    "slug": slug,
                    "type": "exogenous_driver",
                    "statement": f"Daily series correlates with weather ({maxk}: r={r:.2f}).",
                    "evidence": wj,
                    "confidence": confidence(abs(r), hi=0.55, mid=0.35)
                })

    sci = spatial_cluster_index(df)
    if sci is not None:
        claims.append({
            "slug": slug,
            "type": "spatial_clustering",
            "statement": "Locations are clustered (high grid inequality).",
            "evidence": {"gini_heatmap": round(sci,3)},
            "confidence": confidence(sci, hi=0.65, mid=0.45)
        })

    ents = top_entropies(df)
    if ents:
        high = [k for k,v in ents.items() if v>=4.0]
        if high:
            claims.append({
                "slug": slug,
                "type": "rich_attribute",
                "statement": f"High-information columns present: {', '.join(high[:6])}" + ("…" if len(high)>6 else ""),
                "evidence": {"entropies_bits": ents},
                "confidence": "medium"
            })

    return slug, claims

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_root", default="datasets/out")   # run-from-anywhere support
    ap.add_argument("--outdir",    default="discover/out")
    a = ap.parse_args()

    outdir = pathlib.Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in pathlib.Path(a.data_root).glob("*/data.csv"):
        slug, claims = analyze_one(str(p))
        if not claims: continue
        outp = outdir / f"claims_{slug}.json"
        outp.write_text(json.dumps(claims, indent=2), encoding="utf-8")
        rows.extend(claims)
        print(f"[discover] {slug}: {len(claims)} claims -> {outp}")

    md = ["# Discoveries\n"]
    for slug in sorted(set(c["slug"] for c in rows)):
        md.append(f"## {slug}")
        for c in [r for r in rows if r["slug"]==slug]:
            md.append(f"- **{c['type']}** ({c['confidence']}): {c['statement']}")
        md.append("")
    (outdir/"discoveries.md").write_text("\n".join(md), encoding="utf-8")
    print(f"[discover] rollup -> {(outdir/'discoveries.md')}")

if __name__ == "__main__":
    main()
