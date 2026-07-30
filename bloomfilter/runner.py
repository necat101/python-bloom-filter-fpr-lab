"""Deterministic runner for bloom filter correctness + FPR experiments."""

import json
import csv
import math
from bloomfilter.core import (
    BloomFilter,
    InvalidBitCount,
    InvalidHashCount,
    InvalidItem,
    InvalidInsertedCount,
    InvalidState,
)
from bloomfilter.manifest import MANIFEST

RECOGNIZED_CLASSIFICATIONS = [
    "success",
    "invalid_bit_count",
    "invalid_hash_count",
    "invalid_item",
    "invalid_inserted_count",
    "invalid_state",
    "present_match",
    "absent_match",
    "false_positive",
    "false_negative",
]

def fmt_rate(x: float) -> str:
    return f"{x:.12f}"

def run_case(c):
    cid = c["id"]
    kind = c["kind"]
    expect = c["expect"]
    actual = None
    passed = False
    detail = ""

    try:
        if kind == "ctor_ok":
            bf = BloomFilter(c["m"], c["k"])
            actual = "success"
            passed = (actual == expect)

        elif kind == "ctor_fail":
            try:
                bf = BloomFilter(c["m"], c["k"])
                actual = "success"
                passed = False
                detail = "expected exception"
            except InvalidBitCount:
                actual = "invalid_bit_count"
                passed = (actual == expect)
            except InvalidHashCount:
                actual = "invalid_hash_count"
                passed = (actual == expect)

        elif kind == "positions":
            bf = BloomFilter(c["m"], c["k"])
            pos = bf.positions(c["item"])
            actual = "success" if pos == c["expected_positions"] else "mismatch"
            passed = pos == c["expected_positions"]
            detail = f"got {pos}"

        elif kind == "item_reject":
            bf = BloomFilter(c["m"], c["k"])
            bad_type = c["bad_item_type"]
            if bad_type == "str":
                bad = "notbytes"
            elif bad_type == "bytearray":
                bad = bytearray(b"x")
            elif bad_type == "memoryview":
                bad = memoryview(b"x")
            else:
                bad = None
            try:
                bf.positions(bad)  # type: ignore
                actual = "success"
                passed = False
            except InvalidItem:
                actual = "invalid_item"
                passed = (actual == expect)

        elif kind == "add_present":
            bf = BloomFilter(c["m"], c["k"])
            bf.add(c["item"])
            rc = bf.might_contain(c["item"])
            actual = "present_match" if rc else "false_negative"
            passed = rc and actual == expect

        elif kind == "absent_empty":
            bf = BloomFilter(c["m"], c["k"])
            rc = bf.might_contain(c["query"])
            actual = "absent_match" if not rc else "false_positive"
            passed = (not rc) and actual == expect

        elif kind == "duplicate_idempotent":
            bf = BloomFilter(c["m"], c["k"])
            bf.add(c["item"])
            h1 = bf.to_bytes()
            bf.add(c["item"])
            h2 = bf.to_bytes()
            actual = "success" if h1 == h2 else "mismatch"
            passed = h1 == h2
            detail = f"{h1.hex()} vs {h2.hex()}"

        elif kind == "order_independent":
            bf_a = BloomFilter(c["m"], c["k"])
            for x in c["items_a"]:
                bf_a.add(x)
            ha = bf_a.to_bytes().hex()
            bf_b = BloomFilter(c["m"], c["k"])
            for x in c["items_b"]:
                bf_b.add(x)
            hb = bf_b.to_bytes().hex()
            exp_hex = c.get("expected_hex")
            ok = (ha == hb)
            if exp_hex:
                ok = ok and (ha == exp_hex)
            actual = "success" if ok else "mismatch"
            passed = ok
            detail = f"{ha} vs {hb}"

        elif kind == "duplicate_positions":
            bf = BloomFilter(c["m"], c["k"])
            pos = bf.positions(c["item"])
            actual = "success" if pos == c["expected_positions"] else "mismatch"
            passed = pos == c["expected_positions"]
            # also ensure add/might_contain works
            bf.add(c["item"])
            passed = passed and bf.might_contain(c["item"])
            detail = f"pos={pos}"

        elif kind == "bit_placement":
            bf = BloomFilter(c["m"], c["k"])
            bf.add(c["add_item"])
            hx = bf.to_bytes().hex()
            actual = "success" if hx == c["expected_hex"] else "mismatch"
            passed = hx == c["expected_hex"]
            detail = hx

        elif kind == "serialize_roundtrip":
            bf = BloomFilter(c["m"], c["k"])
            for x in c["items"]:
                bf.add(x)
            payload = bf.to_bytes()
            bf2 = BloomFilter.from_bytes(c["m"], c["k"], payload)
            payload2 = bf2.to_bytes()
            actual = "success" if payload == payload2 else "mismatch"
            passed = payload == payload2

        elif kind == "from_bytes_reject_len":
            payload = bytes.fromhex(c["payload_hex"])
            try:
                bf = BloomFilter.from_bytes(c["m"], c["k"], payload)
                actual = "success"
                passed = False
            except InvalidState:
                actual = "invalid_state"
                passed = (actual == expect)

        elif kind == "from_bytes_reject_unused":
            payload = bytes.fromhex(c["payload_hex"])
            try:
                bf = BloomFilter.from_bytes(c["m"], c["k"], payload)
                actual = "success"
                passed = False
            except InvalidState:
                actual = "invalid_state"
                passed = (actual == expect)

        elif kind == "caller_unchanged":
            item = c["item"]
            item_copy = item[:]
            bf = BloomFilter(c["m"], c["k"])
            bf.add(item)
            if item != item_copy:
                actual = "mismatch"
                passed = False
            else:
                # payload unchanged test
                payload = bytes.fromhex(c["payload_hex"])
                payload_copy = payload[:]
                try:
                    bf2 = BloomFilter.from_bytes(c["m"], c["k"], payload)
                except Exception:
                    bf2 = None
                if payload != payload_copy:
                    actual = "mismatch"
                    passed = False
                else:
                    actual = "success"
                    passed = True

        elif kind == "no_false_negatives":
            bf = BloomFilter(c["m"], c["k"])
            for x in c["items"]:
                bf.add(x)
            fn = 0
            for x in c["items"]:
                if not bf.might_contain(x):
                    fn += 1
            actual = "success" if fn == 0 else "false_negative"
            passed = fn == 0
            detail = f"fn={fn}"

        elif kind == "false_positive_case":
            bf = BloomFilter(c["m"], c["k"])
            for x in c["inserted"]:
                bf.add(x)
            fx = bf.to_bytes().hex()
            if fx != c["expected_filter_hex"]:
                actual = "mismatch"
                passed = False
                detail = f"filter {fx} != {c['expected_filter_hex']}"
            else:
                pos = bf.positions(c["query"])
                if pos != c["expected_positions"]:
                    actual = "mismatch"
                    passed = False
                    detail = f"pos {pos}"
                else:
                    rc = bf.might_contain(c["query"])
                    # query must NOT be in inserted list
                    is_member = c["query"] in c["inserted"]
                    if rc and not is_member:
                        actual = "false_positive"
                        passed = (actual == expect)
                    elif rc and is_member:
                        actual = "present_match"
                        passed = False
                    elif not rc:
                        actual = "absent_match"
                        passed = False
                    else:
                        actual = "mismatch"
                        passed = False

        else:
            actual = "invalid_state"
            passed = False
            detail = f"unknown kind {kind}"

    except Exception as e:
        actual = f"exception:{type(e).__name__}"
        passed = False
        detail = str(e)

    return {
        "id": cid,
        "type": "correctness",
        "classification": actual if actual in RECOGNIZED_CLASSIFICATIONS else "invalid_state",
        "expected": expect,
        "actual": actual,
        "pass": passed,
        "detail": detail,
    }


def run_experiment(exp_id, m, k, n_insert, n_query):
    bf = BloomFilter(m, k)
    inserted = [f"insert:{i:04d}".encode() for i in range(n_insert)]
    for x in inserted:
        bf.add(x)
    # false negatives check
    fn = sum(0 if bf.might_contain(x) else 1 for x in inserted)
    # absent queries
    absent = [f"query:{i:04d}".encode() for i in range(n_query)]
    fp = 0
    for q in absent:
        if bf.might_contain(q):
            fp += 1
    tn = n_query - fp
    set_bits = bf.set_bit_count()
    occupancy = set_bits / m
    predicted = bf.expected_false_positive_rate(n_insert)
    occupancy_fpr = bf.occupancy_false_positive_estimate()
    filter_hex = bf.to_bytes().hex()
    passed = (fn == 0 and fp + tn == n_query)
    return {
        "id": exp_id,
        "type": "experiment",
        "m": m,
        "k": k,
        "inserted_count": n_insert,
        "absent_query_count": n_query,
        "set_bit_count": set_bits,
        "occupancy_ratio": fmt_rate(occupancy),
        "predicted_fpr": fmt_rate(predicted),
        "occupancy_fpr": fmt_rate(occupancy_fpr),
        "false_positive_count": fp,
        "false_positive_rate": fmt_rate(fp / n_query if n_query else 0),
        "true_negative_count": tn,
        "false_negative_count": fn,
        "filter_hex": filter_hex,
        "pass": passed,
    }


def main():
    # run correctness cases
    case_rows = []
    seen_ids = set()
    for c in MANIFEST:
        if c["id"] in seen_ids:
            raise SystemExit(f"duplicate case id {c['id']}")
        seen_ids.add(c["id"])
        row = run_case(c)
        case_rows.append(row)

    # run experiments
    experiments = [
        ("compact", 64, 3, 20, 128),
        ("balanced", 256, 4, 40, 256),
        ("spacious", 1024, 7, 80, 512),
    ]
    exp_rows = []
    for exp in experiments:
        erow = run_experiment(*exp)
        if erow["id"] in seen_ids:
            raise SystemExit("duplicate experiment id")
        seen_ids.add(erow["id"])
        exp_rows.append(erow)

    # classification totals
    totals = {cls: 0 for cls in RECOGNIZED_CLASSIFICATIONS}
    for r in case_rows:
        cls = r["classification"]
        if cls in totals:
            totals[cls] += 1
    # validate totals sum
    if sum(totals.values()) != len(case_rows):
        raise SystemExit("classification totals mismatch")

    # Validate experiment invariants
    for er in exp_rows:
        if er["false_positive_count"] + er["true_negative_count"] != er["absent_query_count"]:
            raise SystemExit(f"{er['id']} fp+tn != query_count")
        if er["false_negative_count"] != 0:
            raise SystemExit(f"{er['id']} false_negative != 0")

    # Validate case pass
    failed_cases = [r for r in case_rows if not r["pass"]]
    failed_exps = [r for r in exp_rows if not r["pass"]]

    # Build results.json
    results = {
        "cases": [
            {
                "id": r["id"],
                "type": r["type"],
                "classification": r["classification"],
                "expected": r["expected"],
                "actual": r["actual"],
                "pass": r["pass"],
            } for r in case_rows
        ],
        "experiments": exp_rows,
        "totals": totals,
    }
    with open("results.json", "w", newline="\n", encoding="utf-8") as f:
        json.dump(results, f, sort_keys=True, separators=(",", ":"))
        f.write("\n")

    # results.csv
    # union columns
    csv_fields = [
        "row_type", "id", "classification", "expected", "actual", "pass",
        "m", "k", "inserted_count", "absent_query_count",
        "set_bit_count", "occupancy_ratio", "predicted_fpr", "occupancy_fpr",
        "false_positive_count", "false_positive_rate",
        "true_negative_count", "false_negative_count", "filter_hex",
    ]
    with open("results.csv", "w", newline="\n", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in case_rows:
            w.writerow({
                "row_type": "correctness",
                "id": r["id"],
                "classification": r["classification"],
                "expected": r["expected"],
                "actual": r["actual"],
                "pass": str(r["pass"]).lower(),
            })
        for er in exp_rows:
            w.writerow({
                "row_type": "experiment",
                "id": er["id"],
                "classification": "",
                "expected": "",
                "actual": "",
                "pass": str(er["pass"]).lower(),
                "m": er["m"],
                "k": er["k"],
                "inserted_count": er["inserted_count"],
                "absent_query_count": er["absent_query_count"],
                "set_bit_count": er["set_bit_count"],
                "occupancy_ratio": er["occupancy_ratio"],
                "predicted_fpr": er["predicted_fpr"],
                "occupancy_fpr": er["occupancy_fpr"],
                "false_positive_count": er["false_positive_count"],
                "false_positive_rate": er["false_positive_rate"],
                "true_negative_count": er["true_negative_count"],
                "false_negative_count": er["false_negative_count"],
                "filter_hex": er["filter_hex"],
            })

    # RESULTS.md
    with open("RESULTS.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("# Results\n\n")
        f.write(f"Correctness cases: {len(case_rows)}\n\n")
        f.write("Classification totals:\n\n")
        for cls in RECOGNIZED_CLASSIFICATIONS:
            f.write(f"- {cls}: {totals.get(cls,0)}\n")
        f.write("\n## Experiments\n\n")
        f.write("| id | m | k | inserted | queries | set_bits | occupancy | predicted_fpr | occupancy_fpr | fp | fp_rate | tn | fn | pass |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for er in exp_rows:
            f.write(f"| {er['id']} | {er['m']} | {er['k']} | {er['inserted_count']} | {er['absent_query_count']} | {er['set_bit_count']} | {er['occupancy_ratio']} | {er['predicted_fpr']} | {er['occupancy_fpr']} | {er['false_positive_count']} | {er['false_positive_rate']} | {er['true_negative_count']} | {er['false_negative_count']} | {er['pass']} |\n")
        f.write("\n")

    # terminal totals
    print(f"Cases: {len(case_rows)}, failed: {len(failed_cases)}")
    print(f"Experiments: {len(exp_rows)}, failed: {len(failed_exps)}")
    print("Totals:", totals)

    if failed_cases or failed_exps:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
