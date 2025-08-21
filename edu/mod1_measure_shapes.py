import argparse, os
import numpy as np
import matplotlib.pyplot as plt
from common import now_iso, write_manifest, save_plot

def f(x):
    # f(x) = sin(1/x), safe near 0 with NaNs set to 0
    with np.errstate(divide="ignore", invalid="ignore"):
        y = np.sin(1.0 / x)
    return np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)

def riemann_midpoint(func, a, b, n):
    n = int(n)
    h = (b - a) / n
    i = np.arange(n)
    xm = a + (i + 0.5) * h
    s = np.sum(func(xm))
    return float(h * s)  # ensure plain Python float

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--a", type=float, default=0.001)
    p.add_argument("--b", type=float, default=1.0)
    p.add_argument("--n", type=int, default=20000)
    p.add_argument("--eps", type=float, default=1e-3)  # accepted but unused in this demo
    p.add_argument("--plot", default=os.path.join("edu_out","mod1","riemann.png"))
    p.add_argument("--out",  default=os.path.join("edu_out","mod1","measure.json"))
    args = p.parse_args()

    # compute midpoint estimate
    est = riemann_midpoint(f, args.a, args.b, args.n)

    # figure
    os.makedirs(os.path.dirname(args.plot), exist_ok=True)
    xs = np.linspace(args.a, args.b, 2000)
    ys = f(xs)
    plt.figure(figsize=(6,3))
    plt.plot(xs, ys, linewidth=1)

    # a small set of rectangles for visualization
    nrect = min(60, max(1, args.n))
    hr = (args.b - args.a) / nrect
    i = np.arange(nrect)
    xm = args.a + (i + 0.5) * hr
    fm = f(xm)
    for xi, yi in zip(xm, fm):
        plt.plot([xi-0.5*hr, xi+0.5*hr, xi+0.5*hr, xi-0.5*hr, xi-0.5*hr],
                 [0,0,yi,yi,0], linewidth=0.5)
    plt.title("Midpoint Riemann sum of sin(1/x) on [0.001, 1]")
    plt.xlabel("x"); plt.ylabel("f(x)")
    save_plot(args.plot)

    # manifest
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    write_manifest(args.out, {
        "module": "mod1_measure_shapes",
        "timestamp": now_iso(),
        "params": {"a": args.a, "b": args.b, "n": args.n, "eps": args.eps},
        "metrics": {"integral_midpoint": est},
        "artifacts": {"riemann_plot": args.plot}
    })

    print(f"[mod1] integral≈{est:.6f}; plot→ {args.plot}; manifest→ {args.out}")

if __name__ == "__main__":
    main()
