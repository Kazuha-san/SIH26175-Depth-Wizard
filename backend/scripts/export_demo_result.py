"""
Runs the REAL backend pipeline (your actual trained models, actual
calibration, actual mesh prep) on a real image, then saves a single
self-contained JSON file the standalone demo viewer can load with zero
backend/network dependency at demo time.

Decodes the 16-bit heightmap PNG back into a plain float array HERE
(server-side, with PIL, which handles 16-bit PNGs correctly) rather than
relying on the browser to do it -- browser <canvas> silently collapses
16-bit PNG data to 8-bit on decode, which is a real, easy-to-hit footgun
for a from-scratch demo page. Shipping plain floats sidesteps it entirely.

USAGE (backend must be running -- `uvicorn app.main:app` in another terminal):
    python scripts/export_demo_result.py path/to/image.png --name city_demo
    python scripts/export_demo_result.py path/to/geotiff.tif --name sf_demo

Writes standalone/results/<name>.json -- open standalone/index.html and
pick it from the dropdown (edit RESULTS list at the top of index.html to
add the name once you've generated it).
"""
import argparse
import base64
import io
import json
import os
import sys
import time

import numpy as np
import requests
from PIL import Image

DEFAULT_BACKEND = "http://localhost:8000"
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
OUT_DIR = os.path.join(REPO_ROOT, "standalone", "results")


def decode_heightmap(heightmap_png_b64, height_min, height_max):
    """Inverts package_result_for_frontend's 16-bit encoding back to real floats."""
    raw = base64.b64decode(heightmap_png_b64)
    img = Image.open(io.BytesIO(raw))
    arr = np.array(img).astype(np.float64)  # 16-bit grayscale, values in [0, 65535]
    normalized = arr / 65535.0
    elevation = height_min + normalized * (height_max - height_min)
    return elevation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path", help="Path to a real image to run through the pipeline.")
    parser.add_argument("--name", required=True, help="Output name, e.g. 'city_demo' -> results/city_demo.json")
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--label", default=None, help="Display label for the demo dropdown (defaults to --name).")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Uploading {args.image_path} to {args.backend}/upload ...")
    with open(args.image_path, "rb") as f:
        upload_resp = requests.post(f"{args.backend}/upload", files={"file": f})
    upload_resp.raise_for_status()
    image_id = upload_resp.json()["image_id"]
    print(f"  image_id: {image_id}")

    print("Running pipeline (this is the slow part -- depth + calibration + mesh prep) ...")
    start = time.time()
    process_resp = requests.post(f"{args.backend}/process/{image_id}", timeout=600)
    process_resp.raise_for_status()
    result = process_resp.json()
    print(f"  done in {time.time() - start:.1f}s")

    print("Decoding 16-bit heightmap back to real float elevations ...")
    elevation = decode_heightmap(result["heightmap_png_b64"], result["height_min"], result["height_max"])
    h, w = elevation.shape

    out = {
        "label": args.label or args.name,
        "width": int(w),
        "height": int(h),
        "elevation": elevation.flatten().round(5).tolist(),
        "texture_png_b64": result["texture_png_b64"],
        "confidence_png_b64": result.get("confidence_png_b64"),
        "height_min": result["height_min"],
        "height_max": result["height_max"],
        "height_units": result.get("height_units", "relative"),
        "metadata": {
            "input_type": result.get("input_type", "unknown"),
            "calibration_method": result.get("metadata", {}).get("calibration_method"),
            "srtm_used": result.get("metadata", {}).get("srtm_used"),
        },
    }

    out_path = os.path.join(OUT_DIR, f"{args.name}.json")
    with open(out_path, "w") as f:
        json.dump(out, f)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\nWrote {out_path} ({size_mb:.1f} MB)")
    print(f"Add \"{args.name}\" to the RESULTS list at the top of standalone/index.html to show it in the demo.")


if __name__ == "__main__":
    main()
