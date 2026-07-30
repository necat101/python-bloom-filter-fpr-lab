# VERIFY.md — python-bloom-filter-fpr-lab

## Implementation revision

- Repository: https://github.com/necat101/python-bloom-filter-fpr-lab
- Default branch: main
- Implementation SHA: `3fff4f6e504e27a724947569e827072cbf0859d3`

## Clean-clone verification

Commands run in a fresh clone, detached at implementation SHA:

```
git clone https://github.com/necat101/python-bloom-filter-fpr-lab.git bf-verify
git checkout --detach 3fff4f6e504e27a724947569e827072cbf0859d3
git rev-parse HEAD
# -> 3fff4f6e504e27a724947569e827072cbf0859d3
python3 --version
# -> Python 3.12.3
python3 -m py_compile bloomfilter/*.py bloomfilter/tests/*.py
# exit 0
python3 -m bloomfilter.runner
# exit 0
python3 -m unittest bloomfilter.tests.test_independent -v
# exit 0, 22 tests OK
python3 -m bloomfilter.runner   # regenerate
# exit 0
git diff --exit-code -- results.json results.csv RESULTS.md
# exit 0 — all three artifacts byte-identical
git status --short
# (clean)
```

Wall time: ~0.37 s (Python 3.12.3, runner + unittest)

## Results summary

- Correctness cases: 35
- Experiments: 3
- Classifications: success 17, invalid_bit_count 4, invalid_hash_count 5, invalid_item 3, invalid_inserted_count 0, invalid_state 3, present_match 1, absent_match 1, false_positive 1, false_negative 0
- Independent unittests: 22 tests, 0 failures, 0 skips

Experiments:

| id | m | k | inserted | fp | fp_rate | predicted_fpr | occupancy_fpr | fn |
|---|---|---|---|---|---|---|---|---|
| compact | 64 | 3 | 20 | 37 | 0.289062500000 | 0.225193352609 | 0.262912750244 | 0 |
| balanced | 256 | 4 | 40 | 12 | 0.046875000000 | 0.046648198329 | 0.056843418861 | 0 |
| spacious | 1024 | 7 | 80 | 1 | 0.001953125000 | 0.002353634346 | 0.002228469460 | 0 |

All inserted items reported present (zero false negatives). Artifact byte comparisons passed for results.json, results.csv, and RESULTS.md. Working tree clean.

This verification tested implementation revision `3fff4f6e504e27a724947569e827072cbf0859d3`. This documentation commit was not itself clean-clone tested.
