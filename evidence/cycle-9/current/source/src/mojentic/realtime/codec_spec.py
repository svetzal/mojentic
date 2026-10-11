import base64

import numpy as np

from mojentic.realtime.codec import decode_base64_pcm16, encode_base64_pcm16


class DescribePcm16Codec:
    class DescribeRoundTrip:
        def should_round_trip_numpy_int16_array(self):
            original = np.array([0, 1, -1, 32767, -32768, 12345], dtype=np.int16)

            encoded = encode_base64_pcm16(original)
            decoded = decode_base64_pcm16(encoded)

            assert decoded.dtype == np.int16
            assert np.array_equal(decoded, original)

        def should_round_trip_bytes_input(self):
            samples = np.array([10, -10, 20, -20], dtype=np.int16)
            raw_bytes = samples.tobytes()

            encoded = encode_base64_pcm16(raw_bytes)
            decoded = decode_base64_pcm16(encoded)

            assert np.array_equal(decoded, samples)

    class DescribeDecode:
        def should_produce_writable_array(self):
            samples = np.array([1, 2, 3], dtype=np.int16)
            encoded = base64.b64encode(samples.tobytes()).decode("ascii")

            decoded = decode_base64_pcm16(encoded)
            decoded[0] = 99

            assert decoded[0] == 99
