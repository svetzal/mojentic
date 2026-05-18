"""
Audio codec helpers for the realtime subsystem.

Realtime sends and receives audio as base64-encoded PCM16 (little-endian
16-bit signed mono, 24 kHz by default). These helpers convert between
the wire format and :class:`numpy.ndarray` arrays of dtype ``int16`` so
consumer code never touches base64.
"""
from __future__ import annotations

import base64
from typing import Union

import numpy as np


def decode_base64_pcm16(b64: str) -> np.ndarray:
    """
    Decode a base64 string into a :class:`numpy.ndarray` of PCM samples.

    Parameters
    ----------
    b64
        Base64-encoded little-endian 16-bit signed PCM bytes.

    Returns
    -------
    numpy.ndarray
        Array of dtype ``int16`` containing the decoded samples.
    """
    raw = base64.b64decode(b64)
    return np.frombuffer(raw, dtype="<i2").copy()


def encode_base64_pcm16(frame: Union[np.ndarray, bytes, bytearray]) -> str:
    """
    Encode PCM samples to a base64 string for the wire.

    Parameters
    ----------
    frame
        Either a :class:`numpy.ndarray` (any int dtype, coerced to int16
        little-endian) or raw bytes already in PCM16 wire format.

    Returns
    -------
    str
        Base64-encoded payload suitable for ``input_audio_buffer.append``.
    """
    if isinstance(frame, np.ndarray):
        samples = np.ascontiguousarray(frame, dtype="<i2")
        return base64.b64encode(samples.tobytes()).decode("ascii")
    return base64.b64encode(bytes(frame)).decode("ascii")
