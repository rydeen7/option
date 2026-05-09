#!/usr/bin/env python3
"""
Download 2 years of daily US options volume (Call/Put) from CBOE.
Data source: https://www.cboe.com/markets/us/options/market-statistics/daily?dt=YYYY-MM-DD
"""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_CSV = DATA_DIR / "options_volume.csv"
DATA_DIR.mkdir(exist_ok=True)

BASE_URL = "https://www.cboe.com/markets/us/options/market-statistics/daily"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_WORKERS = 5
RETRY_COUNT = 3
DELAY_BETWEEN_BATCHES = 1.0  # seconds


def fetch_one(date_str: str) -> dict | None:
    """Fetch options data for a single date. Returns dict or None on failure."""
    url = f"{BASE_URL}?dt={date_str}"
    for attempt in range(RETRY_COUNT):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                time.sleep(2)
                continue
            data = parse_html(r.text, date_str)
            return data
        except Exception:
            if attempt < RETRY_COUNT - 1:
                time.sleep(2)
    return None


def parse_html(html: str, date_str: str) -> dict | None:
    """Parse CBOE page HTML to extract options volume and P/C ratio."""
    try:
        idx = html.find('\\"optionsData\\":')
        if idx < 0:
            return None

        # Find end of optionsData block (before selectedDate)
        idx_end = html.find('\\"selectedDate\\"', idx)
        if idx_end < 0:
            return None

        # Unescape JS string content: \\" -> "
        raw = html[idx:idx_end].rstrip(',')
        unescaped = raw.replace('\\"', '"')
        parsed = json.loads('{' + unescaped + '}')
        options = parsed['optionsData']

        # Extract actual selected date from page (validates the date had data)
        date_match = re.search(r'selectedDate\\":\\"(\d{4}-\d{2}-\d{2})', html)
        actual_date = date_match.group(1) if date_match else date_str

        # Only accept if the returned date matches our request (skip holidays/weekends)
        if actual_date != date_str:
            return None

        # P/C ratio
        ratios = {r['name']: r['value'] for r in options['ratios']}
        total_pc = float(ratios.get('TOTAL PUT/CALL RATIO', 0))

        # Volume data
        vol = next(x for x in options['SUM OF ALL PRODUCTS'] if x['name'] == 'VOLUME')
        call_vol = int(vol['call'])
        put_vol = int(vol['put'])
        total_vol = int(vol['total'])

        if call_vol == 0 or put_vol == 0:
            return None

        return {
            'date': actual_date,
            'call_volume': call_vol,
            'put_volume': put_vol,
            'total_volume': total_vol,
            'put_call_ratio': total_pc,
            'call_put_ratio': round(call_vol / put_vol, 4),
        }
    except Exception:
        return None


def generate_business_days(years: int = 2) -> list[str]:
    """Generate business day date strings for the past N years."""
    end = datetime.today() - timedelta(days=1)
    start = end - timedelta(days=int(years * 365.25))
    dates = pd.bdate_range(start=start, end=end)
    return [d.strftime('%Y-%m-%d') for d in dates]


def download_all(years: int = 2) -> pd.DataFrame:
    """Download options data for all business days over the past N years."""
    dates = generate_business_days(years)
    print(f"Fetching {len(dates)} trading days ({years} years)...")

    results = []
    errors = 0
    batch_size = MAX_WORKERS

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for i in range(0, len(dates), batch_size):
            batch = dates[i:i + batch_size]
            futures = {executor.submit(fetch_one, d): d for d in batch}
            for future in as_completed(futures):
                data = future.result()
                if data:
                    results.append(data)
                else:
                    errors += 1

            done = min(i + batch_size, len(dates))
            print(f"  {done}/{len(dates)} ({done*100//len(dates)}%)  "
                  f"records={len(results)} errors={errors}", end='\r')
            if i + batch_size < len(dates):
                time.sleep(DELAY_BETWEEN_BATCHES)

    print()
    df = pd.DataFrame(results)
    if df.empty:
        raise RuntimeError("No data retrieved. Check network or CBOE site availability.")

    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    return df


def main():
    print("=== CBOE US Options Volume Downloader ===")
    df = download_all(years=2)
    df.to_csv(DATA_CSV, index=False)
    print(f"Saved {len(df)} rows to {DATA_CSV}")
    print(df.tail(3).to_string())


if __name__ == "__main__":
    main()
