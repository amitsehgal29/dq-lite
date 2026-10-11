import unittest

from dq_lite import run, validate_rules


def rows(*vals, col="c"):
    return [{col: v} for v in vals]


def one(rule, data):
    return run(data, [rule])["results"][0]


class CheckTests(unittest.TestCase):
    def test_not_null_counts_blank_and_whitespace(self):
        r = one({"column": "c", "check": "not_null"}, rows("a", "", "  ", None))
        self.assertEqual(r["failed_rows"], 3)
        self.assertEqual(r["examples"][0], {"line": 3, "reason": "empty"})

    def test_unique_points_to_first_line_and_ignores_blanks(self):
        r = one({"column": "c", "check": "unique"}, rows("a", "b", "a", "", "", "a"))
        self.assertEqual(r["failed_rows"], 2)
        self.assertEqual([e["reason"] for e in r["examples"]], ["duplicate of line 2"] * 2)

    def test_in_set(self):
        r = one({"column": "c", "check": "in_set", "values": ["x", "y"]}, rows("x", "z", ""))
        self.assertEqual(r["failed_rows"], 1)

    def test_range_inclusive_and_non_numeric(self):
        r = one({"column": "c", "check": "range", "min": 0, "max": 10}, rows("0", "10", "11", "-1", "abc"))
        self.assertEqual(r["failed_rows"], 3)
        self.assertIn("not a number", r["examples"][2]["reason"])

    def test_regex_full_match(self):
        r = one({"column": "c", "check": "regex", "pattern": "[A-Z]{2}"}, rows("AE", "AEX", "ae"))
        self.assertEqual(r["failed_rows"], 2)

    def test_max_length(self):
        r = one({"column": "c", "check": "max_length", "max": 3}, rows("abc", "abcd"))
        self.assertEqual(r["failed_rows"], 1)


class RunTests(unittest.TestCase):
    def test_warn_rules_do_not_fail_run(self):
        rep = run(rows(""), [{"column": "c", "check": "not_null", "severity": "warn"}])
        self.assertTrue(rep["ok"])
        self.assertEqual((rep["errors"], rep["warnings"]), (0, 1))

    def test_error_rule_fails_run(self):
        rep = run(rows(""), [{"column": "c", "check": "not_null"}])
        self.assertFalse(rep["ok"])

    def test_examples_are_capped(self):
        rep = run(rows(*[""] * 20), [{"column": "c", "check": "not_null"}], max_examples=5)
        self.assertEqual(rep["results"][0]["failed_rows"], 20)
        self.assertEqual(len(rep["results"][0]["examples"]), 5)


class ValidateTests(unittest.TestCase):
    def test_reports_bad_rules(self):
        problems = validate_rules([
            {"column": "nope", "check": "not_null"},
            {"column": "c", "check": "bogus"},
            {"column": "c", "check": "in_set"},
            {"column": "c", "check": "range"},
            {"column": "c", "check": "regex", "pattern": "("},
            {"column": "c", "check": "not_null", "severity": "loud"},
        ], ["c"])
        self.assertEqual(len(problems), 6)

    def test_valid_rules_pass(self):
        self.assertEqual(validate_rules([{"column": "c", "check": "range", "max": 5}], ["c"]), [])


if __name__ == "__main__":
    unittest.main()
