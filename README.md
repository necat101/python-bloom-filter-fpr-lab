# python-bloom-filter-fpr-lab

Deterministic correctness and false-positive-rate lab for one explicitly defined Bloom filter format, using only the Python standard library.

## Wikipedia background

Bloom filters are space-efficient probabilistic data structures for set membership testing with no false negatives and a controllable false-positive rate.

Reference: https://en.wikipedia.org/wiki/Bloom_filter

Wikipedia is background only. It is **not** the normative specification for this lab's hashing, bit numbering, serialization, validation, or experiment corpus.

## Official Python documentation

- hashlib: https://docs.python.org/3/library/hashlib.html
- math: https://docs.python.org/3/library/math.html

## Explicit local format and hashing policies

- Filter size `m` bits, `m` is `type(m) is int`, `m >= 1`
- Hash count `k`, `type(k) is int`, `1 <= k <= 65535`
- Items: `type(item) is bytes` only; reject `str`, `bytearray`, `memoryview`
- Empty byte string is valid
- Storage: exactly `ceil(m/8)` bytes
- Bit `p` → byte `p // 8`, mask `1 << (p % 8)` (LSB-first)
- Unused high bits in final byte must remain zero
- Duplicate insertions idempotent, order-independent
- No deletion
- `might_contain` returns `True` / `False` only; the filter does not distinguish members from false positives
- Hash positions: `digest = sha256(b"\x00" + hash_index.to_bytes(2,"big") + len(item).to_bytes(4,"big") + item).digest()`, `position = int.from_bytes(digest[:8],"big") % m`, `hash_index = 0..k-1`
- Duplicate positions permitted, not replaced; this is a deterministic lab policy, not a claim of statistical independence
- False-positive probability estimate: `(1 - math.exp(-k*n/m)) ** k`
- Occupancy estimate: `(set_bits / m) ** k`
- Both rates labeled approximations

## Public API

```
BloomFilter(bit_count: int, hash_count: int)
positions(item: bytes) -> tuple[int, ...]
add(item: bytes) -> None
might_contain(item: bytes) -> bool
set_bit_count() -> int
to_bytes() -> bytes
BloomFilter.from_bytes(bit_count, hash_count, payload) -> BloomFilter
expected_false_positive_rate(inserted_count: int) -> float
occupancy_false_positive_estimate() -> float
```

Exceptions: `InvalidBitCount`, `InvalidHashCount`, `InvalidItem`, `InvalidInsertedCount`, `InvalidState`.

## Local observations

Correctness cases: 35, 0 failures.

Classification totals: success 17, invalid_bit_count 4, invalid_hash_count 5, invalid_item 3, invalid_inserted_count 0, invalid_state 3, present_match 1, absent_match 1, false_positive 1, false_negative 0.

Experiments:

| id | m | k | inserted | fp | fp_rate | predicted | occupancy | fn |
|---|---|---|---|---|---|---|---|---|
| compact | 64 | 3 | 20 | 37 | 0.289062500000 | 0.225193352609 | 0.262912750244 | 0 |
| balanced | 256 | 4 | 40 | 12 | 0.046875000000 | 0.046648198329 | 0.056843418861 | 0 |
| spacious | 1024 | 7 | 80 | 1 | 0.001953125000 | 0.002353634346 | 0.002228469460 | 0 |

All inserted items reported present (zero false negatives). Observed false-positive rates differ from the approximate formulas, as expected for a single deterministic corpus.

See `RESULTS.md`, `results.json`, `results.csv` for full evidence.

## Disclaimers

- A positive Bloom-filter lookup does **not** prove membership.
- The SHA-256 derivation is a local deterministic construction for this lab.
- The lab does not prove real-world hash independence.
- One deterministic corpus does not establish a universal false-positive rate.
- This lab is not a production storage, security, authentication, or authorization system.
