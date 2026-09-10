"""
Loads the GAMUS dataset (huggingface.co/datasets/earthflow/GAMUS) for
inference-side use: pulling real RGB tiles + nDSM ground truth + 6-class
land-cover masks for smoke tests, Stage 1<->2 wiring, and manual checks.

NOTE on field names: this was written without a live HF connection to
inspect the dataset's exact column schema (the notebooks that trained v3
DID have that access, but this file wasn't ported from them -- it's new).
`_FIELD_CANDIDATES` below lists the most likely key names for each of the
three things we need (RGB, height, land-cover), in priority order, and
`_first_present_key()` picks whichever one actually exists on a real sample
the first time this runs. If NONE of the candidates match, it raises a
clear KeyError showing the real available keys, rather than silently
returning the wrong field or crashing on a raw KeyError -- if that happens,
add the real key name to the relevant candidates list and re-run.

Class IDs (confirmed via GAMUS paper arXiv 2305.14914 + visual mask check
during Stage 1 training, so THESE are trustworthy, unlike the field-name
guesses above):
    0 = unlabeled, 1 = ground, 2 = low-vegetation, 3 = building,
    4 = water, 5 = road, 6 = tree
"""
import numpy as np

_FIELD_CANDIDATES = {
    "rgb": ["image", "rgb", "rgb_image", "img"],
    "height": ["ndsm", "height", "dsm", "depth", "label"],
    "landcover": ["landcover", "land_cover", "semantic", "mask", "class_mask"],
}

GAMUS_CLASS_NAMES = {
    0: "unlabeled", 1: "ground", 2: "low_vegetation",
    3: "building", 4: "water", 5: "road", 6: "tree",
}


def _first_present_key(sample, field: str):
    """Returns the first candidate key for `field` that exists in `sample`."""
    for key in _FIELD_CANDIDATES[field]:
        if key in sample:
            return key
    raise KeyError(
        f"None of the expected '{field}' field names {_FIELD_CANDIDATES[field]} "
        f"were found on this GAMUS sample. Actual keys present: {list(sample.keys())}. "
        f"Update _FIELD_CANDIDATES['{field}'] in gamus_loader.py with the real key "
        f"name and re-run."
    )


def load_gamus_split(split: str = "test", streaming: bool = True):
    """
    Loads the GAMUS dataset split via in-memory streaming (zero disk download/cache).
    In the Hub repo (earthflow/GAMUS), the dataset is stored as individual H5 files
    under images/<split>/, heights/<split>/, and classes/<split>/.
    Returns a generator yielding sample dictionaries containing paired 'rgb', 'height',
    and 'landcover' arrays.
    """
    import io
    import urllib.request
    import h5py
    from huggingface_hub import HfApi

    api = HfApi()
    all_files = list(api.list_repo_files(repo_id="earthflow/GAMUS", repo_type="dataset"))
    
    prefix = f"images/{split}/"
    rgb_files = [f for f in all_files if f.startswith(prefix) and f.endswith("_RGB.h5")]

    def _stream_h5_array(repo_filepath: str):
        url = f"https://huggingface.co/datasets/earthflow/GAMUS/resolve/main/{repo_filepath}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
        with h5py.File(io.BytesIO(data), "r") as f:
            key = list(f.keys())[0]
            return f[key][:]

    def _generator():
        for rgb_rel in rgb_files:
            base_name = rgb_rel[len(prefix):-len("_RGB.h5")]
            agl_rel = f"heights/{split}/{base_name}_AGL.h5"
            cls_rel = f"classes/{split}/{base_name}_CLS.h5"

            rgb = _stream_h5_array(rgb_rel)

            height = None
            if agl_rel in all_files:
                height = _stream_h5_array(agl_rel)

            cls_mask = None
            if cls_rel in all_files:
                cls_mask = _stream_h5_array(cls_rel)

            yield {
                "id": base_name,
                "rgb": rgb,
                "height": height,
                "landcover": cls_mask,
                "image": rgb,  # backward compatibility
            }

    return _generator()



def get_rgb_image(sample) -> np.ndarray:
    """Extracts the RGB tile from a GAMUS sample as an (H, W, 3) uint8 array."""
    key = _first_present_key(sample, "rgb")
    img = sample[key]
    if hasattr(img, "convert"):  # PIL Image
        img = img.convert("RGB")
        return np.array(img)
    return np.asarray(img)


def get_height_map(sample) -> np.ndarray:
    """Extracts the nDSM/height ground-truth map from a GAMUS sample as (H, W) float."""
    key = _first_present_key(sample, "height")
    arr = sample[key]
    if hasattr(arr, "convert"):
        arr = np.array(arr)
    else:
        arr = np.asarray(arr)
    return arr.astype(np.float32)


def get_landcover_mask(sample) -> np.ndarray:
    """
    Extracts the 6-class semantic land-cover mask for a GAMUS sample as an
    (H, W) int array (used by Stage 2's per-class scale calibration).
    Class IDs per GAMUS_CLASS_NAMES above.
    """
    key = _first_present_key(sample, "landcover")
    arr = sample[key]
    if hasattr(arr, "convert"):
        arr = np.array(arr)
    else:
        arr = np.asarray(arr)
    return arr.astype(np.int64)
