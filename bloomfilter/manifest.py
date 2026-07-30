"""Fixed correctness manifest.

Every position/serialization case contains literal expected values.
"""

MANIFEST = [
    # construction ok
    {"id": "ctor_m1", "kind": "ctor_ok", "m": 1, "k": 1, "expect": "success"},
    {"id": "ctor_m8", "kind": "ctor_ok", "m": 8, "k": 3, "expect": "success"},
    {"id": "ctor_m9", "kind": "ctor_ok", "m": 9, "k": 2, "expect": "success"},
    {"id": "ctor_normal", "kind": "ctor_ok", "m": 256, "k": 4, "expect": "success"},

    # m rejects
    {"id": "ctor_m0", "kind": "ctor_fail", "m": 0, "k": 1, "expect": "invalid_bit_count"},
    {"id": "ctor_m_neg", "kind": "ctor_fail", "m": -5, "k": 1, "expect": "invalid_bit_count"},
    {"id": "ctor_m_true", "kind": "ctor_fail", "m": True, "k": 1, "expect": "invalid_bit_count"},
    {"id": "ctor_m_str", "kind": "ctor_fail", "m": "8", "k": 1, "expect": "invalid_bit_count"},

    # k rejects
    {"id": "ctor_k0", "kind": "ctor_fail", "m": 8, "k": 0, "expect": "invalid_hash_count"},
    {"id": "ctor_k_neg", "kind": "ctor_fail", "m": 8, "k": -1, "expect": "invalid_hash_count"},
    {"id": "ctor_k_true", "kind": "ctor_fail", "m": 8, "k": True, "expect": "invalid_hash_count"},
    {"id": "ctor_k_str", "kind": "ctor_fail", "m": 8, "k": "3", "expect": "invalid_hash_count"},
    {"id": "ctor_k_big", "kind": "ctor_fail", "m": 8, "k": 65536, "expect": "invalid_hash_count"},

    # exact positions, m=256 k=4
    {"id": "pos_empty", "kind": "positions", "m": 256, "k": 4, "item": b"", "expected_positions": (234, 84, 131, 6), "expect": "success"},
    {"id": "pos_ascii", "kind": "positions", "m": 256, "k": 4, "item": b"abc", "expected_positions": (54, 198, 29, 11), "expect": "success"},
    {"id": "pos_embedded_zero", "kind": "positions", "m": 256, "k": 4, "item": b"a\x00b", "expected_positions": (158, 171, 126, 160), "expect": "success"},
    {"id": "pos_utf8", "kind": "positions", "m": 256, "k": 4, "item": b"\xc3\xbc\xc3\xb1\xc3\xae\xc3\xa7\xc3\xb8d\xc3\xa9", "expected_positions": (104, 211, 65, 121), "expect": "success"},

    # item type rejects
    {"id": "item_reject_str", "kind": "item_reject", "m": 16, "k": 3, "bad_item_type": "str", "expect": "invalid_item"},
    {"id": "item_reject_bytearray", "kind": "item_reject", "m": 16, "k": 3, "bad_item_type": "bytearray", "expect": "invalid_item"},
    {"id": "item_reject_memoryview", "kind": "item_reject", "m": 16, "k": 3, "bad_item_type": "memoryview", "expect": "invalid_item"},

    # add / present
    {"id": "add_present", "kind": "add_present", "m": 32, "k": 3, "item": b"hello", "expect": "present_match"},

    # absent in empty filter
    {"id": "absent_empty", "kind": "absent_empty", "m": 256, "k": 4, "query": b"absent_xyz", "expect": "absent_match"},

    # duplicate insertion idempotent
    {"id": "duplicate_idempotent", "kind": "duplicate_idempotent", "m": 64, "k": 3, "item": b"dup_test", "expect": "success"},

    # order independence
    {"id": "order_independent", "kind": "order_independent", "m": 32, "k": 3, "items_a": [b"foo", b"bar"], "items_b": [b"bar", b"foo"], "expected_hex": "08026006", "expect": "success"},

    # duplicate positions accepted
    {"id": "duplicate_positions", "kind": "duplicate_positions", "m": 3, "k": 4, "item": b"x0", "expected_positions": (1, 2, 2, 1), "expect": "success"},

    # one-bit filter placement
    {"id": "bit_one", "kind": "bit_placement", "m": 1, "k": 1, "add_item": b"z", "expected_hex": "01", "expect": "success"},

    # cross-byte boundary
    {"id": "bit_cross_byte", "kind": "bit_placement", "m": 16, "k": 1, "add_item": b"\x00", "expected_hex": "0080", "expect": "success"},

    # m not divisible by 8
    {"id": "m_not_div8", "kind": "ctor_ok", "m": 9, "k": 2, "expect": "success"},

    # serialization roundtrip
    {"id": "serialize_roundtrip", "kind": "serialize_roundtrip", "m": 32, "k": 3, "items": [b"a", b"b", b"c"], "expect": "success"},

    # from_bytes reject short
    {"id": "from_bytes_short", "kind": "from_bytes_reject_len", "m": 16, "k": 3, "payload_hex": "ff", "expect": "invalid_state"},

    # from_bytes reject long
    {"id": "from_bytes_long", "kind": "from_bytes_reject_len", "m": 16, "k": 3, "payload_hex": "000000", "expect": "invalid_state"},

    # from_bytes reject nonzero unused high bits (m=9 -> 2 bytes, 7 unused high bits)
    {"id": "from_bytes_unused_bits", "kind": "from_bytes_reject_unused", "m": 9, "k": 2, "payload_hex": "00fe", "expect": "invalid_state"},

    # caller-owned bytes unchanged
    {"id": "caller_unchanged", "kind": "caller_unchanged", "m": 32, "k": 3, "item": b"immutable", "payload_hex": "00000000", "expect": "success"},

    # no false negatives
    {"id": "no_false_negatives", "kind": "no_false_negatives", "m": 128, "k": 4, "items": [b"n1", b"n2", b"n3", b"n4", b"n5"], "expect": "success"},

    # false positive ground truth
    {"id": "false_positive_case", "kind": "false_positive_case", "m": 16, "k": 3, "inserted": [b"a", b"b"], "query": b"q0", "expected_positions": (15, 12, 13), "expected_filter_hex": "00b3", "expect": "false_positive"},
]
