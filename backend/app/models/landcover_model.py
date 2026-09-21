"""
Land-cover segmentation for Stage 2's per-class calibration (Innovation #1).

This closes the gap flagged during integration: GAMUS gives free land-cover
masks for training/testing, but a real uploaded image has none -- Stage 2's
per_class_calibration() needs a `landcover_mask` it can't get any other way.

Architecture matches landcover_segmentation_v6.ipynb EXACTLY (DeepLabV3
with a MobileNetV3-Large backbone, 7-class head) -- this file only loads
that trained checkpoint and runs inference, no training logic here.

Checkpoint: drop the notebook's saved `landcover_seg_v6.pth` (or whichever
version is currently best) at the path passed to load_landcover_model().
Not bundled in this repo -- same pattern as the depth checkpoint.
"""
import numpy as np

MODEL_INPUT_SIZE = 512  # must match the segmentation notebook's IMG_SIZE
NUM_CLASSES = 7  # unlabeled, ground, low_vegetation, building, water, road, tree


class LandcoverLoadError(RuntimeError):
    """Raised when the checkpoint can't be loaded with real trained weights.

    Deliberately loud: the previous version of this loader used
    strict=False and swallowed key mismatches, which meant a checkpoint/
    architecture mismatch would silently leave the classifier (or more)
    randomly initialized -- producing a landcover mask that's effectively
    noise, which in turn meant Stage 3's building-flattening never fired
    and raw noisy depth shipped straight to the mesh. Better to fail here
    than to silently ship a broken mask.
    """


def load_landcover_model(checkpoint_path: str, device: str = None):
    """
    Loads DeepLabV3-MobileNetV3-Large with the 7-class head and applies
    the trained checkpoint's weights.

    Rebuilds the classifier head to the right shape FIRST (based on
    NUM_CLASSES), then loads with strict checking so any real mismatch
    between the checkpoint and this architecture throws instead of
    silently loading a partially-random model. The checkpoint's
    training-only aux_classifier weights are intentionally dropped before
    loading -- inference never reads the aux output, so this doesn't
    affect the landcover mask.
    """
    import torch
    import torch.nn as nn
    from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device)

    ckpt = torch.load(checkpoint_path, map_location=device)
    # Notebook saves {"model_state": ..., "optimizer_state": ..., "epoch": ..., "best_iou": ...}
    state_dict = ckpt["model_state"] if isinstance(ckpt, dict) and "model_state" in ckpt else ckpt

    # The training notebook builds this model with aux_loss=True (a
    # training-only auxiliary head that injects extra gradient signal from
    # an earlier backbone layer), so the checkpoint's state dict contains
    # aux_classifier.* weights. run_landcover_inference() below only ever
    # reads model(tensor)["out"], never ["aux"] -- the aux head has zero
    # effect on the landcover mask. Rather than reconstructing an unused
    # aux head just to satisfy load_state_dict, drop those keys from the
    # checkpoint before loading: this discards training-only weights, not
    # anything that affects inference output.
    state_dict = {k: v for k, v in state_dict.items() if not k.startswith("aux_classifier.")}

    # Build the model with the FINAL head shape before loading anything,
    # so load_state_dict's key/shape check is meaningful. No aux head is
    # built here since it's unused at inference (see above).
    model = deeplabv3_mobilenet_v3_large(weights=None, aux_loss=False)
    model.classifier[-1] = nn.Conv2d(256, NUM_CLASSES, kernel_size=1)

    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    # We used strict=False only to get the missing/unexpected lists for a
    # clear error message -- now we actually enforce correctness: the ONLY
    # acceptable "missing" key is the classifier head param we just replaced
    # above (its shape wouldn't have matched a differently-sized checkpoint
    # head). Anything else missing or unexpected means the checkpoint
    # doesn't really match this architecture. (aux_classifier keys were
    # already stripped from both sides above, so they can't appear here.)
    allowed_missing_prefixes = ("classifier.4.",)
    real_missing = [k for k in missing if not k.startswith(allowed_missing_prefixes)]
    if real_missing or unexpected:
        raise LandcoverLoadError(
            f"Checkpoint at {checkpoint_path} does not match the expected "
            f"DeepLabV3-MobileNetV3-Large({NUM_CLASSES}-class) architecture.\n"
            f"  Unexpected keys ({len(unexpected)}): {unexpected[:10]}\n"
            f"  Missing keys beyond the expected head ({len(real_missing)}): {real_missing[:10]}\n"
            f"Loading this checkpoint anyway would leave part of the model "
            f"randomly initialized and produce a near-noise landcover mask, "
            f"which silently disables Stage 3's building-flattening. Fix the "
            f"checkpoint/architecture mismatch rather than loading through this."
        )

    model = model.to(device)
    model.eval()

    # Sanity-check on a real-ish input: a genuinely trained model should be
    # confident (not near-uniform 1/7 probability everywhere) and should
    # predict more than one class across a real image. This does not prove
    # correctness but it does catch "loaded a randomly-initialized model
    # without erroring" (uniform logits) or "collapsed to one class"
    # (e.g. always predicting 'unlabeled').
    test_input = torch.rand(1, 3, MODEL_INPUT_SIZE, MODEL_INPUT_SIZE).to(device)
    with torch.no_grad():
        output = model(test_input)["out"]
        probs = torch.softmax(output, dim=1)
        max_conf = probs.max(dim=1).values.mean().item()
        n_classes_predicted = len(torch.unique(output.argmax(dim=1)))

    print(
        f"[landcover_model] Loaded OK. Sanity check on random noise input -- "
        f"mean top-class confidence: {max_conf:.3f}, distinct classes predicted: "
        f"{n_classes_predicted}/{NUM_CLASSES}. (On pure noise a healthy model "
        f"is usually NOT near-uniform confidence ~{1/NUM_CLASSES:.2f}; if it is, "
        f"double check the checkpoint.)"
    )
    if abs(max_conf - 1.0 / NUM_CLASSES) < 0.02:
        print(
            "[landcover_model] WARNING: confidence is suspiciously close to "
            "uniform random on noise input -- verify this checkpoint is "
            "actually trained, not a fresh/randomly-initialized save."
        )

    return model


def run_landcover_inference(normalized_image: np.ndarray, model) -> np.ndarray:
    """
    normalized_image: the SAME array stage1_depth.normalize_gsd() produces
    (512x512x3, uint8-range RGB) -- pass it in post-GSD-normalization so the
    mask lines up pixel-for-pixel with the depth output and srtm_reference,
    with no separate resize/crop step to get wrong.

    Returns an (H, W) int64 array of class IDs matching
    config.LANDCOVER_CLASS_IDS (0=unlabeled .. 6=tree).
    """
    import torch

    if normalized_image.shape[0] != MODEL_INPUT_SIZE or normalized_image.shape[1] != MODEL_INPUT_SIZE:
        raise ValueError(
            f"run_landcover_inference expects a {MODEL_INPUT_SIZE}x{MODEL_INPUT_SIZE} "
            f"GSD-normalized image (same as Stage 1's input), got {normalized_image.shape[:2]}. "
            f"Call stage1_depth.normalize_gsd() first."
        )

    device = next(model.parameters()).device
    rgb = normalized_image.astype(np.float32) / 255.0
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)["out"]
        mask = logits.argmax(1).squeeze(0).cpu().numpy().astype(np.int64)

    return mask
