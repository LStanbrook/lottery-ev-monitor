"""Expected value of each UK National Lottery draw game, with alerts above a threshold.

    python monitor.py                      # print the table
    python monitor.py --notify             # also alert on games over the threshold (once per jackpot)
    python monitor.py --jackpot lotto=12m  # what-if with a jackpot you choose (no scraping for it)
"""
import argparse
import csv
import json
import os
import sys
import tomllib
from datetime import datetime
from pathlib import Path

from lottery_ev import dashboard, notify
from lottery_ev.ev import Assumptions, evaluate
from lottery_ev.games import GAMES
from lottery_ev.scrape import GameData, parse_money, scrape_all

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
STATE_FILE = DATA_DIR / "state.json"
HISTORY_FILE = DATA_DIR / "history.csv"
DASHBOARD_FILE = DATA_DIR / "dashboard.html"


def load_config() -> dict:
    with open(ROOT / "config.toml", "rb") as f:
        return tomllib.load(f)


def money(x: float | None) -> str:
    if x is None:
        return "-"
    if x >= 1e6:
        return f"£{x / 1e6:,.1f}m"
    return f"£{x:,.0f}" if x >= 1000 else f"£{x:,.2f}"


def print_table(results) -> None:
    header = f"{'Game':<14}{'Price':>7}{'Jackpot':>10}{'Worth today':>13}{'EV/line':>9}{'Per £1':>8}{'Share?':>8}  Notes"
    print(header)
    print("-" * len(header))
    for r in sorted(results, key=lambda r: r.ratio, reverse=True):
        share = f"{r.share_chance:.0%}" if r.share_chance is not None else "-"
        print(f"{r.game.name:<14}{money(r.game.price):>7}{money(r.jackpot):>10}{money(r.jackpot_value):>13}"
              f"{money(r.ev):>9}{r.ratio:>7.0%} {share:>8}  {', '.join(r.notes)}")
    print("\nPer £1 = expected £ back per £1 staked (100% = break-even). "
          "Share? = chance a jackpot win would be shared.")


def append_history(results) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    new = not HISTORY_FILE.exists()
    with open(HISTORY_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "game", "jackpot", "ev", "ratio", "tickets", "must_be_won"])
        now = datetime.now().isoformat(timespec="seconds")
        for r in results:
            w.writerow([now, r.game.key, r.jackpot or "", round(r.ev, 4), round(r.ratio, 4),
                        round(r.tickets) if r.tickets else "", r.must_be_won])


def send_alerts(results, cfg: dict) -> None:
    alerts = cfg.get("alerts", {})
    per_game = alerts.get("per_game", {})
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    for r in results:
        threshold = per_game.get(r.game.key, alerts.get("threshold", 0.6))
        # Key on the jackpot so we alert once per draw, not on every run.
        key = f"{r.jackpot}|{r.must_be_won}"
        if r.ratio < threshold or state.get(r.game.key) == key:
            continue
        title = f"{r.game.name}: {r.ratio:.0%} return"
        body = (f"EV {money(r.ev)} per {money(r.game.price)} line, jackpot {money(r.jackpot)}"
                + (" - MUST BE WON" if r.must_be_won else ""))
        print(f"ALERT  {title} - {body}")
        if cfg.get("notify", {}).get("windows_toast", True) and sys.platform == "win32":
            notify.windows_toast(title, body)
        # In GitHub Actions the topic comes from the NTFY_TOPIC secret.
        if topic := os.environ.get("NTFY_TOPIC") or cfg.get("notify", {}).get("ntfy_topic"):
            notify.ntfy(topic, title, body)
        state[r.game.key] = key
    DATA_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--notify", action="store_true", help="send alerts for games over the threshold")
    parser.add_argument("--jackpot", action="append", default=[], metavar="GAME=AMOUNT",
                        help="override a jackpot, e.g. lotto=12m or powerball=1.2bn")
    parser.add_argument("--no-scrape", action="store_true", help="use only --jackpot values and defaults")
    args = parser.parse_args()

    cfg = load_config()
    assumptions = Assumptions(**cfg.get("assumptions", {}))

    live: dict[str, GameData] = {}
    if not args.no_scrape:
        try:
            live = scrape_all()
        except Exception as e:  # keep going with fixed-prize games and overrides
            print(f"Warning: could not fetch live jackpots ({e})", file=sys.stderr)
    for item in args.jackpot:
        key, _, amount = item.partition("=")
        live.setdefault(key, GameData()).jackpot = parse_money(amount)

    results = [evaluate(game, live.get(key), assumptions) for key, game in GAMES.items()]
    print_table(results)
    if not args.jackpot:
        append_history(results)
        dashboard.build(results, HISTORY_FILE, cfg.get("alerts", {}).get("threshold", 0.6), DASHBOARD_FILE)
    if args.notify:
        send_alerts(results, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
