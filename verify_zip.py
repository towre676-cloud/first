import sys, os, json, zipfile, hashlib

def h_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def main():
    if len(sys.argv) != 2:
        print("Usage: python verify_zip.py <freeze_YYYY-MM_<hashprefix>.zip>"); sys.exit(2)
    zip_path = sys.argv[1]
    if not os.path.exists(zip_path):
        print(f"ERROR: zip not found: {zip_path}"); sys.exit(2)

    ok = True
    with zipfile.ZipFile(zip_path, "r") as z:
        names = set(z.namelist())
        if "provenance.json" not in names:
            print("ERROR: provenance.json missing from zip"); sys.exit(1)
        prov = json.loads(z.read("provenance.json"))
        expect_bundle = prov.get("bundle_sha256", "")
        expect_files  = prov.get("manifests", {})

        print(f"ZIP: {os.path.basename(zip_path)}")
        print("— file digests —")
        for k, meta in expect_files.items():
            base = os.path.basename(k)
            if base not in names:
                print(f"{base:22} MISSING"); ok = False; continue
            got = h_bytes(z.read(base)); exp = meta.get("sha256", "")
            print(f"{base:22} {got}  {'OK' if got==exp else 'MISMATCH'}")
            ok = ok and (got == exp)

        need = ["taxi_markov.json", "rmsk_chr1_bmo.json", "wiki_vote_trace.json"]
        if all(n in names for n in need):
            m1 = json.loads(z.read("taxi_markov.json"))
            m2 = json.loads(z.read("rmsk_chr1_bmo.json"))
            m3 = json.loads(z.read("wiki_vote_trace.json"))
            bundle = json.dumps({"taxi": m1, "rmsk": m2, "graph": m3}, sort_keys=True).encode()
            got_bundle = h_bytes(bundle)
            print("\n— bundle hash —")
            print("bundle_sha256 =", got_bundle)
            print("expected      =", expect_bundle, ("OK" if got_bundle==expect_bundle else "MISMATCH"))
            ok = ok and (got_bundle == expect_bundle)
        else:
            print("WARN: missing one or more manifests needed to recompute bundle hash")
            ok = False

    print("\nALL OK ✅" if ok else "\nVERIFICATION FAILED ❌")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
