"""Expected value per line, in £, for each game.

Main modelling choices:
- Jackpot sharing: other jackpot winners are Poisson with mean lam = tickets_sold * P(jackpot).
  Your expected share given you win is (1 - e^-lam) / lam, so jackpot EV = value * p * that.
- Ticket sales are estimated from the latest prize breakdown: winners in a busy tier / that
  tier's probability. The next draw is assumed to sell `sales_growth` times as many.
- Lotto Must Be Won draws: if nobody hits the jackpot it rolls down to lower tiers, so the
  whole jackpot reaches players either way and its EV per ticket is simply jackpot / tickets.
- Annuity jackpots (Powerball, Set For Life) are valued at present value, not face value.
- UK prizes are tax-free, and Powerball's advertised UK jackpot is already a post-tax figure.
"""
from dataclasses import dataclass, field
from math import exp

from .games import Game
from .scrape import GameData

# Busiest tier for each game, used to back out how many tickets were sold.
SALES_TIER = {"lotto": "Match 3", "euromillions": "Match 2", "powerball": "Match 0 plus Powerball"}
POOL_BASED = {"euromillions", "powerball"}  # lower-tier prizes vary draw to draw


@dataclass
class Assumptions:
    discount_rate: float = 0.045
    powerball_annual_increase: float = 0.05
    sales_growth: float = 1.10
    lotto_must_be_won: str = "auto"       # "auto", "yes" or "no"
    lotto_mbw_sales_boost: float = 1.5
    millionaire_maker_winners: int = 1
    millionaire_maker_prize: float = 1_000_000


@dataclass
class Result:
    game: Game
    ev: float
    jackpot: float | None = None          # advertised
    jackpot_value: float | None = None    # what it's worth to you today
    jackpot_ev: float = 0.0
    other_ev: float = 0.0
    extra_ev: float = 0.0
    tickets: float | None = None
    share_chance: float | None = None     # P(someone else also wins | you win)
    must_be_won: bool = False
    rollovers: int | None = None          # Lotto only
    notes: list[str] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        """£ returned per £1 staked. 1.0 = break-even."""
        return self.ev / self.game.price

    @property
    def ratio_headline(self) -> float:
        """Same as ratio, but valuing the jackpot at its advertised figure rather than today's value.
        Jackpot EV is proportional to the jackpot's value, so it just scales up."""
        if not self.jackpot or not self.jackpot_value:
            return self.ratio
        uplift = self.jackpot_ev * (self.jackpot / self.jackpot_value - 1)
        return (self.ev + uplift) / self.game.price


def annuity_pv_factor(years: int, rate: float, growth: float = 0.0) -> float:
    """Present value of an annuity paid yearly from today, as a fraction of its face value."""
    face = sum((1 + growth) ** t for t in range(years))
    pv = sum(((1 + growth) / (1 + rate)) ** t for t in range(years))
    return pv / face


def tickets_sold(game: Game, data: GameData, column: str = "Total Winners") -> float | None:
    row = data.breakdown.get(SALES_TIER.get(game.key, ""))
    tier = next((t for t in game.tiers if t.label == SALES_TIER.get(game.key)), None)
    winners = row.winners(column) if row else None
    if not winners or not tier:
        return None
    return winners / (tier.prob * game.rounds)


def lotto_rollovers(recent_jackpots: list[float], next_jackpot: float) -> int:
    """Consecutive rollovers leading into the next draw (a jackpot that grows was not won)."""
    seq = list(reversed(recent_jackpots)) + [next_jackpot]
    count = 0
    for prev, cur in zip(reversed(seq[:-1]), reversed(seq[1:])):
        if cur > prev:
            count += 1
        else:
            break
    return count


def evaluate(game: Game, data: GameData | None, a: Assumptions) -> Result:
    data = data or GameData()
    res = Result(game=game, ev=0.0)

    for tier in game.tiers:
        prize = tier.prize
        if game.key in POOL_BASED:
            row = data.breakdown.get(tier.label)
            if row and row.prize:  # 0 when nobody won the tier
                prize = row.prize
        res.other_ev += tier.prob * prize * game.rounds

    if not game.has_jackpot_feed:
        value = game.fixed_jackpot
        if game.key == "set_for_life":
            value *= annuity_pv_factor(30, a.discount_rate)
        res.jackpot = game.fixed_jackpot
        res.jackpot_value = value
        res.jackpot_ev = value * game.jackpot_prob * game.rounds
        res.notes.append("fixed prizes")
        res.ev = res.jackpot_ev + res.other_ev
        return res

    if data.jackpot is None:
        res.notes.append("no jackpot found, lower tiers only")
        res.ev = res.other_ev
        return res

    res.jackpot = data.jackpot
    value = data.jackpot
    if game.key == "powerball":
        value *= annuity_pv_factor(30, a.discount_rate, a.powerball_annual_increase)
    res.jackpot_value = value

    sold = tickets_sold(game, data)
    if sold:
        sold *= a.sales_growth

    if game.key == "lotto":
        if a.lotto_must_be_won == "auto":
            n = res.rollovers = lotto_rollovers(data.recent_jackpots, data.jackpot)
            res.must_be_won = n >= 5
            res.notes.append(f"{n} rollover{'s' if n != 1 else ''}")
        else:
            res.must_be_won = a.lotto_must_be_won == "yes"
        if res.must_be_won and sold:
            sold *= a.lotto_mbw_sales_boost
            res.notes.append("MUST BE WON")
    res.tickets = sold

    p = game.jackpot_prob * game.rounds
    if res.must_be_won and sold:
        res.jackpot_ev = value / sold
    elif sold:
        lam = sold * p
        res.jackpot_ev = value * p * (1 - exp(-lam)) / lam
        res.share_chance = 1 - exp(-lam)
    else:
        res.jackpot_ev = value * p
        res.notes.append("sales unknown, sharing ignored")

    if game.key == "euromillions":
        uk_sold = tickets_sold(game, data, column="UK Winners")
        if uk_sold:
            res.extra_ev = a.millionaire_maker_winners * a.millionaire_maker_prize / (uk_sold * a.sales_growth)
        else:
            res.notes.append("Millionaire Maker not valued")

    res.ev = res.jackpot_ev + res.other_ev + res.extra_ev
    return res
