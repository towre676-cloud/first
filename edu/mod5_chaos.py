import argparse, numpy as np, math
from common import now_iso, write_manifest, save_plot
from matplotlib import pyplot as plt

def logistic_series(r, x0, N, burn=1000):
    x=x0
    xs=[]
    for _ in range(burn): x = r*x*(1-x)
    for _ in range(N): x = r*x*(1-x); xs.append(x)
    return np.array(xs)

def lyapunov(r, xs): return float(np.mean(np.log(abs(r*(1-2*xs)))))

def symbol_entropy(bits, k=3):
    # k-gram entropy per symbol
    if len(bits)<k: return 0.0
    from collections import Counter
    grams = Counter(tuple(bits[i:i+k]) for i in range(len(bits)-k+1))
    total = sum(grams.values())
    ps = [c/total for c in grams.values()]
    Hk = -sum(p*math.log2(p) for p in ps)
    return Hk / k

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--r", type=float, default=4.0)
    ap.add_argument("--x0", type=float, default=0.123456)
    ap.add_argument("--N", type=int, default=20000)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--out", default="edu_out/mod5/chaos.json")
    ap.add_argument("--plot", default="edu_out/mod5/chaos.png")
    args=ap.parse_args()

    xs = logistic_series(args.r, args.x0, args.N)
    lam = lyapunov(args.r, xs)
    bits = (xs>0.5).astype(int)
    Hk = symbol_entropy(bits, k=args.k)
    hks = max(0.0, lam)/math.log(2.0)

    fig,axs=plt.subplots(1,2, figsize=(9,3))
    axs[0].plot(xs[:2000], lw=0.7); axs[0].set_title("logistic trajectory (first 2k)")
    axs[1].hist(xs, bins=100); axs[1].set_title("empirical density")
    save_plot(fig, args.plot)

    write_manifest(args.out, {
        "module":"mod5_chaos",
        "created_at": now_iso(),
        "parameters":{"r":args.r,"x0":args.x0,"N":args.N,"k":args.k},
        "metrics":{"lyapunov": lam, "entropy_k_bits_per_step": Hk, "h_KS_bits_per_step": hks},
        "artifacts":{"plot": args.plot}
    })
    print(f"[mod5] λ={lam:.4f}, H_{args.k}/step={Hk:.4f}, h_KS≈{hks:.4f}; plot→ {args.plot}; manifest→ {args.out}")

if __name__=="__main__":
    main()
