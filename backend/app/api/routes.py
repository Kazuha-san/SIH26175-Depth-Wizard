"""
API routes. This is the ONLY file the frontend talks to.
Each endpoint should call into app/pipeline/ and return plain JSON /
base64-encoded images -- keep routing logic thin, no pipeline logic here.
"""
from fastapi import APIRouter, UploadFile, File

router = APIRouter()


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    Accepts PNG/JPG/GeoTIFF. Detects georeferenced vs non-georeferenced.
    TODO: save file, return input_type + metadata (CRS, bounds, GSD if geo).
    """
    raise NotImplementedError


@router.post("/process/{image_id}")
async def run_pipeline(image_id: str):
    """
    Runs Stage 1 -> Stage 2 -> (prep for Stage 3) on the uploaded image.
    TODO: call pipeline.stage1_depth, pipeline.stage2_calibration
    Returns: height map, confidence map, calibration stats, DSM metadata.
    """
    raise NotImplementedError


@router.get("/result/{image_id}")
async def get_result(image_id: str):
    """
    TODO: return cached pipeline output for an already-processed image.
    """
    raise NotImplementedError
