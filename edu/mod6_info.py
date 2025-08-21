import argparse, os, json, zlib, bz2, lzma
import numpy as np
from common import now_iso, write_manifest

def entropy_bits_per_byte(data: bytes) -> float:
    if not data: return 0.0
    b = np.frombuffer(data, dtype=np.uint8)
    hist = np.bincount(b, minlength=256).astype(np.float64)
    p = hist / hist.sum()
    p = p[p > 0]
    return float(-np.sum(p * np.log2(p)))

def adjacent_mutual_info_bits(data: bytes) -> float:
    if len(data) < 2: return 0.0
    b = np.frombuffer(data, dtype=np.uint8)
    x, y = b[:-1], b[1:]
    joint, _, _ = np.histogram2d(x, y, bins=256, range=[[0,255],[0,255]])
    joint = joint.astype(np.float64)
    Z = joint.sum()
    if Z == 0: return 0.0
    joint /= Z
    px = joint.sum(axis=1, keepdims=True)
    py = joint.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        logterm = np.log2(joint) - np.log2(px) - np.log2(py)
        logterm[~np.isfinite(logterm)] = 0.0
    return float(np.sum(joint * logterm))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--out",  default=os.path.join("edu_out","mod6","info.json"))
    args = ap.parse_args()

    data = open(args.file, "rb").read()
    H = entropy_bits_per_byte(data)
    I = adjacent_mutual_info_bits(data)
    n = len(data)

    comp_bytes = {
        "zlib": zlib.compress(data, level=9),
        "bz2":  bz2.compress(data, compresslevel=9),
        "lzma": lzma.compress(data, preset=6),
    }
    ratios = {k: len(v)/n if n else 0.0 for k, v in comp_bytes.items()}
    sizes  = {"original": n, **{k: len(v) for k, v in comp_bytes.items()}}

    payload = {
        "module": "mod6_info",
        "created_at": now_iso(),
        "parameters": {"file": os.path.abspath(args.file)},
        "metrics": {
            "byte_entropy_bits": H,
            "adjacent_mutual_info_bits": I,
            "compression_ratios": ratios,
            "sizes_bytes": sizes,
        },
    }
    if n < 4096:
        payload["note"] = ("Very small file: container headers/dictionaries can dominate, "
                           "so ratios may exceed 1 even if the data is structured.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    write_manifest(args.out, payload)
    print(f"[mod6] size={n}B, H≈{H:.3f}, I_adj≈{I:.3f}; ratios {ratios}; manifest→ {args.out}")

if __name__ == "__main__":
    main()
