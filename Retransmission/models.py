# models.py
# Purpose:
#   Load the neural network
#   Ensure the architecture is easy to split
#   Provide metadata (number of blocks)
# For the project, we use MobileNetV2, since it is lightweight and structured as sequential feature blocks.

import torch
import torchvision.models as models


def load_model(device="cpu"):
    """
    Load MobileNetV2 model for inference.
    """

    model = models.mobilenet_v2(weights="IMAGENET1K_V1")

    model.eval()
    model.to(device)

    return model


def get_feature_blocks(model):
    """
    Returns the list of feature blocks used for splitting.
    """

    return list(model.features)


def get_num_splits(model):
    """
    Number of valid split points in the network.
    """

    return len(list(model.features))


def get_input_tensor(device="cpu"):
    """
    Generate dummy input tensor for testing.
    """

    return torch.randn(1, 3, 224, 224).to(device)