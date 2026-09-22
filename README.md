# DepthWizard -- SIH 2026, PS 26175 (ISRO)

Single-view RGB -> DSM + navigable 3D flythrough. Local/offline build,
no deployment.

## Structure

- `backend/` -- Python. ML pipeline (depth backbone, calibration) + FastAPI
  local server. See `backend/app/pipeline/` for the 3-stage pipeline logic.
- `frontend/` -- JavaScript. React + Three.js visualization UI. See
  `frontend/src/components/viewport/` for the 3D rendering.

## Running locally

### First time after cloning

1. **Get the model checkpoints.** They're too large for GitHub
   (`landcover_seg_v6.pth` is 127MB, over GitHub's 100MB hard limit) so
   they're git-ignored, not in the repo. Get `depth_anything_v2_gamus_v4.pth`
   and `landcover_seg_v6.pth` from **[TODO: add your shared Drive/storage
   link here]** and place both in `backend/checkpoints/`.
2. Make sure you have **Python 3.10+** and **Node.js** installed.
3. Run the launcher for your OS (see below) -- it handles the Python venv,
   dependencies, and frontend build automatically on first run.

### Launching the app (one click, after first-time setup above)

- **Windows:** double-click `run_windows.bat`

A terminal window stays open behind the app -- that's normal, it's
showing backend logs. Close the app window, or Ctrl+C in the terminal, to
stop everything. First launch takes longer (creates a Python venv, builds
the frontend); after that it starts in a few seconds.

### Manual / dev mode

If you'd rather run things by hand, or you're actively developing:

As a desktop app (one native window, no browser):
```
cd frontend
npm install
npm run build        # one-time, or after any frontend change

cd ../backend
pip install -r requirements.txt
python desktop_app.py
```

As two dev servers (for hot-reload frontend development):

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

Frontend dev server runs at `http://localhost:5173` and talks to the
backend at `http://localhost:8000`.

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
