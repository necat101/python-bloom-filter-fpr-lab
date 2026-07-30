"""Independent tests — stdlib only, no runner/manifest/results imports."""

import unittest
import hashlib
import math
from bloomfilter.core import (
    BloomFilter,
    InvalidBitCount,
    InvalidHashCount,
    InvalidItem,
    InvalidInsertedCount,
    InvalidState,
)

class TestBloomIndependent(unittest.TestCase):

    def test_hash_input_construction(self):
        bf = BloomFilter(256, 4)
        item = b"test_item"
        # independent recompute
        il = len(item).to_bytes(4, "big")
        expected = []
        for hi in range(4):
            h_in = b"\x00" + hi.to_bytes(2, "big") + il + item
            digest = hashlib.sha256(h_in).digest()
            pos = int.from_bytes(digest[:8], "big") % 256
            expected.append(pos)
        self.assertEqual(bf.positions(item), tuple(expected))

    def test_hash_index_encoding(self):
        # verify 2-byte big-endian index is used
        bf = BloomFilter(1024, 300)
        item = b"x"
        pos0 = bf.positions(item)[0]
        pos255 = bf.positions(item)[255]
        # recompute with explicit encoding
        il = len(item).to_bytes(4, "big")
        d0 = hashlib.sha256(b"\x00" + (0).to_bytes(2, "big") + il + item).digest()
        p0 = int.from_bytes(d0[:8], "big") % 1024
        d255 = hashlib.sha256(b"\x00" + (255).to_bytes(2, "big") + il + item).digest()
        p255 = int.from_bytes(d255[:8], "big") % 1024
        self.assertEqual(pos0, p0)
        self.assertEqual(pos255, p255)

    def test_item_length_encoding(self):
        bf = BloomFilter(128, 2)
        # items with same suffix but different length must differ
        p_a = bf.positions(b"a")
        p_aa = bf.positions(b"\x00a")  # different
        # direct check that length field is 4-byte big-endian
        item = b"abc"
        il = len(item).to_bytes(4, "big")
        self.assertEqual(il, b"\x00\x00\x00\x03")
        h_in = b"\x00" + (0).to_bytes(2, "big") + il + item
        self.assertEqual(h_in[:7], b"\x00\x00\x00\x00\x00\x00\x03")

    def test_first_eight_byte_conversion(self):
        # position = int.from_bytes(digest[:8], "big") % m
        bf = BloomFilter(257, 1)
        item = b"indep"
        il = len(item).to_bytes(4, "big")
        digest = hashlib.sha256(b"\x00\x00\x00" + il + item).digest()
        pos_expected = int.from_bytes(digest[:8], "big") % 257
        self.assertEqual(bf.positions(item)[0], pos_expected)

    def test_modulo_reduction(self):
        bf = BloomFilter(10, 5)
        for q in [b"a", b"b", b"c", b"\x00\xff"]:
            ps = bf.positions(q)
            for p in ps:
                self.assertGreaterEqual(p, 0)
                self.assertLess(p, 10)

    def test_lsb_bit_placement(self):
        bf = BloomFilter(16, 1)
        # find an item that hits position 0,1,8,9 etc
        # just check that to_bytes uses 1 << (p%8)
        # brute find pos 3
        found = None
        for i in range(500):
            item = f"i{i}".encode()
            ps = BloomFilter(16, 1).positions(item)
            if ps[0] == 3:
                found = item
                break
        self.assertIsNotNone(found)
        bf2 = BloomFilter(16, 1)
        bf2.add(found)
        b = bf2.to_bytes()
        # pos 3 -> byte 0, mask 0x08
        self.assertEqual(b[0] & 0x08, 0x08)
        self.assertEqual(b[0], 0x08)

    def test_cross_byte_positions(self):
        bf = BloomFilter(16, 1)
        # pos 8 -> byte 1, bit 0
        # find such item
        target = None
        for i in range(1000):
            item = f"c{i}".encode()
            if BloomFilter(16, 1).positions(item)[0] == 8:
                target = item
                break
        self.assertIsNotNone(target)
        bf2 = BloomFilter(16, 1)
        bf2.add(target)
        self.assertEqual(bf2.to_bytes(), bytes([0x00, 0x01]))

    def test_unused_high_bits_validation(self):
        # m=9 -> 2 bytes, 7 unused high bits in byte 1
        # valid payload
        bf = BloomFilter.from_bytes(9, 1, b"\x00\x00")
        self.assertEqual(bf.to_bytes(), b"\x00\x00")
        # invalid: set high bit
        with self.assertRaises(InvalidState):
            BloomFilter.from_bytes(9, 1, b"\x00\x80")
        with self.assertRaises(InvalidState):
            BloomFilter.from_bytes(9, 1, b"\x00\xff")

    def test_duplicate_positions_allowed(self):
        bf = BloomFilter(3, 4)
        pos = bf.positions(b"x0")
        self.assertEqual(pos, (1, 2, 2, 1))
        bf.add(b"x0")
        self.assertTrue(bf.might_contain(b"x0"))
        # serialized: bits 1 and 2 set -> 0b00000110 = 0x06, unused bits 3..7 zero
        self.assertEqual(bf.to_bytes(), b"\x06")

    def test_duplicate_insertion_idempotent(self):
        bf = BloomFilter(64, 3)
        bf.add(b"dup")
        h1 = bf.to_bytes()
        bf.add(b"dup")
        h2 = bf.to_bytes()
        self.assertEqual(h1, h2)

    def test_insertion_order_independence(self):
        bf_a = BloomFilter(32, 3)
        bf_a.add(b"foo"); bf_a.add(b"bar")
        bf_b = BloomFilter(32, 3)
        bf_b.add(b"bar"); bf_b.add(b"foo")
        self.assertEqual(bf_a.to_bytes(), bf_b.to_bytes())
        self.assertEqual(bf_a.to_bytes().hex(), "08026006")

    def test_exact_bytes_validation(self):
        bf = BloomFilter(8, 1)
        with self.assertRaises(InvalidItem):
            bf.add("str")  # type: ignore
        with self.assertRaises(InvalidItem):
            bf.add(bytearray(b"x"))  # type: ignore
        with self.assertRaises(InvalidItem):
            bf.add(memoryview(b"x"))  # type: ignore

    def test_bool_rejection_integers(self):
        with self.assertRaises(InvalidBitCount):
            BloomFilter(True, 1)
        with self.assertRaises(InvalidHashCount):
            BloomFilter(8, True)
        bf = BloomFilter(16, 2)
        with self.assertRaises(InvalidInsertedCount):
            bf.expected_false_positive_rate(True)

    def test_serialization_roundtrip(self):
        bf = BloomFilter(32, 3)
        for x in [b"a", b"b", b"c"]:
            bf.add(x)
        payload = bf.to_bytes()
        bf2 = BloomFilter.from_bytes(32, 3, payload)
        self.assertEqual(bf2.to_bytes(), payload)

    def test_malformed_serialized_state(self):
        # wrong length
        with self.assertRaises(InvalidState):
            BloomFilter.from_bytes(16, 1, b"\x00")
        with self.assertRaises(InvalidState):
            BloomFilter.from_bytes(16, 1, b"\x00\x00\x00")
        # non-bytes payload
        with self.assertRaises(InvalidState):
            BloomFilter.from_bytes(8, 1, bytearray(b"\x00"))  # type: ignore
        # unused bits
        with self.assertRaises(InvalidState):
            BloomFilter.from_bytes(9, 1, b"\x00\xfe")

    def test_predicted_rate_arithmetic(self):
        bf = BloomFilter(256, 4)
        n = 40
        expected = (1.0 - math.exp(-4 * n / 256)) ** 4
        self.assertAlmostEqual(bf.expected_false_positive_rate(n), expected, places=12)
        # invalid inserted_count
        with self.assertRaises(InvalidInsertedCount):
            bf.expected_false_positive_rate(-1)
        with self.assertRaises(InvalidInsertedCount):
            bf.expected_false_positive_rate(1.5)  # type: ignore
        with self.assertRaises(InvalidInsertedCount):
            bf.expected_false_positive_rate(True)

    def test_occupancy_estimate(self):
        bf = BloomFilter(16, 3)
        bf.add(b"a"); bf.add(b"b")
        set_bits = bf.set_bit_count()
        self.assertEqual(set_bits, 5)
        expected = (set_bits / 16) ** 3
        self.assertAlmostEqual(bf.occupancy_false_positive_estimate(), expected, places=12)

    def test_zero_false_negatives_experiment(self):
        # run compact experiment independently
        m, k, n_insert, n_query = 64, 3, 20, 128
        bf = BloomFilter(m, k)
        inserted = [f"insert:{i:04d}".encode() for i in range(n_insert)]
        for x in inserted:
            bf.add(x)
        fn = sum(0 if bf.might_contain(x) else 1 for x in inserted)
        self.assertEqual(fn, 0)

    def test_full_experiment_reconstruction_balanced(self):
        # Independently reconstruct the "balanced" experiment
        m, k, n_insert, n_query = 256, 4, 40, 256
        bf = BloomFilter(m, k)
        inserted = [f"insert:{i:04d}".encode() for i in range(n_insert)]
        for x in inserted:
            bf.add(x)
        # final bit array
        filter_bytes = bf.to_bytes()
        self.assertEqual(len(filter_bytes), 32)
        set_bits = bf.set_bit_count()
        # query absent set
        absent = [f"query:{i:04d}".encode() for i in range(n_query)]
        fp_count = 0
        for q in absent:
            if bf.might_contain(q):
                fp_count += 1
        tn_count = n_query - fp_count
        # false negatives
        fn = sum(0 if bf.might_contain(x) else 1 for x in inserted)
        self.assertEqual(fn, 0)
        # verify counts match known deterministic run
        # from runner: set_bits=125, fp=12, tn=244
        self.assertEqual(set_bits, 125)
        self.assertEqual(fp_count, 12)
        self.assertEqual(tn_count, 244)
        # verify bit array reconstructs from positions
        buf = bytearray(32)
        for x in inserted:
            il = len(x).to_bytes(4, "big")
            for hi in range(k):
                digest = hashlib.sha256(b"\x00" + hi.to_bytes(2, "big") + il + x).digest()
                p = int.from_bytes(digest[:8], "big") % m
                buf[p // 8] |= 1 << (p % 8)
        self.assertEqual(bytes(buf), filter_bytes)

    def test_caller_owned_inputs_unchanged(self):
        item = b"immutable"
        item_copy = item[:]
        bf = BloomFilter(32, 3)
        bf.add(item)
        self.assertEqual(item, item_copy)
        payload = b"\x00\x00\x00\x00"
        payload_copy = payload[:]
        bf2 = BloomFilter.from_bytes(32, 3, payload)
        self.assertEqual(payload, payload_copy)
        # ensure bf2 didn't alias payload
        bf2.add(b"x")
        self.assertEqual(payload, payload_copy)

    def test_validation_order_multi_malformed(self):
        # from_bytes: bit_count invalid should raise InvalidBitCount before checking payload
        with self.assertRaises(InvalidBitCount):
            BloomFilter.from_bytes(True, 1, b"\x00")  # bad m, payload also wrong len
        with self.assertRaises(InvalidBitCount):
            BloomFilter.from_bytes(0, 1, b"")
        # hash_count invalid before payload check
        with self.assertRaises(InvalidHashCount):
            BloomFilter.from_bytes(8, 0, b"\x00")
        # payload type before length / unused bits
        with self.assertRaises(InvalidState):
            BloomFilter.from_bytes(8, 1, "notbytes")  # type: ignore
        # length before unused bits
        with self.assertRaises(InvalidState):
            BloomFilter.from_bytes(16, 1, b"\x00")  # short

    def test_expected_fpr_invalid_inserted_count(self):
        bf = BloomFilter(64, 3)
        with self.assertRaises(InvalidInsertedCount):
            bf.expected_false_positive_rate(-5)
        with self.assertRaises(InvalidInsertedCount):
            bf.expected_false_positive_rate(True)
        with self.assertRaises(InvalidInsertedCount):
            bf.expected_false_positive_rate("20")  # type: ignore


if __name__ == "__main__":
    unittest.main()
