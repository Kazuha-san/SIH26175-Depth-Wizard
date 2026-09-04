"""
Fine-tuning entrypoint for the depth backbone on GAMUS.
Run standalone (not part of the FastAPI app) -- this produces the
checkpoint that app/pipeline/stage1_depth.py loads at inference time.

Usage: python training/train.py --config training/config.yaml
"""


def main():
    """TODO: training loop -- load GAMUS via app.data.gamus_loader,
    fine-tune DepthBackbone (freeze most encoder layers), scale-invariant
    loss, save checkpoint to backend/checkpoints/.
    """
    raise NotImplementedError


if __name__ == "__main__":
    main()
