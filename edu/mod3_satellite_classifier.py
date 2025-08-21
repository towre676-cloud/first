import argparse, numpy as np
from PIL import Image
from common import now_iso, write_manifest, save_plot
from matplotlib import pyplot as plt

def laplacian(u):
    return (-4*u + np.roll(u,1,0)+np.roll(u,-1,0)+np.roll(u,1,1)+np.roll(u,-1,1))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--lambda", dest="lmb", type=float, default=0.2)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--tau", type=float, default=0.1)
    ap.add_argument("--out", default="edu_out/mod3/sat.json")
    ap.add_argument("--plot", default="edu_out/mod3/sat.png")
    args=ap.parse_args()

    g = Image.open(args.image).convert("L")
    g = np.asarray(g, dtype=np.float64)/255.0
    u = g.copy()
    for _ in range(args.steps):
        u += args.tau*(laplacian(u) - args.lmb*(u-g))  # gradient descent

    # energy ∫|∇u|^2 dx ≈ sum of squared forward diffs
    ux = np.diff(u, axis=1, append=u[:,-1:])
    uy = np.diff(u, axis=0, append=u[-1:,:])
    H1 = float((ux*ux+uy*uy).sum())

    seg = (u>0.5).astype(float)
    fig,axs=plt.subplots(1,3, figsize=(9,3))
    axs[0].imshow(g, cmap="gray"); axs[0].set_title("input")
    axs[1].imshow(u, cmap="gray"); axs[1].set_title("smoothed")
    axs[2].imshow(seg, cmap="gray"); axs[2].set_title("threshold 0.5")
    for a in axs: a.axis("off")
    save_plot(fig, args.plot)

    write_manifest(args.out, {
        "module":"mod3_satellite_classifier",
        "created_at": now_iso(),
        "parameters":{"lambda":args.lmb,"steps":args.steps,"tau":args.tau},
        "metrics":{"dirichlet_energy": H1},
        "artifacts":{"preview": args.plot}
    })
    print(f"[mod3] H1 energy={H1:.3f}; plot→ {args.plot}; manifest→ {args.out}")

if __name__=="__main__":
    main()
