"""Computed odds should match the published '1 in N' figures."""
import unittest

from lottery_ev.ev import annuity_pv_factor, lotto_rollovers
from lottery_ev.games import (EUROMILLIONS, EUROMILLIONS_HOTPICKS, GAMES, LOTTO, LOTTO_HOTPICKS,
                              POWERBALL, SET_FOR_LIFE, THUNDERBALL)


def one_in(p: float) -> float:
    return 1 / p


class TestOdds(unittest.TestCase):
    def test_lotto_two_rounds(self):
        # Published odds are per ticket across both rounds.
        self.assertAlmostEqual(one_in(LOTTO.jackpot_prob * 2), 22_528_737, delta=1)
        tiers = {t.label: one_in(t.prob * 2) for t in LOTTO.tiers}
        self.assertAlmostEqual(tiers["Match 5 plus Bonus"], 3_754_790, delta=1)
        self.assertAlmostEqual(tiers["Match 5"], 72_208, delta=1)
        self.assertAlmostEqual(tiers["Match 4"], 1_090, delta=1)
        self.assertAlmostEqual(tiers["Match 3"], 48.1, delta=0.4)

    def test_powerball(self):
        self.assertAlmostEqual(one_in(POWERBALL.jackpot_prob), 292_201_338, delta=1)
        tiers = {t.label: round(one_in(t.prob)) for t in POWERBALL.tiers}
        self.assertEqual(tiers["Match 5"], 11_688_054)
        self.assertEqual(tiers["Match 4 plus Powerball"], 913_129)
        self.assertEqual(tiers["Match 0 plus Powerball"], 38)
        self.assertEqual(tiers["Match 2"], 28)

    def test_jackpot_odds(self):
        self.assertAlmostEqual(one_in(EUROMILLIONS.jackpot_prob), 139_838_160, delta=1)
        self.assertAlmostEqual(one_in(THUNDERBALL.jackpot_prob), 8_060_598, delta=1)
        self.assertAlmostEqual(one_in(SET_FOR_LIFE.jackpot_prob), 15_339_390, delta=1)


class TestHotPicks(unittest.TestCase):
    def test_returns(self):
        # Pick 1: £10 at 1 in 10 for £1.50; Lotto £3 at 6/59 per round, two rounds, for £1.
        ev = lambda g: g.fixed_jackpot * g.jackpot_prob * g.rounds / g.price
        self.assertAlmostEqual(ev(EUROMILLIONS_HOTPICKS[0]), 10 * 0.1 / 1.5)
        self.assertAlmostEqual(ev(LOTTO_HOTPICKS[0]), 3 * 6 / 59 * 2)
        self.assertAlmostEqual(1 / EUROMILLIONS_HOTPICKS[4].jackpot_prob, 2_118_760)

    def test_published_odds(self):
        # Lotto HotPicks covers two rounds, so e.g. Pick 1 is 1 in 5.2 (not 59/12 = 4.9).
        for g, published in zip(LOTTO_HOTPICKS, (5.2, 57.3, 813, 15_172, 417_200)):
            self.assertAlmostEqual(g.top_prize_odds / published, 1, delta=0.01)
        for g, published in zip(EUROMILLIONS_HOTPICKS, (10, 122.5, 1_960, 46_060, 2_118_760)):
            self.assertAlmostEqual(g.top_prize_odds / published, 1, delta=0.01)

    def test_every_pick_count_is_listed(self):
        for g in LOTTO_HOTPICKS + EUROMILLIONS_HOTPICKS:
            self.assertIn(g.key, GAMES)
        self.assertEqual(len(LOTTO_HOTPICKS), 5)
        self.assertEqual(len(EUROMILLIONS_HOTPICKS), 5)


class TestHelpers(unittest.TestCase):
    def test_rollovers(self):
        # Newest first, as listed on the results page.
        self.assertEqual(lotto_rollovers([2.8e6, 2.0e6, 4.3e6, 3.5e6, 2.0e6], 2.0e6), 0)
        self.assertEqual(lotto_rollovers([2.8e6, 2.0e6, 4.3e6, 3.5e6, 2.0e6], 3.6e6), 2)
        self.assertEqual(lotto_rollovers([6e6, 5e6, 4e6, 3e6, 2e6], 7e6), 5)

    def test_annuity(self):
        self.assertAlmostEqual(annuity_pv_factor(30, 0.0), 1.0)
        self.assertLess(annuity_pv_factor(30, 0.045, 0.05), 0.6)


if __name__ == "__main__":
    unittest.main()
