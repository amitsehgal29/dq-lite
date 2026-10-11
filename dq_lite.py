#!/usr/bin/env python3
"""dq-lite: declarative data-quality checks for a CSV, from a small JSON rules file.

Standard library only. Each rule names a column and a check. Supported checks:

  not_null   value is present (not empty after trimming)
  unique     no value repeats (empty values are ignored)
  in_set     value is one of "values"
  range      numeric value within "min" and/or "max" (inclusive)
  regex      value fully matches "pattern"
  max_length value length is at most "max"

Empty values are skipped by every check except not_null, so combine not_null
with another rule when a field is required. Prints a JSON report and exits 1
when any rule with severity "error" (the default) fails; "warn" rules are
reported but never fail the run.
"""
import argparse
import csv
import json
import re
import sys

CHECKS = ("not_null", "unique", "in_set", "range", "regex", "max_length")


def validate_rules(rules, columns):
    problems = []
    for i, r in enumerate(rules):
        where = f"rule {i + 1}"
        if r.get("check") not in CHECKS:
            problems.append(f"{where}: unknown check {r.get('check')!r}")
        if r.get("column") not in columns:
            problems.append(f"{where}: column {r.get('column')!r} not in CSV")
        if r.get("check") == "in_set" and not isinstance(r.get("values"), list):
            problems.append(f"{where}: in_set needs a 'values' list")
        if r.get("check") == "range" and "min" not in r and "max" not in r:
            problems.append(f"{where}: range needs 'min' and/or 'max'")
        if r.get("check") == "regex":
            try:
                re.compile(r.get("pattern", ""))
            except re.error as e:
                problems.append(f"{where}: bad regex ({e})")
        if r.get("check") == "max_length" and not isinstance(r.get("max"), int):
            problems.append(f"{where}: max_length needs an integer 'max'")
        if r.get("severity", "error") not in ("error", "warn"):
            problems.append(f"{where}: severity must be 'error' or 'warn'")
    return problems


def _fails(rule, value, state):
    """Return a short reason if `value` breaks `rule`, else None."""
    check = rule["check"]
    v = (value or "").strip()
    if check == "not_null":
        return "empty" if not v else None
    if not v:
        return None
    if check == "unique":
        if v in state:
            return f"duplicate of line {state[v]}"
        return None
    if check == "in_set":
        allowed = [str(x) for x in rule["values"]]
        return None if v in allowed else f"{v!r} not in {allowed}"
    if check == "range":
        try:
            n = float(v)
        except ValueError:
            return f"{v!r} is not a number"
        if "min" in rule and n < rule["min"]:
            return f"{v} < min {rule['min']}"
        if "max" in rule and n > rule["max"]:
            return f"{v} > max {rule['max']}"
        return None
    if check == "regex":
        return None if re.fullmatch(rule["pattern"], v) else f"{v!r} does not match"
    if check == "max_length":
        return None if len(v) <= rule["max"] else f"length {len(v)} > {rule['max']}"
    return None


def run(rows, rules, max_examples=5):
    results = []
    for rule in rules:
        state, failures, count = {}, [], 0
        for line, row in enumerate(rows, start=2):  # line 1 is the header
            value = row.get(rule["column"])
            reason = _fails(rule, value, state)
            if rule["check"] == "unique":
                v = (value or "").strip()
                if v and v not in state:
                    state[v] = line
            if reason:
                count += 1
                if len(failures) < max_examples:
                    failures.append({"line": line, "reason": reason})
        results.append({
            "column": rule["column"],
            "check": rule["check"],
            "severity": rule.get("severity", "error"),
            "failed_rows": count,
            "passed": count == 0,
            "examples": failures,
        })
    errors = sum(1 for r in results if not r["passed"] and r["severity"] == "error")
    warnings = sum(1 for r in results if not r["passed"] and r["severity"] == "warn")
    return {"rows": len(rows), "rules": len(rules), "errors": errors, "warnings": warnings,
            "ok": errors == 0, "results": results}


def main(argv=None):
    p = argparse.ArgumentParser(description="Run JSON-defined data-quality rules against a CSV.")
    p.add_argument("csv", help="CSV file to check")
    p.add_argument("rules", help="JSON file with a list of rules")
    p.add_argument("--failures-only", action="store_true", help="only list rules that failed")
    args = p.parse_args(argv)

    with open(args.rules, encoding="utf-8") as f:
        rules = json.load(f)
    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        rows = list(reader)

    problems = validate_rules(rules, columns)
    if problems:
        print(json.dumps({"error": "invalid rules", "problems": problems}, indent=2), file=sys.stderr)
        return 2

    report = run(rows, rules)
    if args.failures_only:
        report["results"] = [r for r in report["results"] if not r["passed"]]
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
