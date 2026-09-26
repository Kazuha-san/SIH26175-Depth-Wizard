"""
STAGE 3 -- Mesh prep + packaging.

SHAPE CLEANUP + SMOOTHING (numpy/opencv, cheap, fast to iterate):
   - flatten_planar_classes(): per-instance plane-fit snapping on
     "should be flat-topped" classes (buildings), using the land-cover
     mask -- this is the fix for the domed/blobby building shapes seen
     during Stage 1 evaluation, done as POST-processing on the height
     map rather than by fighting the depth model's loss function (that
     approach -- structure_loss -- was tried and reverted; see
     stage1_depth.py's module docstring for why).
   - smooth_dsm(): edge-aware guided-filter smoothing (reuses
     utils.image_utils.guided_filter) to remove pixel-level speckle
     without smearing real edges.

PACKAGING:
   - package_result_for_frontend(): packages the cleaned DSM + confidence
     map + RGB texture as lightweight JSON for the Three.js viewer, which
     builds its own mesh client-side via GPU vertex displacement. This is
     the only consumption path -- the live, navigable flythrough.
   Consumes the same cleaned-up DSM that flatten_planar_classes/smooth_dsm
   produce, so what gets rendered always reflects the full cleanup pass.
"""
import base64
import io
import logging

import numpy as np

logger = logging.getLogger(__name__)


def flatten_planar_classes(dsm: np.ndarray, landcover_mask: np.ndarray,
                            class_ids=None, min_pixels: int = 30,
                            gable_residual_threshold_frac: float = 0.12,
                            min_pixels_per_gable_half: int = 40) -> np.ndarray:
    """
    Per-instance plane-fit snapping: for each connected blob of a
    "planar" land-cover class (buildings, by default -- see
    config.PLANAR_LANDCOVER_CLASSES), fit a tilted plane z = a*x + b*y + c
    to that blob's raw predicted heights via least squares, then replace
    every pixel in the blob with the plane's value at that pixel.

    This directly manufactures flat rooftops / sharp walls -- the thing
    the structure_loss training experiment was trying (and failing) to
    achieve -- because we're not fighting the network's gradients, we're
    imposing planarity where the land-cover mask already tells us it
    should exist. A plane (not a single constant) is used so pitched/
    sloped roofs (shed/mono-pitch -- a single tilted plane already covers
    these, which is most real warehouse roofs) aren't flattened into
    something visually wrong.

    GABLE/HIP ROOFS: a single plane fit across a whole gable roof would
    average both slopes into one wrong tilted plane instead of a ridge.
    If the single-plane fit's residual is too high relative to the
    blob's own height range (gable_residual_threshold_frac), this
    reruns as a two-plane fit instead: PCA on the blob's pixel
    coordinates finds its long axis (a gable ridge typically runs along
    a building's long axis), the blob is split into two halves along
    the SHORT axis (i.e. each half is one roof slope, ridge down the
    middle), and each half gets its own independent plane fit. This is
    an approximation built entirely from the depth model's own signal +
    the land-cover mask -- it does not attempt to detect hip roofs (4
    planes) specifically, and if the depth model's raw prediction only
    weakly captures the ridge in the first place (plausible for a
    shallow-pitch roof from a near-overhead view), the split can still
    end up close to the single-plane result. Falls back to the single
    plane whenever either half would be too small to fit reliably.

    Tree canopy is deliberately NOT in the default class list: canopy has
    real internal height variance (individual branches/gaps) that a plane
    fit would misrepresent -- that's a case for the confidence overlay
    (Innovation #2) to flag as "uncertain", not for flattening.

    class_ids: iterable of land-cover class IDs to flatten. Defaults to
        config.PLANAR_LANDCOVER_CLASSES mapped through
        config.LANDCOVER_CLASS_IDS.
    min_pixels: connected components smaller than this are left
        untouched -- a plane fit on a handful of pixels is unstable and
        more likely to be mask noise than a real building.
    """
    from scipy import ndimage
    from app import config

    if class_ids is None:
        class_ids = [config.LANDCOVER_CLASS_IDS[name] for name in config.PLANAR_LANDCOVER_CLASSES]

    if dsm.shape != landcover_mask.shape:
        raise ValueError(
            f"dsm shape {dsm.shape} must match landcover_mask shape {landcover_mask.shape}."
        )

    result = dsm.copy()
    yy, xx = np.mgrid[0:dsm.shape[0], 0:dsm.shape[1]]

    n_gable_split = 0

    for class_id in class_ids:
        class_mask = (landcover_mask == class_id)
        if not np.any(class_mask):
            continue

        labeled, n_blobs = ndimage.label(class_mask)

        if logger.isEnabledFor(logging.DEBUG):
            blob_sizes = sorted(
                (int((labeled == b).sum()) for b in range(1, n_blobs + 1)), reverse=True
            )
            logger.debug(
                "flatten_planar_classes: class_id=%s n_blobs=%d total_pixels=%d top3=%s",
                class_id, n_blobs, int(class_mask.sum()), blob_sizes[:3],
            )

        for blob_id in range(1, n_blobs + 1):
            blob_mask = labeled == blob_id
            n_pixels = int(blob_mask.sum())
            if n_pixels < min_pixels:
                continue  # leave small/noisy blobs untouched

            x = xx[blob_mask].astype(np.float64)
            y = yy[blob_mask].astype(np.float64)
            z = dsm[blob_mask].astype(np.float64)

            valid = np.isfinite(z)
            if valid.sum() < min_pixels:
                continue
            x_valid, y_valid, z_valid = x[valid], y[valid], z[valid]

            # Fit on robust inliers only (see _robust_inlier_mask) so a
            # localized hallucinated cluster can't drag the whole roof's
            # plane up/down to match it. Falls back to all valid pixels
            # if too few survive (degenerate/small blob -- not enough
            # left to trust a "trimmed" fit over just using everything).
            inliers = _robust_inlier_mask(z_valid)
            if inliers.sum() < min_pixels:
                inliers = np.ones_like(z_valid, dtype=bool)
            x_fit, y_fit, z_fit = x_valid[inliers], y_valid[inliers], z_valid[inliers]

            single_coeffs = _fit_plane_lstsq(x_fit, y_fit, z_fit)
            single_plane_fitted = _eval_plane(single_coeffs, x_fit, y_fit)
            residual_rms = float(np.sqrt(np.mean((single_plane_fitted - z_fit) ** 2)))
            # Robust range (from the inlier set), NOT the raw z_valid
            # range -- z_valid.max() can literally BE the hallucinated
            # outlier we're trying to protect against, so clipping to it
            # later would still let the whole roof sit right up against
            # that inflated ceiling.
            height_range = float(z_fit.max() - z_fit.min())

            # Evaluate over the FULL blob (not just the valid subset) so any
            # NaN/invalid pixels inside the footprint get filled by the
            # fitted plane too, same as before this function tracked residuals.
            plane_values = _eval_plane(single_coeffs, x, y)
            if height_range > 1e-6 and (residual_rms / height_range) > gable_residual_threshold_frac:
                # Same robust-inlier protection for the gable fit: build a
                # "valid AND inlier" mask over the full blob so
                # _try_gable_split's PCA/plane fitting also ignores the
                # hallucinated cluster, not just the single-plane path.
                valid_trimmed = valid.copy()
                valid_trimmed[valid] = inliers
                gable_values, gable_residual_rms = _try_gable_split(
                    x, y, z, valid_trimmed, min_pixels_per_gable_half
                )
                # FIX: a high single-plane residual isn't proof this roof
                # is actually a gable -- it's just as often the depth
                # model's own known noise on an ordinarily FLAT rooftop
                # (see stage1_depth's docstring on why v5's structure_loss
                # experiment was reverted). Forcing a two-plane hinge fit
                # onto noise it doesn't real describe lets the fit chase
                # that noise: `a`/`b` come out large, and the resulting
                # tent shape spikes wherever |u| and v are largest -- one
                # corner of the footprint -- producing an unnatural sharp
                # peak instead of a flat roof. Only actually commit to the
                # gable fit if it's a MEANINGFULLY better fit than staying
                # flat; otherwise a flat (if imperfect) single plane is
                # the safer, more honest answer than a confident wrong
                # spike.
                if (
                    gable_values is not None
                    and gable_residual_rms < 0.7 * residual_rms
                ):
                    plane_values = gable_values
                    n_gable_split += 1

            # FIX: whichever fit was used (single-plane or gable), never
            # let it extrapolate beyond the heights actually observed on
            # this roof. A footprint isn't a rectangle -- odd/concave
            # corners can sit far from the fit's centroid, where even a
            # decent-in-aggregate plane fit extrapolates to an
            # unrealistic value. Clamped to the ROBUST [z_fit.min(),
            # z_fit.max()] range, not the raw z_valid range -- z_valid's
            # own max can literally BE the hallucinated outlier we just
            # excluded from fitting, so clipping to it would still let a
            # dragged-up plane sit right at that inflated ceiling.
            plane_values = np.clip(plane_values, z_fit.min(), z_fit.max())

            result[blob_mask] = plane_values

    if n_gable_split:
        logger.debug("flatten_planar_classes: %d blob(s) fit as two-plane (gable-style) roofs", n_gable_split)

    return result


def _robust_inlier_mask(z: np.ndarray, k: float = 3.5) -> np.ndarray:
    """
    Returns a boolean mask marking which of `z`'s values are "inliers" by
    a robust (median/MAD-based) outlier test, for use BEFORE plane fitting.

    WHY THIS EXISTS: a plane's constant term is essentially the fitted
    blob's mean height, and the ordinary mean/least-squares fit has no
    protection against outliers. Depth-model hallucination -- a real,
    documented failure mode (see config.py's DSM_OUTLIER_CLAMP_PERCENTILES
    comments) -- can put a cluster of too-high pixels anywhere in a
    building's footprint. Even a modest fraction of such pixels drags the
    ENTIRE fitted plane upward to match, turning one bad patch into the
    whole roof appearing to float far above its true height -- worse than
    doing nothing, since flattening spreads the error across the full
    footprint instead of leaving it localized.

    Median + MAD (median absolute deviation) is used instead of
    mean/stddev specifically because those are themselves not robust --
    an outlier cluster inflates the mean and stddev too, weakening
    exactly the check meant to catch it. 1.4826 rescales MAD to be
    comparable to a standard deviation under a normal distribution, so
    k=3.5 behaves similarly to a ~3.5-sigma cutoff.

    If MAD is ~0 (blob is extremely uniform, no real spread to measure),
    everything is treated as an inlier -- there's nothing to robustly
    reject against.
    """
    median = np.median(z)
    mad = np.median(np.abs(z - median))
    if mad < 1e-9:
        return np.ones_like(z, dtype=bool)
    scaled_mad = 1.4826 * mad
    return np.abs(z - median) <= k * scaled_mad


def _fit_plane_lstsq(x: np.ndarray, y: np.ndarray, z: np.ndarray):
    """Least-squares fit of z = a*x + b*y + c. Returns (a, b, c)."""
    A = np.column_stack([x, y, np.ones_like(x)])
    coeffs, *_ = np.linalg.lstsq(A, z, rcond=None)
    return coeffs


def _eval_plane(coeffs, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    a, b, c = coeffs
    return a * x + b * y + c


def _try_gable_split(x: np.ndarray, y: np.ndarray, z: np.ndarray,
                      valid: np.ndarray, min_pixels_per_half: int):
    """
    Attempts a two-plane (gable-style) fit: PCA on (x, y) of the VALID
    pixels finds the blob's long axis (the ridge direction) and short
    axis (perpendicular to the ridge).

    FIX: this used to fit each half of the blob as a FULLY INDEPENDENT
    plane (a*x + b*y + c, separate a/b/c per side). Nothing constrained
    those two planes to agree in height where they meet, so at the split
    line -- a dead-straight PCA-derived line right through the blob's
    centroid -- there was almost always a vertical jump between the two
    planes' values. That jump rendered as a sharp, perfectly straight
    ridge/trench slicing across the roof: not a real gable ridge (which
    is a slope change, not a height discontinuity), just two mismatched
    planes stitched together with no shared seam.

    Instead, fit ONE continuous hinge surface in ridge-aligned
    coordinates: z = a*|u| + b*v + c, where u is signed distance from the
    ridge line (short-axis projection) and v is position along the ridge
    (long-axis projection). |u| makes the surface a "tent" -- V-shaped in
    cross-section -- that is mathematically guaranteed to be continuous
    (height matches exactly) at u=0, i.e. exactly along the ridge, while
    `a` and `b` still let each side tilt independently to fit the real
    slopes. This is the actual shape of a gable roof: two planes meeting
    cleanly at a ridge line, never a vertical step.

    Returns (values, residual_rms): values is the combined per-pixel
    surface for the full blob, in the same order as x/y; residual_rms is
    this fit's own RMS residual over the valid pixels, so the caller can
    compare it against the single-plane fit's residual before deciding
    whether committing to a gable shape is actually justified, rather
    than just trusting a high single-plane residual as proof of a real
    ridge. Returns (None, None) if either half would be too small to
    trust.
    """
    x_valid, y_valid, z_valid = x[valid], y[valid], z[valid]

    coords = np.column_stack([x_valid, y_valid])
    centroid = coords.mean(axis=0)
    centered_valid = coords - centroid
    cov = np.cov(centered_valid.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    short_axis = eigvecs[:, np.argmin(eigvals)]  # perpendicular to the ridge
    long_axis = eigvecs[:, np.argmax(eigvals)]   # along the ridge

    u_valid = centered_valid @ short_axis
    v_valid = centered_valid @ long_axis

    side_a_valid = u_valid >= 0
    side_b_valid = ~side_a_valid
    if side_a_valid.sum() < min_pixels_per_half or side_b_valid.sum() < min_pixels_per_half:
        return None, None

    # z = a*|u| + b*v + c, least squares over valid points.
    A = np.column_stack([np.abs(u_valid), v_valid, np.ones_like(u_valid)])
    coeffs, *_ = np.linalg.lstsq(A, z_valid, rcond=None)
    a, b, c = coeffs

    fitted_valid = a * np.abs(u_valid) + b * v_valid + c
    residual_rms = float(np.sqrt(np.mean((fitted_valid - z_valid) ** 2)))

    # Evaluate over the FULL blob (including invalid/NaN positions) so
    # gaps get filled, same as the single-plane path.
    centered_full = np.column_stack([x, y]) - centroid
    u_full = centered_full @ short_axis
    v_full = centered_full @ long_axis
    values = a * np.abs(u_full) + b * v_full + c
    return values, residual_rms



def smooth_dsm(dsm: np.ndarray, rgb_guide: np.ndarray) -> np.ndarray:
    """
    Edge-aware smoothing of the (optionally already plane-flattened) DSM,
    using the original RGB image as the guide so real edges (building
    outlines, ridgelines) are preserved while pixel-level speckle noise
    is removed -- a naive Gaussian blur would smear away exactly the
    edges flatten_planar_classes() just sharpened.

    Reuses the same guided_filter already validated in Stage 1's own
    inference path (utils.image_utils.guided_filter), so smoothing
    behavior is consistent across the pipeline rather than two different
    filters doing conceptually the same job differently.
    """
    from app.utils.image_utils import guided_filter

    return guided_filter(rgb_guide, dsm, radius=4, eps=1e-3)


def clean_dsm_for_mesh(dsm: np.ndarray, rgb_guide: np.ndarray,
                        landcover_mask: np.ndarray = None) -> np.ndarray:
    """
    Convenience wrapper chaining the full Stage 3 cleanup:
    plane-fit flattening (only if a land-cover mask is available) ->
    edge-aware smoothing. This is what pipeline.py / the API route should
    call before handing the DSM to package_result_for_frontend().

    Order matters: flatten buildings first (uses raw heights for the
    plane fit), THEN the final edge-aware smoothing pass over everything
    (including now-flattened buildings). Tree pixels are left untouched
    here -- real per-tree height is needed by detect_tree_instances()
    downstream, so nothing erases/suppresses it in this cleanup pass.
    """
    from app import config

    logger.debug(
        "clean_dsm_for_mesh: shape=%s min=%.4f max=%.4f std=%.4f landcover_mask=%s",
        dsm.shape, dsm.min(), dsm.max(), dsm.std(),
        "none" if landcover_mask is None else f"present shape={landcover_mask.shape}",
    )

    cleaned = dsm
    if landcover_mask is not None:
        cleaned = flatten_planar_classes(cleaned, landcover_mask)
    smoothed = smooth_dsm(cleaned, rgb_guide)

    # BUG FIX: smooth_dsm's guided filter (radius=4) was re-blurring the
    # sharp plane-fit edges flatten_planar_classes() just created -- the
    # docstring above even says "edges flatten_planar_classes() just
    # sharpened" but the code never actually protected them from this
    # pass, so every flattened building got melted right back into a
    # sloped blob. Composite: keep the exact flattened plane value on
    # building pixels (they don't need denoising, they're already a
    # deliberate flat plane, not raw model output), take the smoothed
    # value everywhere else (trees/ground/roads genuinely need the
    # noise reduction).
    if landcover_mask is not None:
        planar_ids = [config.LANDCOVER_CLASS_IDS[name] for name in config.PLANAR_LANDCOVER_CLASSES]
        planar_pixel_mask = np.isin(landcover_mask, planar_ids)
        result = np.where(planar_pixel_mask, cleaned, smoothed)
        logger.debug(
            "clean_dsm_for_mesh: protected %d planar (building) pixels from post-flatten smoothing",
            int(planar_pixel_mask.sum()),
        )
    else:
        result = smoothed

    # Global outlier clamp -- catches raw depth hallucination (a tall
    # dome/ridge in ground/vegetation terrain that flatten/suppress don't
    # touch, since they only target building/tree pixels specifically).
    # Only clips NON-building pixels, and percentile bounds are computed
    # from non-building pixels too, so a legitimate flattened building
    # roof at the high end of the range can't get clipped by its own fix.
    if landcover_mask is not None:
        planar_ids = [config.LANDCOVER_CLASS_IDS[name] for name in config.PLANAR_LANDCOVER_CLASSES]
        planar_pixel_mask = np.isin(landcover_mask, planar_ids)

        # FIX: percentile bounds used to be computed from ALL non-building
        # pixels, including tree canopy -- if a scene is mostly tree cover
        # and that canopy is hallucinating elevated height (confirmed: the
        # nearest-neighbor tree fix barely engaged, 0/24489 px in one real
        # run, meaning neighboring non-tree pixels are ALSO elevated), the
        # 97th percentile is computed from a mostly-contaminated
        # population and doesn't clip anything meaningful. Reference
        # bounds now come from ONLY ground+road pixels specifically --
        # the flattest, most reliable classes, least likely to hallucinate
        # -- so the clamp has a trustworthy baseline regardless of how
        # much of the image is tree-covered.
        reference_ids = [
            config.LANDCOVER_CLASS_IDS[name]
            for name in ("ground", "road")
            if name in config.LANDCOVER_CLASS_IDS
        ]
        reference_mask = np.isin(landcover_mask, reference_ids)
        min_reference_pixels = 200
        if reference_mask.sum() >= min_reference_pixels:
            reference_values = result[reference_mask]
            reference_source = "ground+road"
        else:
            reference_values = result[~planar_pixel_mask]
            reference_source = "all non-building (ground+road too sparse in this scene)"

        if reference_values.size > 0:
            lo_pct, hi_pct = config.DSM_OUTLIER_CLAMP_PERCENTILES
            lo, hi = np.percentile(reference_values, [lo_pct, hi_pct])
            before_max = result.max()
            clamped_non_planar = np.clip(result, lo, hi)
            result = np.where(planar_pixel_mask, result, clamped_non_planar)
            logger.debug(
                "clean_dsm_for_mesh: outlier clamp (reference=%s, n=%d): [%.4f, %.4f] "
                "(was max=%.4f, now max=%.4f)",
                reference_source, reference_values.size, lo, hi, before_max, result.max(),
            )

    return result


def extract_building_footprints(landcover_mask: np.ndarray, dsm: np.ndarray,
                                 class_id: int = None, min_area_px: int = 30,
                                 polygon_epsilon_frac: float = 0.01) -> list:
    """
    Vectorizes each connected building blob into a real footprint polygon
    (contour extraction + Douglas-Peucker simplification), instead of
    treating every building as an axis-aligned rectangle. The frontend
    extrudes walls along this actual outline (L-shapes, irregular blobs,
    whatever the segmentation model found) from height_base up to the
    per-pixel roof height already baked into the DSM by
    flatten_planar_classes() -- roof PITCH (including gable ridges) comes
    from the DSM itself at render time, this function only needs to supply
    where the building's footprint boundary actually is and how high off
    the ground it starts, so walls are sharp instead of the DSM's smooth
    ground-to-roof transition.

    Coordinates in each polygon are normalized to [0, 1] (fraction of
    image width/height), independent of DSM/mask resolution, so the
    frontend can scale them onto whatever mesh resolution it's using.

    Returns a list of dicts:
        {
            "polygon": [[x0, y0], [x1, y1], ...],  # normalized 0..1
            "height_base": float,  # local ground level this building sits on
            "height_top": float,   # representative roof height (median) --
                                    # a fallback for simple rendering; for
                                    # actual roof shape (incl. gable ridges)
                                    # the frontend should sample the DSM
                                    # heightmap inside this polygon instead.
        }
    """
    import cv2
    from scipy import ndimage
    from app import config

    if class_id is None:
        class_id = config.LANDCOVER_CLASS_IDS["building"]

    h, w = landcover_mask.shape
    mask = (landcover_mask == class_id).astype(np.uint8)
    if not np.any(mask):
        return []

    labeled, n_blobs = ndimage.label(mask)
    footprints = []

    for blob_id in range(1, n_blobs + 1):
        blob_mask = (labeled == blob_id).astype(np.uint8)
        if int(blob_mask.sum()) < min_area_px:
            continue

        contours, _ = cv2.findContours(blob_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(contour) < min_area_px:
            continue

        perimeter = cv2.arcLength(contour, True)
        epsilon = max(1.0, polygon_epsilon_frac * perimeter)
        simplified = cv2.approxPolyDP(contour, epsilon, True)
        if len(simplified) < 3:
            continue  # degenerate polygon, skip rather than render garbage

        polygon = [[float(pt[0][0]) / w, float(pt[0][1]) / h] for pt in simplified]

        blob_bool = blob_mask.astype(bool)
        blob_heights = dsm[blob_bool]
        blob_heights = blob_heights[np.isfinite(blob_heights)]
        if blob_heights.size == 0:
            continue
        height_top = float(np.median(blob_heights))

        # Base height: sample a thin ring just outside the footprint (not
        # a global 0) so buildings on sloped terrain get the right local
        # ground level instead of all sharing one baseline.
        ring = ndimage.binary_dilation(blob_bool, iterations=3) & ~blob_bool
        ring_heights = dsm[ring]
        ring_heights = ring_heights[np.isfinite(ring_heights)]
        height_base = (
            float(np.percentile(ring_heights, 20)) if ring_heights.size > 0
            else float(np.min(blob_heights))
        )

        footprints.append({
            "polygon": polygon,
            "height_base": height_base,
            "height_top": height_top,
        })

    return footprints


def detect_tree_instances(landcover_mask: np.ndarray, dsm: np.ndarray,
                           class_id: int = None, min_separation_px: int = None,
                           min_canopy_height: float = None,
                           max_instances: int = None) -> list:
    """
    Detects individual tree positions within tree-class pixels via local
    maxima on the RAW height signal (canopy tops read as local peaks in
    the depth model's output -- this only works now that tree height is
    no longer erased by suppression, see clean_dsm_for_mesh's docstring).
    Non-max suppression (min_separation_px, via a KD-tree) keeps one
    instance per real peak instead of many off the same noisy bump.

    This does NOT segment individual tree crowns precisely -- that would
    need an actual instance-segmentation model, not just a landcover class
    mask. It places a plausible number of discrete tree instances at
    plausible positions/heights so the frontend can render real individual
    canopies (an InstancedMesh -- thousands of trees, one draw call) instead
    of one smooth bumpy tree-class surface. A reasonable approximation of
    "where trees roughly are and how tall", not a per-tree-accurate survey.

    Returns a list of dicts: {"x", "y" (normalized 0..1), "height"
    (canopy height above local ground baseline, NOT raw DSM value -- the
    frontend doesn't need to separately know terrain height under each
    tree), "canopy_radius" (normalized, crude distance-to-edge estimate)}.

    max_instances caps the count (keeping the tallest first, since NMS
    processes peaks height-descending) so a scene that's mostly forest
    doesn't hand the frontend an unrenderable number of instances.
    """
    from scipy import ndimage
    from scipy.spatial import cKDTree
    from app import config

    if class_id is None:
        class_id = config.LANDCOVER_CLASS_IDS["tree"]
    if min_separation_px is None:
        min_separation_px = config.TREE_INSTANCE_MIN_SEPARATION_PX
    if min_canopy_height is None:
        min_canopy_height = config.TREE_INSTANCE_MIN_CANOPY_HEIGHT
    if max_instances is None:
        max_instances = config.MAX_TREE_INSTANCES

    h, w = landcover_mask.shape
    tree_mask = (landcover_mask == class_id)
    if not np.any(tree_mask):
        return []

    non_tree_mask = ~tree_mask
    if np.any(non_tree_mask):
        local_ground_baseline = float(np.percentile(dsm[non_tree_mask], 20))
    else:
        local_ground_baseline = float(np.percentile(dsm[tree_mask], 5))

    footprint_size = max(3, min_separation_px)
    dsm_tree_only = np.where(tree_mask, dsm, -np.inf)
    local_max = ndimage.maximum_filter(dsm_tree_only, size=footprint_size)
    peak_mask = tree_mask & (dsm_tree_only == local_max) & np.isfinite(dsm_tree_only)

    ys, xs = np.where(peak_mask)
    if len(ys) == 0:
        return []

    heights = dsm[ys, xs]
    order = np.argsort(-heights)
    coords = np.column_stack([ys, xs]).astype(float)
    kd = cKDTree(coords)
    suppressed = np.zeros(len(ys), dtype=bool)
    kept_idx = []

    for idx in order:
        if suppressed[idx]:
            continue
        kept_idx.append(idx)
        if len(kept_idx) >= max_instances:
            break
        neighbor_idx = kd.query_ball_point(coords[idx], r=min_separation_px)
        for n in neighbor_idx:
            suppressed[n] = True

    dist_to_edge = ndimage.distance_transform_edt(tree_mask)

    instances = []
    for idx in kept_idx:
        y, x = ys[idx], xs[idx]
        canopy_height = float(dsm[y, x] - local_ground_baseline)
        if canopy_height < min_canopy_height:
            continue
        instances.append({
            "x": float(x) / w,
            "y": float(y) / h,
            "height": canopy_height,
            "canopy_radius": float(dist_to_edge[y, x]) / max(h, w),
        })

    return instances


def _downsample_to_max_resolution(array: np.ndarray, max_resolution: int) -> np.ndarray:
    """Downsamples a 2D or 3D array so its longer side is <= max_resolution."""
    from PIL import Image

    h, w = array.shape[0], array.shape[1]
    scale = min(1.0, max_resolution / max(h, w))
    if scale >= 1.0:
        return array

    new_h, new_w = max(1, int(h * scale)), max(1, int(w * scale))
    if array.ndim == 2:
        img = Image.fromarray(array.astype(np.float32), mode="F")
        return np.array(img.resize((new_w, new_h), Image.BILINEAR))
    else:
        img = Image.fromarray(array.astype(np.uint8))
        return np.array(img.resize((new_w, new_h), Image.BILINEAR))


def _encode_png_base64(array: np.ndarray) -> str:
    """Encodes a numpy array as a base64 PNG data string for JSON transport."""
    from PIL import Image

    img = Image.fromarray(array)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def package_result_for_frontend(dsm: np.ndarray, confidence_map: np.ndarray,
                                 rgb_image: np.ndarray, metadata: dict,
                                 landcover_mask: np.ndarray = None) -> dict:
    """
    Packages the cleaned DSM + confidence map + RGB texture into a
    lightweight, JSON-serializable payload for the /result API response.
    The Three.js frontend builds its own mesh client-side from this data.

    IMPORTANT: downsamples dsm/confidence/rgb to config.MESH_MAX_RESOLUTION
    before encoding -- without this, this function used to send the FULL,
    un-downsampled resolution to the live browser view. On a fixed-size
    display plane (TERRAIN_SIZE in the frontend), that meant per-pixel
    noise in the raw depth output produced near-vertical spikes -- every
    pixel became its own mesh vertex on a plane far too small for that
    vertex density, so noise that would be invisible at a sane resolution
    read as dramatic fake "mountains." Downsampling here also acts as
    extra noise averaging on top of smooth_dsm()'s guided filter, which
    matters most for the relative-only (no SRTM/no calibration) fallback
    path, where the raw Stage 1 output is noisiest.

    building_footprints/tree_instances (when landcover_mask is given) are
    computed at FULL resolution BEFORE downsampling (accuracy matters more
    there than for the base heightmap) and shipped with normalized [0,1]
    coordinates, so they stay correctly placed regardless of the
    heightmap's downsampled resolution.

    Height data is shipped as 16-bit PNG (not 8-bit) to preserve enough
    vertical precision for tall scenes -- an 8-bit heightmap would band
    visibly on a 40m-tall building.

    Returns a dict of JSON-safe values:
        heightmap_png_b64: base64 16-bit grayscale PNG, values scaled to
            [0, 65535] linearly across [height_min, height_max] (both
            included in the response so the frontend can invert the scale)
        confidence_png_b64: base64 8-bit grayscale PNG (or None if no
            uncertainty pass was run), 0=low confidence, 255=high
        texture_png_b64: base64 RGB PNG of the original image, for UV texturing
        height_min / height_max: float, for decoding heightmap_png_b64
        height_units: "meters" if this DSM went through real SRTM
            calibration, "relative" otherwise -- the frontend must NOT
            label relative values with "m", they're not meters
        building_footprints: list from extract_building_footprints(), or
            [] if no landcover_mask was given
        tree_instances: list from detect_tree_instances(), or [] if no
            landcover_mask was given
        metadata: passed through as given (GSD info, calibration method, etc.)
    """
    from app import config

    building_footprints = []
    tree_instances = []
    if landcover_mask is not None:
        building_footprints = extract_building_footprints(landcover_mask, dsm)
        tree_instances = detect_tree_instances(landcover_mask, dsm)

    dsm_ds = _downsample_to_max_resolution(dsm, config.MESH_MAX_RESOLUTION)
    rgb_ds = _downsample_to_max_resolution(rgb_image, config.MESH_MAX_RESOLUTION)
    confidence_ds = (
        _downsample_to_max_resolution(confidence_map, config.MESH_MAX_RESOLUTION)
        if confidence_map is not None else None
    )

    valid = np.isfinite(dsm_ds)
    height_min = float(np.min(dsm_ds[valid])) if np.any(valid) else 0.0
    height_max = float(np.max(dsm_ds[valid])) if np.any(valid) else 1.0
    if height_max <= height_min:
        height_max = height_min + 1.0

    dsm_filled = np.nan_to_num(dsm_ds, nan=height_min)
    normalized = np.clip((dsm_filled - height_min) / (height_max - height_min), 0, 1)
    heightmap_16bit = (normalized * 65535).astype(np.uint16)

    confidence_png_b64 = None
    if confidence_ds is not None:
        confidence_8bit = np.clip(confidence_ds * 255, 0, 255).astype(np.uint8)
        confidence_png_b64 = _encode_png_base64(confidence_8bit)

    calibration_method = metadata.get("calibration_method", "none_relative_only")
    height_units = "meters" if calibration_method != "none_relative_only" else "relative"

    return {
        "heightmap_png_b64": _encode_png_base64(heightmap_16bit),
        "confidence_png_b64": confidence_png_b64,
        "texture_png_b64": _encode_png_base64(rgb_ds.astype(np.uint8)),
        "height_min": height_min,
        "height_max": height_max,
        "height_units": height_units,
        "building_footprints": building_footprints,
        "tree_instances": tree_instances,
        "metadata": metadata,
    }
