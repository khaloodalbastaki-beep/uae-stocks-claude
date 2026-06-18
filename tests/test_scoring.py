"""Deterministic-scoring tests. stdlib unittest (no pytest dep, keeps the toolchain light).
Run:  python3 -m unittest discover -s tests -v
"""
import unittest

from brain.scoring import Fundamentals, growth_score, stability_score, dividend_score, score_all


class TestScoring(unittest.TestCase):
    def test_ranges_and_grades(self):
        f = Fundamentals()
        out = score_all(f, "holding")
        for pillar in ("growth", "stability", "dividend"):
            self.assertGreaterEqual(out[pillar]["score"], 0)
            self.assertLessEqual(out[pillar]["score"], 100)
        self.assertIn(out["headline_grade"][0], "ABCD")

    def test_growth_monotonic(self):
        lo = Fundamentals(revenue_growth=-0.02, profit_growth=-0.05, revenue_cagr_3y=0.0, catalysts=0)
        hi = Fundamentals(revenue_growth=0.22, profit_growth=0.28, revenue_cagr_3y=0.18, catalysts=4, margin_trend=0.03)
        self.assertGreater(growth_score(hi).score, growth_score(lo).score)

    def test_stability_leverage_penalised(self):
        safe = Fundamentals(net_debt_to_ebitda=0.6, price_volatility=0.15, ocf_consistency=0.9)
        risky = Fundamentals(net_debt_to_ebitda=4.5, price_volatility=0.5, ocf_consistency=0.5)
        self.assertGreater(stability_score(safe).score, stability_score(risky).score)

    def test_dividend_yield_trap_decay(self):
        """A suspiciously high yield should NOT beat a healthy moderate one (no 'high
        yield = good'). Holding coverage/payout constant, 18% yield must not outscore 5%."""
        healthy = Fundamentals(dividend_yield=0.05, payout_ratio=0.5, fcf_coverage=1.5,
                               net_debt_pressure=0.2, cut_history=0, frequency="quarterly")
        trap = Fundamentals(dividend_yield=0.18, payout_ratio=0.5, fcf_coverage=1.5,
                            net_debt_pressure=0.2, cut_history=0, frequency="quarterly")
        self.assertGreaterEqual(dividend_score(healthy).score, dividend_score(trap).score)

    def test_cut_history_penalised(self):
        clean = Fundamentals(dividend_yield=0.05, cut_history=0, frequency="annual", fcf_coverage=1.4)
        cutter = Fundamentals(dividend_yield=0.05, cut_history=3, frequency="annual", fcf_coverage=1.4)
        self.assertGreater(dividend_score(clean).score, dividend_score(cutter).score)

    def test_archetype_changes_weighting(self):
        """Bank leverage is structural -> a leveraged bank shouldn't be punished on
        stability the way a leveraged developer is."""
        f = Fundamentals(net_debt_to_ebitda=4.0, ocf_consistency=0.9, governance_cadence=0.9,
                         price_volatility=0.2, macro_sensitivity=0.4)
        bank = stability_score(f, "bank").score
        dev = stability_score(f, "developer").score
        self.assertGreater(bank, dev)

    def test_subfactors_present_and_weighted(self):
        out = score_all(Fundamentals(), "bank")
        subs = out["growth"]["subfactors"]
        self.assertTrue(subs)
        for s in subs:
            self.assertIn("contribution", s)
            self.assertIn("note", s)


class TestPipelineShape(unittest.TestCase):
    def test_registry_and_pipeline_smoke(self):
        from brain.registry import load_universe
        from brain.adapters.mock import MockProvider
        uni = load_universe()
        self.assertGreaterEqual(len(uni), 30)
        mp = MockProvider()
        q = mp.get_quote(uni[0].symbol)
        self.assertIsNotNone(q)
        self.assertEqual(q.prov.data_quality, "demo")  # honesty: demo is tagged
        # determinism: same symbol -> same demo price
        self.assertEqual(mp.get_quote(uni[0].symbol).price, q.price)


if __name__ == "__main__":
    unittest.main()
