import os, json, time
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.floating, np.integer)):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

def write_manifest(out_path, payload):
    Path(os.path.dirname(out_path)).mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, cls=NpEncoder)

def save_plot(arg1, path=None):
    """
    save_plot("path.png")              # uses current figure
    save_plot(fig, "path.png")         # saves that figure
    """
    if path is None:
        # called as save_plot("path.png")
        fig = plt.gcf()
        path = arg1
    else:
        # called as save_plot(fig, "path.png")
        fig = arg1

    Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
    try:
        fig.tight_layout()
    except Exception:
        pass
    if isinstance(fig, Figure):
        fig.savefig(path, dpi=140, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.savefig(path, dpi=140, bbox_inches="tight")
        plt.close()
