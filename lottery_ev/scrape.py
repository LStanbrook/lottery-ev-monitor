"""Reads jackpot estimates and latest prize breakdowns from lottery.co.uk (public pages).

The official national-lottery.co.uk site renders jackpots client-side from a private API,
so we use the independent results site instead. A full run makes about 8 page requests.
"""
import functools
import html
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field

BASE = "https://www.lottery.co.uk"
USER_AGENT = "lottery-ev-monitor/0.1 (personal use)"
_MONEY = re.compile(r"([\d][\d,]*(?:\.\d+)?)\s*(million|billion|m\b|bn\b)?", re.I)


@dataclass
class BreakdownRow:
    label: str
    prize: float | None
    cells: dict[str, str]

    def winners(self, column: str = "Total Winners") -> int | None:
        raw = self.cells.get(column, "")
        digits = raw.replace(",", "")
        return int(digits) if digits.isdigit() else None


@dataclass
class GameData:
    jackpot: float | None = None
    breakdown: dict[str, BreakdownRow] = field(default_factory=dict)
    breakdown_url: str | None = None
    recent_jackpots: list[float] = field(default_factory=list)  # newest first (Lotto only)


@functools.cache
def fetch(path: str, attempts: int = 3) -> str:
    req = urllib.request.Request(BASE + path, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
            break
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(10 * (attempt + 1))
    time.sleep(1)  # be polite between requests
    # Pages are mostly UTF-8 but contain stray Latin-1 £ signs; neither matters for parsing numbers.
    return raw.decode("utf-8", errors="replace")


def _text(fragment: str) -> str:
    fragment = re.sub(r"<script.*?</script>|<style.*?</style>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse_money(text: str) -> float | None:
    m = _MONEY.search(text)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    if unit in ("million", "m"):
        value *= 1e6
    elif unit in ("billion", "bn"):
        value *= 1e9
    return value


def money_after(page: str, anchor: str, window: int = 600) -> float | None:
    i = page.find(anchor)
    if i < 0:
        return None
    return parse_money(_text(page[i + len(anchor): i + len(anchor) + window]))


def parse_breakdown(page: str) -> dict[str, BreakdownRow]:
    rows = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.S):
        label = re.search(r"<strong>(.*?)</strong>", tr, flags=re.S)
        if not label:
            continue
        cells = {
            title: _text(body)
            for title, body in re.findall(r'data-title="([^"]+)"[^>]*>(.*?)</td>', tr, flags=re.S)
        }
        if "Prize" not in cells:
            continue
        name = _text(label.group(1))
        rows[name] = BreakdownRow(name, parse_money(cells["Prize"]), cells)
    return rows


def _with_breakdown(slug: str, data: GameData, results_page: str) -> GameData:
    links = re.findall(rf'href="(/{slug}/results-\d{{2}}-\d{{2}}-\d{{4}})"', results_page)
    # The newest draw's breakdown may not be published yet, so fall back to the one before it.
    for url in list(dict.fromkeys(links))[:2]:
        rows = parse_breakdown(fetch(url))
        if rows:
            data.breakdown_url, data.breakdown = url, rows
            break
    return data


def _lotto() -> GameData:
    results = fetch("/lotto/results")
    # The results page's estimate isn't always served (e.g. to non-UK visitors such as
    # GitHub's runners), so fall back to the homepage's Lotto box.
    data = GameData(jackpot=money_after(results, "Next Estimated Lotto Jackpot")
                    or money_after(fetch("/"), "Next Estimated Jackpot:"))
    # Each previous draw is listed as "Jackpot: £X", newest first.
    data.recent_jackpots = [
        v for v in (parse_money(_text(s)) for s in
                    re.findall(r"Jackpot:\s*(.{0,120}?)</", results, flags=re.S)) if v
    ]
    return _with_breakdown("lotto", data, results)


def _euromillions() -> GameData:
    data = GameData(jackpot=money_after(fetch("/"), "Est. EuroMillions Jackpot"))
    return _with_breakdown("euromillions", data, fetch("/euromillions/results"))


def _powerball() -> GameData:
    results = fetch("/powerball/results")
    data = GameData(jackpot=money_after(results, "Next Powerball Jackpot"))
    return _with_breakdown("powerball", data, results)


def scrape_all() -> dict[str, GameData]:
    """Returns live data keyed by game key. Games that fail to scrape are left out."""
    out: dict[str, GameData] = {}
    for key, scraper in (("lotto", _lotto), ("euromillions", _euromillions), ("powerball", _powerball)):
        try:
            out[key] = scraper()
        except OSError as e:
            print(f"Warning: could not fetch {key} ({e})", file=sys.stderr)
            continue
        if out[key].jackpot is None:
            print(f"Warning: no {key} jackpot found on lottery.co.uk", file=sys.stderr)
        if not out[key].breakdown:
            print(f"Warning: no {key} prize breakdown found", file=sys.stderr)
    return out
