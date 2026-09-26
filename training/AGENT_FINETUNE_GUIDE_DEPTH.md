# Depth Model Fine-tuning Loop -- Agent Guide

You (an AI agent -- Claude Code, Claude in a chat, whatever the teammate
is running) are helping a teammate iterate on `depth_finetune.ipynb`,
which fine-tunes the Depth Anything V2 backbone used by
`backend/app/pipeline/stage1_depth.py`. The human runs cells in Colab;
you don't have execution access there. Your job is to read what they
show you, diagnose it, and edit the notebook file for the next run.

This is the same loop as `AGENT_FINETUNE_GUIDE.md` (the segmentation
notebook's guide) but for a REGRESSION model, not classification -- the
failure patterns and what to look at are different. Read this one, not
that one, when working on this notebook.

## Read the notebook's own history note first

Cell 0 of `depth_finetune.ipynb` documents exactly what v1->v4 each
changed and why, and explicitly flags that v5's attempt (a 4th loss term
for building-roof shape) regressed MAE across every class and was
abandoned. **Do not let a run reintroduce that regression** by adding a
shape/edge-sharpening loss term beyond what `multi_scale_gradient_loss`
already does -- if the human or an early idea points that direction,
redirect to Stage 3 (`stage3_mesh_prep.flatten_planar_classes`) instead,
which is where that concern actually got resolved for the shipped
checkpoint (v4) without hurting accuracy.

## The loop

1. **Human runs the notebook in Colab**, uploading the current
   `depth_anything_v2_gamus_v4.pth` first if `RESUME_FROM_CHECKPOINT` is
   set to it (recommended default -- see "Resuming vs. from scratch"
   below).
2. **Human pastes/screenshots you the output** of:
   - Section 6's per-epoch train/val loss log (the full log, not just
     the last epoch -- the train-val GAP trajectory matters as much as
     either number alone)
   - Section 6's loss curve image
   - Section 7's per-class MAE table (zero-shot vs. baseline
     resumed-from vs. this run -- all three, not just this run's numbers)
   - Section 8's RGB / zero-shot / this-run / ground-truth image
   - Section 2's config cell as it currently stands
3. **You diagnose and edit the notebook file directly** -- see "What to
   look for" below.
4. **Human re-runs from Section 4 down** (Sections 1-3 -- setup and
   dataset download -- don't need to be redone in the same Colab
   session, `hf_hub_download` caches locally) with a **new `RUN_NAME`**
   and reports back. Repeat.

Don't just ask "what should I change" back to the human -- read the
actual numbers/images and propose a specific, justified edit. Ask ONE
targeted question only if something is genuinely ambiguous or illegible.

## What to look for

**Per-class MAE table (Section 7) -- this is the primary signal:**
- Compare THIS RUN against the BASELINE (resumed-from checkpoint), not
  just against zero-shot -- zero-shot will always look terrible, that's
  not the comparison that matters. A run that beats zero-shot but loses
  to its own baseline is a regression, not progress.
- Building and tree are the two classes this whole notebook lineage
  exists to improve (see the v1->v4 history) -- weigh their MAE more
  than ground/road/low-vegetation, which are already easy and roughly
  flat across versions.
- One class's MAE improving a lot while another gets meaningfully worse
  is usually `HARD_CLASS_WEIGHT` (or a future split building/tree
  weight) pulling capacity from one class to the other, not a genuine
  net improvement -- flag this explicitly even if the human doesn't ask.
- Watch for water: it's often the rarest class in a given tile subset,
  so its MAE can be noisy/unreliable across small eval sets -- a big
  swing there with few tiles behind it deserves lower confidence than
  the same swing in building/tree, which the dataset selection biases
  toward (Section 3).

**Loss curves (Section 6):**
- Growing train-val gap over epochs -- overfitting; earlier stopping
  (lower `PATIENCE`), fewer unfrozen blocks
  (`LAST_N_BLOCKS_TO_UNFREEZE`), or more training tiles.
- Val loss plateaus immediately and never really drops -- learning rate
  too low, or too few blocks unfrozen to actually adapt.
- Loss spikes mid-training -- usually a bad batch or LR too high;
  unlikely to need architecture changes, try `LEARNING_RATE` first.

**Visual comparison (Section 8) -- what the numbers hide:**
- This run visually "smoother"/blurrier than the baseline despite
  similar or better MAE -- likely `GRAD_LOSS_WEIGHT` too low relative to
  the scale-invariant term; the pointwise number can look fine while
  edges/boundaries get worse, which matters for Stage 3's plane-fitting
  since it depends on the depth model's own signal to detect a ridge/
  edge at all (see `stage3_mesh_prep.flatten_planar_classes`'s gable-
  split logic, which explicitly documents this dependency).
- Prediction confidently wrong in a specific SHAPE (e.g. domed
  buildings, blobby tree canopies) rather than just noisy -- this is
  shape, not accuracy; resist the urge to chase it with a new loss term
  here (see the v5 warning above) and instead note it as a Stage 3
  candidate.
- Zero-shot and this-run predictions look nearly identical -- too few
  blocks unfrozen, or LR too low to move the model meaningfully from
  its resumed starting point.

## Resuming vs. training from scratch

Default (`RESUME_FROM_CHECKPOINT` set to v4) is almost always the right
choice -- v4 already represents 4 rounds of validated improvement over
zero-shot. Training from scratch (`RESUME_FROM_CHECKPOINT = None`) is
only worth trying if you specifically want to test a different base
recipe (e.g. a very different `LAST_N_BLOCKS_TO_UNFREEZE` or loss
weighting) in isolation, without v4's accumulated fine-tuning
potentially masking the effect -- and even then, compare it against v4
head-to-head in the same per-class table, don't evaluate it alone.

## When it's actually done

A run is a real candidate for replacing `depth_anything_v2_gamus_v4.pth`
when:
- Per-class MAE beats the baseline (v4) on building AND tree specifically
  (the two classes this lineage targets), not just on the overall
  average -- an overall-average improvement that's actually a
  ground/road improvement masking a building/tree regression is not a
  real win for this project's stated goals.
- No class regressed by more than noise (re-run Section 7 once more on
  the same checkpoint if a number looks surprising -- eval uses a fixed
  30-tile sample, not the full val set, so some run-to-run noise is
  expected).
- The visual grid doesn't show a new failure pattern that wasn't there
  in the baseline.

At that point: report the full per-class table (zero-shot / baseline /
this run, all three) + the visual grid back, and do NOT rename the file
to `depth_anything_v2_gamus_v4.pth` yourselves -- that swap happens
deliberately once compared against any other parallel attempt, not
automatically inside this loop.

