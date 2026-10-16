"""Fictional market universe for the demo.

All companies, tickers, prices, and filings are invented. Any resemblance of a ticker to a
real listed security is coincidental; the data must not be read as information about one.

The dataset covers the September 2026 trading month and contains a handful of planted
"stories" (events) that an analyst can discover through conversation in Amazon Quick.
"""
from datetime import date

# Trading calendar: September 2026 weekdays, excluding Labor Day (Mon 7 Sep).
HOLIDAYS = {date(2026, 9, 7)}
START, END = date(2026, 9, 1), date(2026, 9, 30)
# US equities trade 09:30-16:00 ET. ET is UTC-4 for the whole window (EDT), so 13:30-20:00 UTC.
UTC_OFFSET_HOURS = 4
SESSION_MINUTES = 390

SECTOR_DRIFT = {  # daily log-drift; sets up a defensive rotation over the month
    "Technology": -0.0008, "Communication Services": 0.0, "Consumer Discretionary": -0.0003,
    "Consumer Staples": 0.0012, "Health Care": 0.0004, "Financials": -0.0002,
    "Energy": 0.0010, "Industrials": 0.0002, "Utilities": 0.0025, "Real Estate": 0.0005,
}

# sym, name, sector, industry, start_price, shares_out_m, eps_ttm, revenue_ttm_bn, ebitda_ttm_bn,
# net_debt_bn, dividend_yield_pct, beta, liquidity (relative trade count), hq
_COMPANIES = [
    ("NVLT", "Novalight Semiconductor", "Technology", "Semiconductors", 412.00, 2450, 9.80, 96.0, 52.0, -18.0, 0.2, 1.70, 10, "Santa Clara, CA"),
    ("ORCH", "Orchard Devices", "Technology", "Consumer Electronics", 228.50, 15200, 6.90, 410.0, 140.0, -30.0, 0.45, 1.15, 10, "Cupertino, CA"),
    ("SKYF", "Skyforge Software", "Technology", "Application Software", 318.40, 960, 7.10, 38.5, 13.2, -6.5, 0.0, 1.30, 6, "Seattle, WA"),
    ("HELX", "Helix Networks", "Technology", "Networking Equipment", 96.20, 1800, 4.15, 52.0, 16.8, 4.2, 1.6, 1.05, 5, "San Jose, CA"),
    ("STRM", "Streamline Media", "Communication Services", "Streaming", 142.75, 860, 3.40, 34.0, 7.9, 12.0, 0.0, 1.25, 5, "Los Angeles, CA"),
    ("PNGO", "Pingo Social", "Communication Services", "Interactive Media", 61.30, 2900, 2.05, 44.0, 18.5, -9.0, 0.0, 1.40, 6, "Austin, TX"),
    ("ROVR", "Rover Motors", "Consumer Discretionary", "Electric Vehicles", 188.90, 3100, 2.30, 92.0, 11.5, -14.0, 0.0, 1.90, 8, "Fremont, CA"),
    ("CRTL", "Cartwheel Retail", "Consumer Discretionary", "Broadline Retail", 74.60, 1450, 4.40, 108.0, 9.6, 8.5, 2.1, 0.95, 4, "Minneapolis, MN"),
    ("BRSA", "Brasa Restaurants", "Consumer Discretionary", "Restaurants", 51.80, 720, 2.60, 11.2, 2.3, 3.1, 1.8, 0.90, 3, "Denver, CO"),
    ("GRNF", "Greenfield Foods", "Consumer Staples", "Packaged Foods", 58.40, 1300, 3.25, 26.0, 4.9, 9.0, 3.2, 0.55, 3, "Chicago, IL"),
    ("PURE", "Purewell Household", "Consumer Staples", "Household Products", 132.10, 2350, 6.15, 82.0, 21.0, 22.0, 2.6, 0.50, 4, "Cincinnati, OH"),
    ("VTRX", "Vitrexa Therapeutics", "Health Care", "Biotechnology", 38.20, 410, -1.85, 0.6, -0.5, -1.2, 0.0, 1.60, 3, "Cambridge, MA"),
    ("CRDN", "Cardion Medical", "Health Care", "Medical Devices", 104.50, 1250, 4.85, 33.0, 9.8, 6.0, 1.2, 0.80, 4, "Minneapolis, MN"),
    ("ARBR", "Arbor Health Plans", "Health Care", "Managed Care", 486.00, 920, 24.10, 372.0, 31.0, 48.0, 1.5, 0.70, 4, "Hartford, CT"),
    ("HRBR", "Harborview Bancorp", "Financials", "Regional Banks", 47.90, 1650, 4.95, 14.8, 0.0, 0.0, 3.9, 1.20, 5, "Pittsburgh, PA"),
    ("LDGR", "Ledger Pay", "Financials", "Payments", 83.25, 1040, 3.10, 18.6, 5.4, -3.0, 0.0, 1.45, 5, "San Francisco, CA"),
    ("SUMT", "Summit Insurance", "Financials", "Property & Casualty", 211.30, 590, 15.20, 49.0, 0.0, 0.0, 1.9, 0.75, 3, "Omaha, NE"),
    ("PTRA", "Petra Energy", "Energy", "Integrated Oil & Gas", 112.60, 4100, 9.40, 340.0, 72.0, 31.0, 3.4, 0.95, 6, "Houston, TX"),
    ("SOLN", "Solenne Renewables", "Energy", "Renewable Energy", 27.45, 1900, 0.85, 7.4, 2.6, 11.0, 1.1, 1.50, 4, "Phoenix, AZ"),
    ("AXLE", "Axle Freight", "Industrials", "Trucking & Logistics", 156.80, 380, 8.30, 19.5, 3.4, 4.6, 1.3, 1.10, 3, "Memphis, TN"),
    ("AERO", "Aerowind Aerospace", "Industrials", "Aerospace & Defense", 274.20, 610, 12.60, 71.0, 10.9, 19.0, 2.0, 0.85, 4, "Arlington, VA"),
    ("VOLT", "Voltaic Utilities", "Utilities", "Electric Utilities", 68.30, 2050, 3.55, 24.5, 10.6, 58.0, 3.6, 0.45, 3, "Columbus, OH"),
    ("KEYS", "Keystone Office REIT", "Real Estate", "Office REITs", 39.70, 840, 1.20, 3.9, 2.2, 9.8, 6.1, 1.10, 2, "New York, NY"),
    ("TERA", "Terabyte Data Centers", "Real Estate", "Data Center REITs", 141.90, 950, 2.75, 7.1, 3.7, 21.0, 2.8, 0.95, 3, "Ashburn, VA"),
]
FIELDS = ["sym", "name", "sector", "industry", "start_price", "shares_out_m", "eps_ttm",
          "revenue_ttm_bn", "ebitda_ttm_bn", "net_debt_bn", "dividend_yield_pct", "beta",
          "liquidity", "hq"]
COMPANIES = [dict(zip(FIELDS, row)) for row in _COMPANIES]

# Planted stories. time_et before 09:30 means pre-market news, applied as an opening gap.
# jump: log price move at the news time. day_vol: trade-count multipliers for that day onward.
# peers: sympathy moves at the same minute. drift: extra per-day drift for listed days.
EVENTS = [
    dict(sym="CRTL", day="2026-09-03", time_et="07:00", jump=0.075, day_vol=[3.2, 1.6],
         label="8-K: Q2 results beat, full-year guidance raised"),
    dict(sym="HRBR", day="2026-09-09", time_et="11:45", jump=-0.072, day_vol=[4.0, 2.2, 1.5],
         peers={"KEYS": -0.025}, drift={"2026-09-10": -0.006, "2026-09-11": -0.005},
         label="8-K: higher provision for credit losses on commercial real estate"),
    dict(sym="NVLT", day="2026-09-15", time_et="14:10", jump=-0.11, day_vol=[5.0, 2.6, 1.6],
         peers={"HELX": -0.03, "TERA": -0.015},
         label="8-K: new export license requirement for advanced accelerators"),
    dict(sym="*", day="2026-09-16", time_et="14:00", jump=0.004, day_vol=[1.4],
         label="Market-wide: Federal Reserve rate decision"),
    # Recall 8-K is filed after the close on 17 Sep; the market reacts at the next open.
    dict(sym="ROVR", day="2026-09-18", time_et="09:00", jump=-0.064, day_vol=[3.4, 1.7],
         label="8-K: voluntary recall of ~120,000 vehicles"),
    dict(sym="ORCH", day="2026-09-22", time_et="07:00", jump=-0.018, day_vol=[2.1, 1.8, 1.6, 1.4],
         drift={"2026-09-23": -0.008, "2026-09-24": -0.006, "2026-09-25": -0.004},
         label="10-K: annual report with expanded supply-chain and AI regulation risk factors"),
    # Unusual activity ahead of the VTRX approval: heavy volume plus block buys late in the day.
    dict(sym="VTRX", day="2026-09-22", time_et="15:30", jump=0.018, day_vol=[2.6, 3.1],
         drift={"2026-09-23": 0.022}, blocks={"2026-09-22": 14, "2026-09-23": 21},
         label="Unusual pre-announcement volume and block buying"),
    dict(sym="VTRX", day="2026-09-24", time_et="07:30", jump=0.20, day_vol=[7.0, 3.0, 1.8],
         label="8-K: FDA approval of VX-401"),
    dict(sym="LDGR", day="2026-09-29", time_et="08:00", jump=-0.052, day_vol=[3.0, 1.7],
         label="8-K: CEO departure and interim CEO appointment"),
]
