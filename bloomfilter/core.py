"""Deterministic Bloom filter, local format.

Local format policy:
- m bits, m is int (type(m) is int), m >= 1
- k hashes, k is int (type(k) is int), 1 <= k <= 65535
- items: type(item) is bytes only
- storage: ceil(m/8) bytes, bit p -> byte p//8, mask 1 << (p%8)
- unused high bits in final byte must be zero
- hash positions: digest = sha256(b"\x00" + hi.to_bytes(2,"big") + len(item).to_bytes(4,"big") + item)
  position = int.from_bytes(digest[:8],"big") % m, hi=0..k-1
- duplicate positions permitted, not replaced
"""

import hashlib
import math


class BloomFilterError(ValueError):
    pass

class InvalidBitCount(BloomFilterError):
    pass

class InvalidHashCount(BloomFilterError):
    pass

class InvalidItem(BloomFilterError):
    pass

class InvalidInsertedCount(BloomFilterError):
    pass

class InvalidState(BloomFilterError):
    pass


def _validate_bit_count(m):
    if type(m) is not int:
        raise InvalidBitCount("bit_count must be int, not bool/subclass")
    if m < 1:
        raise InvalidBitCount("bit_count must be >= 1")

def _validate_hash_count(k):
    if type(k) is not int:
        raise InvalidHashCount("hash_count must be int, not bool/subclass")
    if k < 1 or k > 65535:
        raise InvalidHashCount("hash_count must be in 1..65535")

def _validate_item(item):
    if type(item) is not bytes:
        raise InvalidItem("item must be bytes")

def _storage_bytes(m):
    return (m + 7) // 8


class BloomFilter:
    """Local deterministic Bloom filter."""

    # Validation order per operation (documented):
    # __init__(bit_count, hash_count):
    #   1. validate bit_count type and range
    #   2. validate hash_count type and range
    #   3. allocate zeroed storage
    #
    # positions(item), add(item), might_contain(item):
    #   1. validate item type is bytes
    #   2. compute positions
    #
    # expected_false_positive_rate(inserted_count):
    #   1. validate inserted_count type is int
    #   2. validate inserted_count >= 0
    #   3. compute rate
    #
    # from_bytes(bit_count, hash_count, payload):
    #   1. validate bit_count
    #   2. validate hash_count
    #   3. validate payload type is bytes
    #   4. validate payload length == ceil(bit_count/8)
    #   5. validate unused high bits are zero
    #   6. copy payload into new filter

    def __init__(self, bit_count: int, hash_count: int):
        _validate_bit_count(bit_count)
        _validate_hash_count(hash_count)
        self._m = bit_count
        self._k = hash_count
        self._buf = bytearray(_storage_bytes(bit_count))

    def bit_count(self) -> int:
        return self._m

    def hash_count(self) -> int:
        return self._k

    def positions(self, item: bytes) -> tuple[int, ...]:
        _validate_item(item)
        m = self._m
        item_len = len(item).to_bytes(4, "big")
        out = []
        for hi in range(self._k):
            h_input = b"\x00" + hi.to_bytes(2, "big") + item_len + item
            digest = hashlib.sha256(h_input).digest()
            pos = int.from_bytes(digest[:8], "big") % m
            out.append(pos)
        return tuple(out)

    def add(self, item: bytes) -> None:
        for p in self.positions(item):
            self._buf[p // 8] |= 1 << (p % 8)

    def might_contain(self, item: bytes) -> bool:
        for p in self.positions(item):
            if not (self._buf[p // 8] & (1 << (p % 8))):
                return False
        return True

    def set_bit_count(self) -> int:
        n = 0
        for b in self._buf:
            n += bin(b).count("1")
        return n

    def to_bytes(self) -> bytes:
        return bytes(self._buf)

    @classmethod
    def from_bytes(cls, bit_count: int, hash_count: int, payload: bytes):
        _validate_bit_count(bit_count)
        _validate_hash_count(hash_count)
        if type(payload) is not bytes:
            raise InvalidState("payload must be bytes")
        expected_len = _storage_bytes(bit_count)
        if len(payload) != expected_len:
            raise InvalidState("payload wrong length")
        # unused high bits must be zero
        unused = expected_len * 8 - bit_count
        if unused:
            last = payload[-1]
            mask = ((1 << unused) - 1) << (8 - unused)
            if last & mask:
                raise InvalidState("unused high bits nonzero")
        bf = cls(bit_count, hash_count)
        bf._buf[:] = payload
        return bf

    def expected_false_positive_rate(self, inserted_count: int) -> float:
        if type(inserted_count) is not int:
            raise InvalidInsertedCount("inserted_count must be int")
        if inserted_count < 0:
            raise InvalidInsertedCount("inserted_count must be >= 0")
        n = inserted_count
        m = self._m
        k = self._k
        # (1 - exp(-k*n/m)) ** k
        return (1.0 - math.exp(-k * n / m)) ** k

    def occupancy_false_positive_estimate(self) -> float:
        set_bits = self.set_bit_count()
        return (set_bits / self._m) ** self._k
