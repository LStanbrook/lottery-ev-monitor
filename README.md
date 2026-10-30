# Lottery EV monitor

Works out the expected value (EV) of a line on each UK National Lottery draw game and alerts you when one goes over a threshold.

```
python monitor.py                       # table of every game, best value first
python monitor.py --notify              # same, plus alerts (once per jackpot)
python monitor.py --jackpot lotto=8m    # what-if: what would an £8m Lotto be worth?
python -m unittest discover -s tests -t .
```

Settings live in `config.toml`: the alert threshold, Windows toast and phone (ntfy) alerts, and the modelling assumptions. Every run also appends to `history.csv`, so you can chart how EV moves over time.

## How EV is worked out

| Game | Jackpot source | Lower tiers | Notes |
|---|---|---|---|
| Lotto (£2) | lottery.co.uk next estimate | fixed: £1m / £1,000 / £50 / £10 / £1 | Two rounds per ticket. Detects Must Be Won draws (5 rollovers), where the whole jackpot reaches players, so jackpot EV = jackpot ÷ tickets |
| EuroMillions (£2.50) | lottery.co.uk estimate | prizes from the last draw, or long-run averages | Includes UK Millionaire Maker (£1m ÷ UK tickets) |
| Powerball (£4) | lottery.co.uk estimate | prizes from the last draw | The jackpot is a 30-year annuity rising 5% a year, valued at present value (about 48% of the advertised figure) |
| Thunderball (£1), Set For Life (£1.50) | fixed | fixed | EV never changes, shown for comparison |

**Jackpot sharing:** ticket sales are estimated from the last draw's winner counts (winners in a busy tier ÷ that tier's odds). Other jackpot winners are then treated as Poisson-distributed.

**Not modelled:** Lotto Millionaire Raffle special draws, EuroMillions Must Be Won draws at the €250m cap, HotPicks, and scratchcards / instant win games. Instant win games have a fixed return to player, so there's nothing to monitor.

## Scheduling

GitHub Actions ([.github/workflows/monitor.yml](.github/workflows/monitor.yml)) runs the check at 08:00 and 16:00 UTC every day. Each run:

- sends phone alerts through [ntfy](https://ntfy.sh), using the topic stored in the `NTFY_TOPIC` repo secret
- commits `data/history.csv`, `data/state.json`, `data/dashboard.html` and `data/last_scrape.json` (the fallback used if lottery.co.uk can't be reached) back to the repo
- publishes the dashboard to https://lstanbrook.github.io/lottery-ev-monitor/

To run it now, use the Actions tab → "Lottery EV check" → Run workflow, or `gh workflow run monitor.yml`.

To get alerts, install the ntfy app and subscribe to the same topic. To change the topic: `gh secret set NTFY_TOPIC`.
