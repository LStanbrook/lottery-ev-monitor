"""Prize structures and per-line odds for UK National Lottery draw games (as of Oct 2026).

Odds are computed from each game's number matrix rather than typed in, so they can be
checked against the published figures (see tests/test_odds.py).
"""
from dataclasses import dataclass
from math import comb


@dataclass(frozen=True)
class Tier:
    label: str            # category name as shown on lottery.co.uk prize breakdowns
    prob: float           # chance per line, per round
    prize: float          # default prize in £ (fixed, or long-run average for pool-based tiers)


@dataclass(frozen=True)
class Game:
    key: str
    name: str
    price: float
    jackpot_label: str
    jackpot_prob: float   # per line, per round
    tiers: tuple[Tier, ...]
    rounds: int = 1       # Lotto draws two rounds per ticket since June 2026
    has_jackpot_feed: bool = True   # False = fixed top prize, nothing to monitor
    fixed_jackpot: float = 0.0      # nominal top prize for fixed-prize games


def _hypergeo(pick: int, pool: int, k: int) -> float:
    """Chance of matching exactly k of `pick` drawn numbers when choosing `pick` from `pool`."""
    return comb(pick, k) * comb(pool - pick, pick - k) / comb(pool, pick)


def _matrix(main_pick, main_pool, extra_pick, extra_pool):
    def p(k, s):
        return _hypergeo(main_pick, main_pool, k) * _hypergeo(extra_pick, extra_pool, s)
    return p


# --- Lotto: 6 from 59 plus a bonus ball drawn from the same pool, two rounds per ticket ---
_L = comb(59, 6)
LOTTO = Game(
    key="lotto", name="Lotto", price=2.00, rounds=2,
    jackpot_label="Match 6", jackpot_prob=1 / _L,
    tiers=(
        Tier("Match 5 plus Bonus", 6 / _L, 1_000_000),
        Tier("Match 5", 6 * 52 / _L, 1_000),
        Tier("Match 4", comb(6, 4) * comb(53, 2) / _L, 50),
        Tier("Match 3", comb(6, 3) * comb(53, 3) / _L, 10),
        Tier("Match 2", comb(6, 2) * comb(53, 4) / _L, 1),
    ),
)

# --- EuroMillions: 5 from 50 + 2 stars from 12. Lower tiers are pool-based; defaults are
# lottery.co.uk's Sep 2016 - Oct 2026 UK averages, overridden by the latest draw when available.
_em = _matrix(5, 50, 2, 12)
EUROMILLIONS = Game(
    key="euromillions", name="EuroMillions", price=2.50,
    jackpot_label="Match 5 and 2 Stars", jackpot_prob=_em(5, 2),
    tiers=(
        Tier("Match 5 and 1 Star", _em(5, 1), 262_773),
        Tier("Match 5", _em(5, 0), 25_455),
        Tier("Match 4 and 2 Stars", _em(4, 2), 1_350.31),
        Tier("Match 4 and 1 Star", _em(4, 1), 92.65),
        Tier("Match 3 and 2 Stars", _em(3, 2), 48.73),
        Tier("Match 4", _em(4, 0), 30.89),
        Tier("Match 2 and 2 Stars", _em(2, 2), 10.64),
        Tier("Match 3 and 1 Star", _em(3, 1), 8.23),
        Tier("Match 3", _em(3, 0), 6.78),
        Tier("Match 1 and 2 Stars", _em(1, 2), 5.21),
        Tier("Match 2 and 1 Star", _em(2, 1), 4.13),
        Tier("Match 2", _em(2, 0), 2.72),
    ),
)

# --- UK Powerball: 5 from 69 + 1 from 26, £4 a line. Jackpot is a 30-year annuity.
_pb = _matrix(5, 69, 1, 26)
POWERBALL = Game(
    key="powerball", name="Powerball", price=4.00,
    jackpot_label="Match 5 plus Powerball", jackpot_prob=_pb(5, 1),
    tiers=(
        Tier("Match 5", _pb(5, 0), 1_000_000),
        Tier("Match 4 plus Powerball", _pb(4, 1), 33_000),
        Tier("Match 4", _pb(4, 0), 1_000),
        Tier("Match 3 plus Powerball", _pb(3, 1), 500),
        Tier("Match 3", _pb(3, 0), 52.10),
        Tier("Match 2 plus Powerball", _pb(2, 1), 30.80),
        Tier("Match 1 plus Powerball", _pb(1, 1), 15.30),
        Tier("Match 0 plus Powerball", _pb(0, 1), 11.90),
        Tier("Match 2", _pb(2, 0), 8),
    ),
)

# --- Fixed-prize games: EV never changes, included for comparison only ---
_tb = _matrix(5, 39, 1, 14)
THUNDERBALL = Game(
    key="thunderball", name="Thunderball", price=1.00, has_jackpot_feed=False,
    jackpot_label="Match 5 plus Thunderball", jackpot_prob=_tb(5, 1), fixed_jackpot=500_000,
    tiers=(
        Tier("Match 5", _tb(5, 0), 5_000),
        Tier("Match 4 plus Thunderball", _tb(4, 1), 250),
        Tier("Match 4", _tb(4, 0), 100),
        Tier("Match 3 plus Thunderball", _tb(3, 1), 20),
        Tier("Match 3", _tb(3, 0), 10),
        Tier("Match 2 plus Thunderball", _tb(2, 1), 10),
        Tier("Match 1 plus Thunderball", _tb(1, 1), 5),
        Tier("Match 0 plus Thunderball", _tb(0, 1), 3),
    ),
)

_sfl = _matrix(5, 47, 1, 10)
SET_FOR_LIFE = Game(
    key="set_for_life", name="Set For Life", price=1.50, has_jackpot_feed=False,
    # £10k/month for 30 years; valued as an annuity in ev.py
    jackpot_label="Match 5 plus Life Ball", jackpot_prob=_sfl(5, 1), fixed_jackpot=120_000 * 30,
    tiers=(
        Tier("Match 5", _sfl(5, 0), 120_000),
        Tier("Match 4 plus Life Ball", _sfl(4, 1), 250),
        Tier("Match 4", _sfl(4, 0), 50),
        Tier("Match 3 plus Life Ball", _sfl(3, 1), 30),
        Tier("Match 3", _sfl(3, 0), 20),
        Tier("Match 2 plus Life Ball", _sfl(2, 1), 10),
        Tier("Match 2", _sfl(2, 0), 5),
    ),
)

# --- HotPicks: choose 1-5 numbers, win a fixed prize only if all of them are drawn.
# Lotto HotPicks plays both Lotto rounds (each pick must come up in the same round).
def _hotpicks(key, name, price, drawn, pool, rounds, prizes):
    return [
        Game(key=f"{key}_{n}", name=f"{name} (Pick {n})", price=price, rounds=rounds,
             has_jackpot_feed=False, jackpot_label=f"Pick {n}",
             jackpot_prob=comb(drawn, n) / comb(pool, n), fixed_jackpot=prize, tiers=())
        for n, prize in enumerate(prizes, start=1)
    ]


LOTTO_HOTPICKS = _hotpicks("lotto_hotpicks", "Lotto HotPicks", 1.00, 6, 59, 2,
                           (3, 30, 400, 6_500, 175_000))
EUROMILLIONS_HOTPICKS = _hotpicks("euromillions_hotpicks", "EuroMillions HotPicks", 1.50, 5, 50, 1,
                                  (10, 100, 1_500, 30_000, 1_000_000))


def _best(picks: list[Game]) -> Game:
    """The pick count with the best return. Prizes are fixed, so this never changes."""
    return max(picks, key=lambda g: g.fixed_jackpot * g.jackpot_prob * g.rounds / g.price)


GAMES = {g.key: g for g in (LOTTO, EUROMILLIONS, POWERBALL, THUNDERBALL, SET_FOR_LIFE,
                            _best(LOTTO_HOTPICKS), _best(EUROMILLIONS_HOTPICKS))}
