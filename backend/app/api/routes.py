"""
API routes. This is the ONLY file the frontend talks to.
Each endpoint calls into app/pipeline/ and returns plain JSON /
base64-encoded images -- routing logic here stays thin (validation,
file I/O, wiring), all real pipeline logic lives in app/pipeline/.

STATE: results are kept in a simple in-memory dict (_JOBS), not a
database. This matches the project's "no deployment, runs locally for
the judge showcase" decision -- a single-process demo doesn't need
persistence across restarts. If this ever needs to survive a server
restart, swap _JOBS for a lightweight on-disk cache (e.g. one JSON +
npy file per image_id under a results/ dir) -- the dict's read/write
call sites below wouldn't need to change, only what backs them.

MODEL LOADING: the depth model is loaded ONCE at import time (module
load), not per-request -- reloading a ViT checkpoint on every /process
call would make each request take as long as a cold start, and this
API only ever serves one model version at a time anyway.
"""
import os
import shutil
import uuid

import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException

from app import config
from app.pipeline import stage1_depth, stage2_calibration, stage3_mesh_prep
from app.utils import geotiff_utils, image_utils

router = APIRouter()

UPLOAD_DIR = "/tmp/depthwizard_uploads"
MESH_EXPORT_DIR = "/tmp/depthwizard_meshes"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MESH_EXPORT_DIR, exist_ok=True)

_JOBS = {}  # image_id -> {"status", "input_type", "metadata", "result", "error"}

_model = None


def _get_model():
    """Lazy-loads the fine-tuned depth model once, reused across requests."""
    global _model
    if _model is None:
        _model = stage1_depth.load_depth_model(config.DEPTH_MODEL_CHECKPOINT)
    return _model


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    Accepts PNG/JPG/GeoTIFF. Saves it, detects georeferenced vs
    non-georeferenced, and returns an image_id plus whatever metadata
    is immediately knowable (CRS/bounds/GSD for GeoTIFF; nothing extra
    for plain PNG/JPG). Does NOT run the pipeline yet -- that's /process's job,
    kept separate so the upload+metadata step is fast and the frontend
    can show the input-type badge before committing to the slower run.
    """
    image_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    save_path = os.path.join(UPLOAD_DIR, f"{image_id}{ext}")

    with open(save_path, "wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    is_geo = geotiff_utils.is_georeferenced(save_path)
    metadata = {}
    if is_geo:
        try:
            metadata = geotiff_utils.read_geotiff_metadata(save_path)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to read GeoTIFF metadata: {exc}")

    _JOBS[image_id] = {
        "status": "uploaded",
        "file_path": save_path,
        "input_type": "georeferenced" if is_geo else "non_georeferenced",
        "metadata": metadata,
        "result": None,
        "error": None,
    }

    return {
        "image_id": image_id,
        "input_type": _JOBS[image_id]["input_type"],
        "metadata": metadata,
    }


@router.post("/process/{image_id}")
async def run_pipeline(image_id: str, with_uncertainty: bool = True):
    """
    Runs Stage 1 (depth) -> Stage 2 (calibration) -> Stage 3 (shape
    cleanup + mesh packaging) on a previously uploaded image.

    Georeferenced path requires a real SRTM fetch (srtm_utils.fetch_srtm_for_bounds),
    which needs network access this pipeline doesn't assume is configured --
    if that raises NotImplementedError/an error, we fall back to the
    non-georeferenced (relative DSM) path and note that in the response
    rather than failing the whole request, since a relative DSM + mesh is
    still a usable result for the demo.
    """
    job = _JOBS.get(image_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown image_id: {image_id}")

    try:
        job["status"] = "processing"
        rgb_image = image_utils.load_image(job["file_path"])
        model = _get_model()

        srtm_used = False
        if job["input_type"] == "georeferenced":
            try:
                from app.data import srtm_utils

                bounds = job["metadata"]["bounds_wgs84"]
                srtm_raw_path = os.path.join(UPLOAD_DIR, f"{image_id}_srtm.tif")
                srtm_utils.fetch_srtm_for_bounds(bounds, out_path=srtm_raw_path)

                import rasterio
                with rasterio.open(job["file_path"]) as src:
                    target_transform, target_crs = src.transform, src.crs

                srtm_reference = srtm_utils.resample_to_match(
                    srtm_raw_path, rgb_image.shape[:2], target_transform, target_crs
                )
                pipeline_out = _run_georeferenced(rgb_image, model, srtm_reference, with_uncertainty)
                srtm_used = True
            except Exception as exc:
                job["metadata"]["srtm_fallback_reason"] = str(exc)
                pipeline_out = _run_nongeoreferenced(rgb_image, model, with_uncertainty)
        else:
            pipeline_out = _run_nongeoreferenced(rgb_image, model, with_uncertainty)

        rgb_for_mesh = pipeline_out.get("normalized_image", rgb_image)
        dsm = pipeline_out.get("calibrated_dsm", pipeline_out.get("normalized_rdsm"))
        landcover_mask = pipeline_out.get("landcover_mask")  # None unless caller supplied one
        cleaned_dsm = stage3_mesh_prep.clean_dsm_for_mesh(dsm, rgb_for_mesh, landcover_mask)

        payload = stage3_mesh_prep.package_result_for_frontend(
            dsm=cleaned_dsm,
            confidence_map=pipeline_out.get("confidence_map"),
            rgb_image=rgb_for_mesh,
            metadata={
                **job["metadata"],
                "srtm_used": srtm_used,
                "calibration_method": pipeline_out.get("calibration_method", "none_relative_only"),
                "gsd_info": pipeline_out.get("gsd_info"),
            },
        )

        glb_path = os.path.join(MESH_EXPORT_DIR, f"{image_id}.glb")
        stage3_mesh_prep.export_mesh_glb(cleaned_dsm, rgb_for_mesh, glb_path)
        payload["mesh_glb_path"] = glb_path

        job["result"] = payload
        job["status"] = "done"
        job["error"] = None
        return payload

    except Exception as exc:
        job["status"] = "error"
        job["error"] = str(exc)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}")


def _run_georeferenced(rgb_image, model, srtm_reference, with_uncertainty):
    from app.pipeline import pipeline as pipeline_module
    return pipeline_module.run_stage1_to_stage2_georeferenced(
        rgb_image, model, srtm_reference, with_uncertainty=with_uncertainty
    )


def _run_nongeoreferenced(rgb_image, model, with_uncertainty):
    from app.pipeline import pipeline as pipeline_module
    return pipeline_module.run_stage1_only_nongeoreferenced(
        rgb_image, model, with_uncertainty=with_uncertainty
    )


@router.get("/result/{image_id}")
async def get_result(image_id: str):
    """Returns the cached pipeline output for an already-processed image."""
    job = _JOBS.get(image_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown image_id: {image_id}")
    if job["status"] == "error":
        raise HTTPException(status_code=500, detail=f"Previous processing attempt failed: {job['error']}")
    if job["status"] != "done":
        return {"status": job["status"]}
    return job["result"]
