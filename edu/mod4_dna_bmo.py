import argparse, numpy as np
from common import now_iso, write_manifest, save_plot
from matplotlib import pyplot as plt

def read_fasta_text(path):
    seq=[]; 
    with open(path,"r",encoding="utf-8",errors="ignore") as f:
        for line in f:
            if not line or line[0]==">": continue
            seq.append(line.strip().upper())
    return "".join(seq)

def sliding_density(seq, win=1000):
    v=np.frombuffer(seq.encode("ascii"), dtype="S1")
    is_gc = np.isin(v, [b"G",b"C"]).astype(float)
    k=len(is_gc)
    if k<win: return np.array([])
    cumsum = np.concatenate([[0.0], np.cumsum(is_gc)])
    dens = (cumsum[win:] - cumsum[:-win]) / win
    return dens

def bmo_star(vals):
    best=0.0
    for B in (16,32,64):
        for i in range(0, len(vals)-B+1):
            blk=vals[i:i+B]
            m=blk.mean()
            osc=np.mean(np.abs(blk-m))
            if osc>best: best=osc
    return best

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fasta", required=True)
    ap.add_argument("--win", type=int, default=1000)
    ap.add_argument("--out", default="edu_out/mod4/dna_bmo.json")
    ap.add_argument("--plot", default="edu_out/mod4/dna_bmo.png")
    args=ap.parse_args()

    seq = read_fasta_text(args.fasta)
    dens = sliding_density(seq, args.win)
    bmo = float(bmo_star(dens)) if len(dens) else 0.0

    xs = np.arange(len(dens))
    from matplotlib import pyplot as plt
    fig=plt.figure(figsize=(9,3))
    plt.plot(xs, dens, lw=0.7); plt.title(f"GC density (win={args.win})")
    plt.xlabel("window index"); plt.ylabel("density")
    save_plot(fig, args.plot)

    write_manifest(args.out, {
        "module":"mod4_dna_bmo",
        "created_at": now_iso(),
        "parameters":{"win":args.win},
        "metrics":{"n_windows": int(len(dens)), "bmo_star": bmo},
        "artifacts":{"plot": args.plot}
    })
    print(f"[mod4] windows={len(dens)} BMO*={bmo:.6f}; plot→ {args.plot}; manifest→ {args.out}")

if __name__=="__main__":
    main()
