# serializer.py

import struct
import numpy as np
import torch


HEADER_SIZE = 16


def serialize_tensor(tensor):

    arr = tensor.detach().cpu().numpy().astype(np.float32)

    shape = arr.shape

    header = struct.pack("IIII", *shape)

    return header + arr.tobytes()


def deserialize_tensor(data):

    shape = struct.unpack("IIII", data[:HEADER_SIZE])

    payload = data[HEADER_SIZE:]

    expected = shape[0]*shape[1]*shape[2]*shape[3]*4

    if len(payload) != expected:
        raise RuntimeError(
            f"Tensor size mismatch: got {len(payload)} expected {expected}"
        )

    arr = np.frombuffer(payload, dtype=np.float32)

    arr = arr.reshape(shape)

    return torch.tensor(arr)