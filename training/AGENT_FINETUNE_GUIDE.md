# Fine-tuning Loop -- Agent Guide

You (an AI agent -- Claude Code, Claude in a chat, whatever the teammate is
running) are helping a teammate iterate on `segmentation_finetune.ipynb`,
which fine-tunes DepthWizard's land-cover segmentation model. The human
runs cells in Colab; you don't have execution access there. Your job is to
read what they show you, diagnose it, and edit the notebook file for the
next run.

## The loop

1. **Human runs the notebook in Colab** (all cells, top to bottom, first
   time; just Sections 2 onward on later runs once the dataset cache
   exists).
2. **Human pastes/screenshots you the output** of:
   - Section 7's per-epoch IoU tables (the full training log, not just the
     last epoch -- trajectory matters, not just the final number)
   - Section 8's RGB / ground-truth / prediction grid image
   - Section 9's loss/IoU curve image
   - Section 6's config cell as it currently stands (so you know what
     produced these results)
3. **You diagnose and edit the notebook file directly** (str_replace on the
   relevant cell's source in the `.ipynb`, or hand back the specific lines
   to paste in) -- see "What to look for" below.
4. **Human re-runs from Section 7 down** (no need to redo Sections 3-4,
   the dataset cache persists for the rest of that Colab session) with a
   **new `RUN_NAME`** and reports back. Repeat.

Don't just ask "what should I change" back to the human -- your job is to
read the actual numbers/images they give you and propose a specific,
justified edit. If the images genuinely aren't legible or the metrics are
ambiguous, ask ONE targeted question, not a generic "how did it go."

## What to look for

**Per-class IoU table, across epochs:**
- A class stuck near 0 while others climb -> almost always a class-weight
  or data-imbalance problem, not a learning-rate problem. Check `water` and
  `building` first, they're usually GAMUS's rarest classes.
- All classes plateau early and flat -> learning rate too low, or backbone
  frozen too long (`FREEZE_BACKBONE_EPOCHS`).
- Val IoU jumping around a lot epoch to epoch, never settling -> learning
  rate too high, or batch size too small for how noisy that class's
  gradient is.
- Train loss still dropping but val IoU has stalled/dropped -> overfitting;
  more augmentation, or fewer epochs, or more training samples.

**The RGB / GT / prediction grid:**
- This is the ONLY place you'll see error PATTERNS the IoU number hides.
  Look specifically for:
  - Building predictions bleeding into road/ground at edges -> the model
    doesn't have crisp boundary signal; more augmentation variety, or more
    training samples with buildings near roads.
  - Small buildings/structures missed entirely while large ones are fine
    -> classic class-imbalance-by-pixel-count issue, even if the building
    class's raw IoU looks okay overall (large correct blobs can mask
    consistently-missed small ones). Worth flagging even if not asked.
  - Tree canopy edges vs. tree interior -- Stage 3's tree-instance
    placement (backend `stage3_mesh_prep.py`) depends on clean tree-blob
    boundaries, so blobby/eroded tree edges here will show up later as
    badly-placed tree instances in the actual 3D output.
  - Water misclassified as shadow/dark-road patches, or vice versa -- both
    read as "dark" to the model; if this shows up, it's a genuinely hard
    case worth just naming as a known limitation rather than chasing
    indefinitely.

**The loss/IoU curve image:**
- Loss curve with a sudden spike -> usually one bad batch (corrupted
  cache sample) or LR too high right after backbone unfreezing. Check
  `FREEZE_BACKBONE_EPOCHS` timing against where the spike happens.

## Editing the notebook

The notebook cells map directly to the config/hyperparameters named in
Section 2's config cell (`LEARNING_RATE`, `USE_CLASS_WEIGHTS`,
`FREEZE_BACKBONE_EPOCHS`, `AUGMENT`, etc.) and the loss/metric code in
Sections 6-7. Most changes you'll make are:
- Editing values in the Section 2 config cell
- Editing `GAMUSSegDataset`'s `__getitem__` augmentation block (Section 3)
  to add/strengthen a specific augmentation
- Editing the `criterion` in Section 7 (e.g. swapping in a Dice-loss term
  alongside cross-entropy if small/rare classes stay weak)

**Change ONE thing per run.** If you change three hyperparameters at once
and IoU improves, nobody knows which change actually mattered -- and if two
of those changes fought each other, you could be discarding a genuinely
good change because it got paired with a bad one.

**Always require a new `RUN_NAME`** before the next run, so checkpoints
never silently overwrite each other, and so you can compare this run's
numbers against the specific prior run they came from rather than "some
earlier attempt."

## When it's actually done

A run is a real candidate for replacing `landcover_seg_v6.pth` when:
- Mean IoU across classes beats the current checkpoint's recorded
  `best_iou` (shown when `RESUME_FROM_CHECKPOINT` is set and loaded)
- No single class collapsed to near-0 to get there (check the full table,
  not just the mean -- a higher mean hiding one abandoned class is a
  regression, not an improvement)
- The visual grid doesn't show new obviously-wrong patterns that weren't
  there before, even if the numbers look fine

At that point: report the final checkpoint's IoU table + a couple of visual
grids back, and DO NOT rename the file to `landcover_seg_v6.pth` yourselves
-- that swap happens deliberately once compared against the other
teammate's run, not automatically inside this loop.

