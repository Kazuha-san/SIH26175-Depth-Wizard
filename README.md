# DepthWizard -- SIH 2026, PS 26175 (ISRO)

Single-view RGB -> DSM + navigable 3D flythrough. Local/offline build,
no deployment.

## Structure

- `backend/` -- Python. ML pipeline (depth backbone, calibration) + FastAPI
  local server. See `backend/app/pipeline/` for the 3-stage pipeline logic.
- `frontend/` -- JavaScript. React + Three.js visualization UI. See
  `frontend/src/components/viewport/` for the 3D rendering.
- `agent-prompts/` -- Instruction files (.md) for coding agents (Google
  models / Qwen3 Coder) handling repetitive/simple tasks. Anything
  system-critical still goes through manual review.
- `docs/` -- Roadmap and UI component reference for the team.

## Running locally

Backend:
```
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:
```
cd frontend
npm install
npm run dev
```

Frontend talks to backend over `http://localhost:8000`.

## Pipeline stages (see backend/app/pipeline/)

1. `stage1_depth.py` -- relative height map from fine-tuned Depth Anything V2
2. `stage2_calibration.py` -- relative -> absolute DSM, SRTM-anchored,
   **Innovation #1**: per-land-cover-class calibration instead of one
   global affine fit
3. Mesh + rendering happens client-side in `frontend/src/components/viewport/`,
   **Innovation #2**: confidence/uncertainty overlay (MC-dropout, computed
   in `stage1_depth.py::run_inference_with_uncertainty`)

Everything marked `TODO` / `raise NotImplementedError` is an unfilled stub
-- structure is locked, implementation is not.
