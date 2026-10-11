# dq-lite

A tiny, standard-library-only data-quality checker. You describe the rules for a CSV in a small JSON file, and dq-lite tells you which rows break them. It works like a pocket version of dbt tests or Great Expectations, for a quick gate before a load.

## Checks

| check | rule fields | fails when |
|---|---|---|
| `not_null` | none | the value is empty or only spaces |
| `unique` | none | the value already appeared on an earlier line |
| `in_set` | `values` | the value is not in the list |
| `range` | `min` and/or `max` | the value is not a number or is outside the inclusive bounds |
| `regex` | `pattern` | the value does not fully match |
| `max_length` | `max` | the value is longer than `max` |

Empty values are skipped by every check except `not_null`, so pair `not_null` with another check when a field is required. Each rule can set `"severity": "warn"` to report a problem without failing the run. The default severity is `error`.

## Usage

```bash
python3 dq_lite.py samples/customers.csv samples/rules.json --failures-only
```

With the sample rules, the report flags a duplicate `customer_id` on line 5, an email with no domain suffix on line 4, and ages of -3 and 130 as errors. It also flags a missing email and an unknown segment `vip` as warnings. The run exits 1 because errors were found. Each failing rule lists up to 5 example lines with a plain reason, such as `"duplicate of line 2"` or `"130 > max 120"`.

Bad rules, such as an unknown column, a check name that doesn't exist, or a regex that won't compile, are reported up front with exit code 2 before any data is checked.

## Tests

```bash
python3 -m unittest
```
