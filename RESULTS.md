# Results

Correctness cases: 35

Classification totals:

- success: 17
- invalid_bit_count: 4
- invalid_hash_count: 5
- invalid_item: 3
- invalid_inserted_count: 0
- invalid_state: 3
- present_match: 1
- absent_match: 1
- false_positive: 1
- false_negative: 0

## Experiments

| id | m | k | inserted | queries | set_bits | occupancy | predicted_fpr | occupancy_fpr | fp | fp_rate | tn | fn | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| compact | 64 | 3 | 20 | 128 | 41 | 0.640625000000 | 0.225193352609 | 0.262912750244 | 37 | 0.289062500000 | 91 | 0 | True |
| balanced | 256 | 4 | 40 | 256 | 125 | 0.488281250000 | 0.046648198329 | 0.056843418861 | 12 | 0.046875000000 | 244 | 0 | True |
| spacious | 1024 | 7 | 80 | 512 | 428 | 0.417968750000 | 0.002353634346 | 0.002228469460 | 1 | 0.001953125000 | 511 | 0 | True |

