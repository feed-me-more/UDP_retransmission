# splitter.py

import torch.nn as nn


class SplitModel:

    def __init__(self, model, split_idx):

        features = list(model.features)

        self.edge = nn.Sequential(*features[:split_idx])

        self.server = nn.Sequential(
            *features[split_idx:],
            nn.AdaptiveAvgPool2d((1,1)),
            nn.Flatten(),
            model.classifier
        )

    def edge_forward(self, x):

        return self.edge(x)

    def server_forward(self, x):

        return self.server(x)