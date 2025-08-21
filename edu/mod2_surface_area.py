import argparse, numpy as np
from common import now_iso, write_manifest

def delta_sigma(F, sigma):
    return (1.0/(sigma*np.sqrt(2*np.pi))) * np.exp(-0.5*(F/sigma)**2)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--box", type=float, default=1.2, help="integrate over [-box,box]^3")
    ap.add_argument("--dx", type=float, default=0.02)
    ap.add_argument("--sigma", type=float, default=0.02)
    ap.add_argument("--out", default="edu_out/mod2/surface.json")
    args=ap.parse_args()

    L=args.box; dx=args.dx; sig=args.sigma
    xs=np.arange(-L,L+dx,dx); ys=xs; zs=xs
    X,Y,Z=np.meshgrid(xs,ys,zs, indexing="ij")
    F=X*X+Y*Y+Z*Z-1.0
    grad_norm = 2.0*np.sqrt(X*X+Y*Y+Z*Z)
    integrand = delta_sigma(F, sig)*grad_norm
    est = integrand.sum() * (dx**3)
    write_manifest(args.out, {
        "module":"mod2_surface_area",
        "created_at": now_iso(),
        "parameters":{"box":args.box,"dx":dx,"sigma":sig},
        "metrics":{"area_estimate": float(est), "true_sphere_area": float(4*np.pi)}
    })
    print(f"[mod2] area≈{est:.6f} (true 4π≈{4*np.pi:.6f}); manifest→ {args.out}")

if __name__=="__main__":
    main()
