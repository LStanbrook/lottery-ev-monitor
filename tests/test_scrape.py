"""Homepage jackpot parsing: the generic label belongs to whichever game drew most recently."""
import unittest

from lottery_ev.scrape import home_jackpot


def big(key, name, jackpot):
    return (f'<div class="abstract {key}Box homeResults bigHomeResult"><h2>{name} Results</h2>'
            f'<div class="jackpotCont {key}Box">Jackpot: £1,234,567 '
            f'<span>Next Estimated Jackpot:</span> <span class="bigJackpot">£{jackpot}</span></div></div>')


def short(key, name, jackpot):
    return (f'<div class="abstract {key}Box homeResultsShort floatRight">{name} '
            f'<span>Tuesday\'s Est. {name} Jackpot:</span> <span>£{jackpot}</span></div>')


IRISH = ('<div class="abstract homeBox irish-lottoBox centred">Irish Lotto Results '
         "Tonight's Irish Lotto Jackpot: £2.2 Million</div>")


class TestHomeJackpot(unittest.TestCase):
    def check(self, home, lotto, euro, power):
        self.assertEqual(home_jackpot(home, "lotto", "Lotto"), lotto)
        self.assertEqual(home_jackpot(home, "euromillions", "EuroMillions"), euro)
        self.assertEqual(home_jackpot(home, "powerball", "Powerball"), power)

    def test_lotto_drew_last(self):
        home = (big("lotto", "Lotto", "5.1 Million") + short("euromillions", "EuroMillions", "118 Million")
                + IRISH + short("powerball", "Powerball", "15 Million"))
        self.check(home, 5.1e6, 118e6, 15e6)

    def test_euromillions_drew_last(self):
        # The layout on 7 Nov 2026 that made Lotto read EuroMillions' £118m.
        home = (big("euromillions", "EuroMillions", "118 Million") + short("lotto", "Lotto", "4.3 Million")
                + IRISH + short("powerball", "Powerball", "10 Million"))
        self.check(home, 4.3e6, 118e6, 10e6)

    def test_powerball_drew_last(self):
        home = (big("powerball", "Powerball", "15 Million") + short("lotto", "Lotto", "5.1 Million")
                + short("euromillions", "EuroMillions", "118 Million") + IRISH)
        self.check(home, 5.1e6, 118e6, 15e6)

    def test_missing_box(self):
        self.assertIsNone(home_jackpot(big("euromillions", "EuroMillions", "118 Million"), "lotto", "Lotto"))


if __name__ == "__main__":
    unittest.main()
