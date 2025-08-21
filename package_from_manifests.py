import argparse, hashlib, json, os, sys, time
from pathlib import Path
import zipfile

MANI_DIR = Path("manifests")

def hpath(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""): h.update(chunk)
    return h.hexdigest()

def claims_from_manifests(objs):
    claims = []; ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    for name, M in objs.items():
        cid = M.get("capsule_id") or M.get("capsule")
        if cid == "transition_markov" or cid == "taxi_markov":
            H = M["metrics"]["entropy_rate_bits_per_step"]
            LZ = M["metrics"]["lz78_bits_per_symbol"]
            gap = M["metrics"]["gap_bits_per_step"]
            src = M.get("source", name)
            claims.append({
                "capsule": "transition_markov",
                "timestamp": ts,
                "claim": f"OD entropy-rate on {src} is {H:.6f} bits/step; LZ78 proxy {LZ:.6f}; gap {gap:.6f} bits/step.",
                "falsification": "Rebuild P from D|P counts; recompute pi; re-evaluate H_rate and LZ78 on same policy.",
                "hash": hashlib.sha256(json.dumps(M, sort_keys=True).encode()).hexdigest()
            })
        if cid == "interval_bmo_chr" or cid == "rmsk_bmo_chr":
            bmo = M["metrics"]["bmo_star"]
            ceil = M["metrics"]["john_nirenberg"]["ceiling_proxy"]
            chrom = M["parameters"]["chrom"]
            win = M["parameters"]["window"]
            src = M.get("source", name)
            claims.append({
                "capsule": "interval_bmo_chr",
                "timestamp": ts,
                "claim": f"Interval coverage on {chrom} (win={win}) has BMO*={bmo:.6f}; John–Nirenberg ceiling proxy {ceil:.6e}.",
                "falsification": "Recompute windowed coverage; rescan blocks {16,32,64}; compare BMO* and ceiling proxy.",
                "hash": hashlib.sha256(json.dumps(M, sort_keys=True).encode()).hexdigest()
            })
        if cid == "graph_trace" or cid == "graph_trace":
            diff = M["metrics"]["trace_vs_spectrum_max_abs_diff"]
            src = M.get("source", name)
            n = M["metrics"]["n_nodes"]
            kmax = max(M["metrics"]["k_tested"])
            claims.append({
                "capsule": "graph_trace",
                "timestamp": ts,
                "claim": f"On {src}, max |Tr(A^k) - sum(lambda^k)| over k=1..{kmax} is {diff:.3e} on an induced subgraph of size {n}.",
                "falsification": "Rebuild undirected A on the same node sample; recompute both sides for k=1..K.",
                "hash": hashlib.sha256(json.dumps(M, sort_keys=True).encode()).hexdigest()
            })
    return {"claims": claims, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mani-dir", default="manifests")
    p.add_argument("--out-zip-name", default=None, help="Optional fixed name; otherwise freeze_<MONTH>_<hashprefix>.zip")
    args = p.parse_args()

    md = Path(args.mani_dir)
    if not md.exists():
        print("ERROR: manifests/ missing", file=sys.stderr); sys.exit(2)

    # Load manifests present
    want = ["taxi_markov.json","rmsk_chr1_bmo.json","wiki_vote_trace.json"]
    present = [w for w in want if (md/w).exists()]
    objs = {}
    for fn in sorted([p for p in md.glob("*.json") if p.name not in ("claims.json","provenance.json")]):
        try:
            objs[fn.name] = json.load(open(fn, "rb"))
        except Exception as e:
            print(f"WARNING: skip {fn.name}: {e}", file=sys.stderr)

    # Compute canonical bundle hash
    if all((md/w).exists() for w in want):
        bundle = json.dumps({"taxi": objs["taxi_markov.json"],
                             "rmsk": objs["rmsk_chr1_bmo.json"],
                             "graph": objs["wiki_vote_trace.json"]}, sort_keys=True).encode()
    else:
        # fall back: stable dict by filename
        bundle = json.dumps({k: objs[k] for k in sorted(objs.keys())}, sort_keys=True).encode()
    bundle_sha = hashlib.sha256(bundle).hexdigest()

    # claims.json
    claims = claims_from_manifests(objs)
    (md/"claims.json").write_text(json.dumps(claims, indent=2), encoding="utf-8")

    # provenance.json
    prov = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python": {"version": sys.version},
        "packages": {},
        "bundle_sha256": bundle_sha,
        "manifests": { str((md/k).as_posix()): {"sha256": hpath(md/k)} for k in sorted(objs.keys()) }
    }
    prov_path = md/"provenance.json"
    prov_path.write_text(json.dumps(prov, indent=2), encoding="utf-8")

    month = os.environ.get("MONTH", "UNKNOWN")
    name = args.out_zip_name or f"freeze_{month}_{bundle_sha[:12]}.zip"

    with zipfile.ZipFile(name, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in ["taxi_markov.json","rmsk_chr1_bmo.json","wiki_vote_trace.json","claims.json","provenance.json"]:
            q = md/p
            if q.exists(): z.write(q, arcname=p)
    print("ZIP", name)

if __name__ == "__main__":
    main()
