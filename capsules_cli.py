import argparse, csv, gzip, hashlib, json, math, os, random, sys, time
from collections import Counter, defaultdict
from typing import List, Dict, Tuple
import numpy as np

# Optional deps are only needed by certain subcommands
try:
    import pandas as pd
except Exception:
    pd = None
try:
    import networkx as nx
except Exception:
    nx = None

# ---------- utils ----------
def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

def sha256_path(p:str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""): h.update(chunk)
    return h.hexdigest()

def lz78_bits_per_symbol(seq, max_symbols=500_000):
    if len(seq) > max_symbols:
        seq = seq[:max_symbols]
    dict_ = {}
    next_code = 1
    i = 0
    bits = 0.0
    n = len(seq)
    while i < n:
        phrase = (seq[i],)
        j = i+1
        while j<=n and phrase in dict_:
            if j==n: break
            phrase = phrase + (seq[j],)
            j += 1
        if phrase in dict_:
            bits += math.log2(max(1, next_code))
            i = n
        else:
            bits += math.log2(max(1, next_code))
            dict_[phrase] = next_code
            next_code += 1
            i = j
    return bits / max(1,n)

# ---------- capsules ----------
def capsule_transition(args):
    if pd is None:
        raise RuntimeError("pandas/pyarrow required for 'transition' capsule")
    df = pd.read_parquet(args.input, columns=[args.origin, args.dest])
    pu = df[args.origin].astype("Int64").dropna().astype(int).to_numpy()
    do = df[args.dest].astype("Int64").dropna().astype(int).to_numpy()
    m = int(min(len(pu), len(do)))
    pu = pu[:m]; do = do[:m]

    C = Counter(zip(pu, do))
    rows = defaultdict(int)
    for (i,j), c in C.items(): rows[i] += c
    states = sorted(set(pu.tolist()) | set(do.tolist()))
    idx = {s:k for k,s in enumerate(states)}
    S = len(states)
    P = np.zeros((S,S), dtype=np.float64)
    for (i,j), c in C.items():
        P[idx[i], idx[j]] += c / rows[i]

    v = np.ones(S)/S
    for _ in range(200): v = v @ P
    pi = v / v.sum()

    def H_row(p):
        mask = p>0
        return float(-np.sum(p[mask]*np.log2(p[mask])))
    H_rate = float(sum(pi[i]*H_row(P[i]) for i in range(S)))

    lz_seq = do[::args.stride].tolist()
    lz_rate = lz78_bits_per_symbol(lz_seq, max_symbols=args.lz_cap)

    manifest = {
        "capsule_id": "transition_markov",
        "source": os.path.basename(args.input),
        "inputs": [{"path": args.input, "sha256": sha256_path(args.input)}],
        "parameters": {
            "origin_field": args.origin,
            "dest_field": args.dest,
            "order": 1,
            "stride": args.stride,
            "lz_cap": args.lz_cap
        },
        "random_state": {},
        "metrics": {
            "n_pairs": m,
            "n_states": S,
            "entropy_rate_bits_per_step": H_rate,
            "lz78_bits_per_symbol": lz_rate,
            "gap_bits_per_step": H_rate - lz_rate
        },
        "method": {
            "P": "empirical conditional D|P (counts normalized by origin)",
            "pi": "power iteration on P^T starting from uniform",
            "H_rate": "sum_i pi_i * H(P_i*) in base-2 bits",
            "lz78": f"subsample stride={args.stride}, cap={args.lz_cap}"
        },
        "created_at": now_iso()
    }
    with open(args.out, "w", encoding="utf-8") as f: json.dump(manifest, f, indent=2)
    print(f"[transition] pairs={m:,} states={S} H={H_rate:.4f} LZ={lz_rate:.4f}")

def capsule_interval_bmo(args):
    chrom = args.chrom
    win = args.win
    cov = defaultdict(int)
    with gzip.open(args.input, "rt", encoding="utf-8", errors="replace") as f:
        rdr = csv.reader(f, delimiter="\t")
        for row in rdr:
            if not row: continue
            # UCSC rmsk format by default: chrom at col 5 (0-based), start 6, end 7
            c = row[args.chrom_col]
            if c != chrom: continue
            start = int(row[args.start_col]); end = int(row[args.end_col])
            w0 = start // win; w1 = (end-1) // win
            for w in range(w0, w1+1):
                s = max(start, w*win); e = min(end, (w+1)*win)
                if e> s: cov[w] += (e - s)
    windows = sorted(cov.keys())
    dens = [cov[w]/win for w in windows]

    def bmo(vals, block):
        n=len(vals); best=0.0
        for i in range(0, n):
            j = min(n, i+block)
            if j<=i: continue
            Q = vals[i:j]
            mean = sum(Q)/len(Q)
            osc = sum(abs(x-mean) for x in Q)/len(Q)
            if osc>best: best=osc
        return best

    bmo16, bmo32, bmo64 = bmo(dens,16), bmo(dens,32), bmo(dens,64)
    bmo_star = max(bmo16, bmo32, bmo64)
    c1, c2 = 2.0, 0.5
    alpha_star = c2 / max(1e-12, bmo_star)
    ceiling = c1 * math.exp(-c2 / max(1e-12, bmo_star))

    manifest = {
        "capsule_id": "interval_bmo_chr",
        "source": os.path.basename(args.input),
        "inputs": [{"path": args.input, "sha256": sha256_path(args.input)}],
        "parameters": {
            "chrom": chrom,
            "window": win,
            "chrom_col": args.chrom_col,
            "start_col": args.start_col,
            "end_col": args.end_col
        },
        "random_state": {},
        "metrics": {
            "n_windows": len(windows),
            "bmo_16": bmo16,
            "bmo_32": bmo32,
            "bmo_64": bmo64,
            "bmo_star": bmo_star,
            "john_nirenberg": {
                "c1": c1, "c2": c2,
                "alpha_star": alpha_star,
                "ceiling_proxy": ceiling
            }
        },
        "method": {
            "coverage": "windowed bp/Win for intervals",
            "BMO": "max avg deviation over blocks {16,32,64}"
        },
        "created_at": now_iso()
    }
    with open(args.out, "w", encoding="utf-8") as f: json.dump(manifest, f, indent=2)
    print(f"[interval-bmo] {chrom} windows={len(windows)} BMO*={bmo_star:.6f}")

def capsule_graph(args):
    if nx is None:
        raise RuntimeError("networkx/numpy required for 'graph' capsule")
    edges = []
    with gzip.open(args.input, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line or line.startswith("#"): continue
            a,b = line.strip().split()
            edges.append((int(a), int(b)))
    Gd = nx.DiGraph(); Gd.add_edges_from(edges)
    H = nx.Graph(Gd) if not args.directed else Gd.to_undirected()
    n_all = H.number_of_nodes(); m_all = H.number_of_edges()
    nodes = list(H.nodes())
    sampled_nodes: List[int]
    if args.n_max and n_all > args.n_max:
        random.seed(args.seed)
        sampled_nodes = random.sample(nodes, args.n_max)
        H = H.subgraph(sampled_nodes).copy()
    else:
        sampled_nodes = nodes
    n = H.number_of_nodes(); m = H.number_of_edges()
    A = nx.to_numpy_array(H, dtype=float)
    evals = np.linalg.eigvalsh(A)
    diffs = []
    for k in range(1, args.k_max+1):
        trace_pow = float(np.trace(np.linalg.matrix_power(A, k)))
        spectral = float(np.sum(evals**k))
        diffs.append(abs(trace_pow - spectral))

    manifest = {
        "capsule_id": "graph_trace",
        "source": os.path.basename(args.input),
        "inputs": [{"path": args.input, "sha256": sha256_path(args.input)}],
        "parameters": {
            "directed": bool(args.directed),
            "n_max": args.n_max,
            "k_max": args.k_max,
            "seed": args.seed
        },
        "random_state": {"sampled_nodes": sampled_nodes},
        "metrics": {
            "n_nodes": n,
            "n_edges": m,
            "trace_vs_spectrum_max_abs_diff": max(diffs) if diffs else 0.0,
            "k_tested": list(range(1, args.k_max+1))
        },
        "method": {
            "A": "undirected adjacency of sampled induced subgraph",
            "test": "Tr(A^k) vs sum(lambda^k)"
        },
        "created_at": now_iso()
    }
    with open(args.out, "w", encoding="utf-8") as f: json.dump(manifest, f, indent=2)
    print(f"[graph] n={n} m={m} max|Δ|={max(diffs) if diffs else 0.0:.3e}")

# ---------- CLI ----------
def build_parser():
    p = argparse.ArgumentParser(prog="capsules_cli", description="Generalized capsules → JSON manifests")
    sp = p.add_subparsers(dest="cmd", required=True)

    t = sp.add_parser("transition", help="OD Markov + LZ78")
    t.add_argument("--input", required=True)
    t.add_argument("--origin", required=True)
    t.add_argument("--dest", required=True)
    t.add_argument("--stride", type=int, default=int(os.environ.get("HARSH_TAXI_STRIDE","5")))
    t.add_argument("--lz-cap", type=int, default=int(os.environ.get("HARSH_LZ_MAX","500000")))
    t.add_argument("--out", required=True)
    t.set_defaults(func=capsule_transition)

    b = sp.add_parser("interval-bmo", help="Interval coverage BMO* (e.g., RepeatMasker)")
    b.add_argument("--input", required=True)
    b.add_argument("--chrom", required=True)
    b.add_argument("--win", type=int, default=100_000)
    b.add_argument("--chrom-col", type=int, default=5)
    b.add_argument("--start-col", type=int, default=6)
    b.add_argument("--end-col", type=int, default=7)
    b.add_argument("--out", required=True)
    b.set_defaults(func=capsule_interval_bmo)

    g = sp.add_parser("graph", help="Graph trace vs eigen moments")
    g.add_argument("--input", required=True)
    g.add_argument("--directed", action="store_true")
    g.add_argument("--n-max", type=int, default=int(os.environ.get("HARSH_GRAPH_N","400")))
    g.add_argument("--k-max", type=int, default=int(os.environ.get("HARSH_GRAPH_KMAX","6")))
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("--out", required=True)
    g.set_defaults(func=capsule_graph)

    return p

def main():
    args = build_parser().parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
