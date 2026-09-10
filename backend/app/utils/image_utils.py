import numpy as np


def load_image(file_path: str) -> np.ndarray:
    """
    Loads PNG/JPG/GeoTIFF as an (H, W, 3) uint8 RGB numpy array.

    For GeoTIFF inputs we deliberately go through rasterio, not PIL --
    PIL can silently mis-handle multi-band or non-8-bit GeoTIFFs (e.g.
    16-bit Sentinel-2 bands), whereas rasterio reads the raw band data
    faithfully. We take the first 3 bands as RGB and rescale to uint8
    if the source isn't already 8-bit, since the depth model expects a
    standard [0,255] RGB image regardless of the source's bit depth.
    """
    import os

    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".tif", ".tiff"):
        import rasterio

        with rasterio.open(file_path) as src:
            band_count = min(3, src.count)
            arr = src.read(list(range(1, band_count + 1)))  # (bands, H, W)
        arr = np.transpose(arr, (1, 2, 0))  # (H, W, bands)
        if arr.shape[2] == 1:
            arr = np.repeat(arr, 3, axis=2)

        if arr.dtype != np.uint8:
            # Rescale using robust percentiles so a few hot/void pixels
            # don't crush the visible dynamic range to near-black/white.
            lo = np.percentile(arr, 1)
            hi = np.percentile(arr, 99)
            if hi <= lo:
                hi = lo + 1.0
            arr = np.clip((arr.astype(np.float32) - lo) / (hi - lo), 0, 1)
            arr = (arr * 255).astype(np.uint8)
        return np.ascontiguousarray(arr)

    from PIL import Image

    img = Image.open(file_path).convert("RGB")
    return np.array(img)


def resize_for_model(image: np.ndarray, target_size: tuple) -> np.ndarray:
    """
    Resizes/pads `image` to `target_size` = (height, width) via a
    center-crop-then-resize rather than a naive stretch, so aspect ratio
    is preserved (a stretched image would distort real-world proportions,
    which matters for a model whose depth cues come partly from shape).

    NOTE: this is a generic "make it the right shape" utility. It is
    NOT a substitute for stage1_depth.normalize_gsd(), which additionally
    accounts for ground-sample-distance -- always run normalize_gsd()
    first on real-world images; use this directly only for cases (tests,
    GAMUS samples already at the right GSD) where GSD matching isn't a
    concern.
    """
    from PIL import Image

    target_h, target_w = target_size
    h, w = image.shape[0], image.shape[1]

    # Center-crop to the target aspect ratio first, then resize -- avoids
    # stretching. If the image is smaller than the target in some
    # dimension, this crop step is a no-op for that dimension.
    target_aspect = target_w / target_h
    src_aspect = w / h

    if src_aspect > target_aspect:
        new_w = int(h * target_aspect)
        left = (w - new_w) // 2
        cropped = image[:, left:left + new_w]
    else:
        new_h = int(w / target_aspect)
        top = (h - new_h) // 2
        cropped = image[top:top + new_h, :]

    pil_img = Image.fromarray(cropped).resize((target_w, target_h), Image.BILINEAR)
    return np.array(pil_img)


def guided_filter(guide: np.ndarray, src: np.ndarray, radius: int = 8, eps: float = 1e-2) -> np.ndarray:
    """
    Edge-preserving guided filter (He et al., ECCV 2010).
    Transfers sharp edges from the RGB/grayscale `guide` onto `src` (depth / height map),
    eliminating blurry upsampling blobs around buildings and street lines.

    guide: (H, W, 3) or (H, W) image (uint8 or float32 in [0, 1])
    src: (H, W) float32 single-channel height/depth map
    radius: local window radius in pixels (default 8)
    eps: regularization parameter penalizing large variance (default 1e-2)
    """
    import cv2
    import numpy as np

    if guide.ndim == 3:
        # Convert RGB guide to grayscale float32 in [0, 1]
        if guide.dtype == np.uint8:
            I = cv2.cvtColor(guide, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        else:
            I = cv2.cvtColor((guide * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    else:
        I = guide.astype(np.float32)
        if I.max() > 1.0:
            I = I / 255.0

    p = src.astype(np.float32)
    ksize = (2 * radius + 1, 2 * radius + 1)

    mean_I = cv2.boxFilter(I, cv2.CV_32F, ksize)
    mean_p = cv2.boxFilter(p, cv2.CV_32F, ksize)
    mean_Ip = cv2.boxFilter(I * p, cv2.CV_32F, ksize)
    cov_Ip = mean_Ip - mean_I * mean_p

    mean_II = cv2.boxFilter(I * I, cv2.CV_32F, ksize)
    var_I = mean_II - mean_I * mean_I

    a = cov_Ip / (var_I + eps)
    b = mean_p - a * mean_I

    mean_a = cv2.boxFilter(a, cv2.CV_32F, ksize)
    mean_b = cv2.boxFilter(b, cv2.CV_32F, ksize)

    q = mean_a * I + mean_b
    return q.astype(src.dtype)

