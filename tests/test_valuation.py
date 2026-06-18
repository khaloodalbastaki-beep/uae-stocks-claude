"""Tests for the deterministic fair-value engine."""
import unittest

from brain.valuation import fair_value


def _bank():
    return {
        "reported": {"shares_outstanding": 11048000000, "total_equity": 130875000000,
                     "eps": 1.48, "dividend_per_share": 0.75, "payout_ratio": 0.51},
        "series": {"years": [2021, 2022, 2023, 2024],
                   "net_income": [13e9, 14.5e9, 16e9, 17.1e9],
                   "revenue": [22e9, 25e9, 28e9, 31.6e9]},
    }


class ValuationTests(unittest.TestCase):
    def test_bank_methods_cluster_and_sane(self):
        v = fair_value(_bank(), 18.46, "bank")
        self.assertIsNotNone(v)
        self.assertGreaterEqual(len(v["methods"]), 2)
        # a ~13% ROE bank near book should land within a sane band of the price, not 3x off
        self.assertTrue(0.4 * 18.46 <= v["fair_value"] <= 2.0 * 18.46)
        self.assertIn(v["rating"], ("undervalued", "overvalued", "fairly valued"))

    def test_requires_two_methods(self):
        # only a dividend, no eps/equity/series -> single method -> no published value
        thin = {"reported": {"dividend_per_share": 0.5}}
        self.assertIsNone(fair_value(thin, 10.0, "utility"))

    def test_no_inputs_returns_none(self):
        self.assertIsNone(fair_value({"reported": {}}, 10.0, "consumer"))
        self.assertIsNone(fair_value(_bank(), None, "bank"))      # no price
        self.assertIsNone(fair_value(_bank(), 0, "bank"))         # zero price

    def test_percent_payout_normalised(self):
        # payout stored as a percent (e.g. 51) must not blow up growth/DDM
        rec = _bank(); rec["reported"]["payout_ratio"] = 51
        v = fair_value(rec, 18.46, "bank")
        self.assertIsNotNone(v)
        self.assertTrue(0.4 * 18.46 <= v["fair_value"] <= 2.0 * 18.46)

    def test_perpetual_growth_capped_below_rate(self):
        # extreme reported growth must not push terminal g near r (Gordon blow-up guard)
        rec = _bank()
        rec["series"]["net_income"] = [5e9, 10e9, 15e9, 25e9]  # ~70% CAGR
        v = fair_value(rec, 18.46, "bank")
        self.assertIsNotNone(v)
        self.assertLessEqual(v["fair_value"], 3.0 * 18.46)  # no explosion

    def test_oneoff_earnings_normalised_for_multiple(self):
        # a one-off NI spike should be haircut for the P/E method (sustainable earnings)
        rec = {
            "reported": {"shares_outstanding": 12.6e9, "total_equity": 10.5e9,
                         "eps": 0.106, "dividend_per_share": 0.045, "payout_ratio": 0.43},
            "series": {"years": [2022, 2023, 2024],
                       "net_income": [0.35e9, 0.42e9, 1.33e9], "revenue": [1.3e9, 1.63e9, 2.88e9]},
        }
        v = fair_value(rec, 0.425, "consumer")
        self.assertIsNotNone(v)
        # pe method should be well below the naive eps*PE (0.106*16≈1.7)
        self.assertLess(v["methods"]["pe"], 1.4)


if __name__ == "__main__":
    unittest.main()
