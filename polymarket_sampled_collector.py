"""
Polymarket Sampled Data Collector
Extends the base collector with time-window sampling for better coverage.
Collects markets across multiple weeks and samples trades from large markets.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import json
import pandas as pd

from polymarket_data_collector import PolymarketDataCollector


class PolymarketSampledCollector(PolymarketDataCollector):
    """
    Extended collector with time-window sampling.
    - Collects markets across multiple weeks (not just most recent)
    - Samples trades from large markets (2000+ trades)
    """

    def get_sampled_trades_for_market(self,
                                       condition_id: str,
                                       max_trades: int = 10000,
                                       num_windows: int = 10) -> tuple[List[Dict], bool]:
        """
        Fetch trades for a market, sampling for very large markets.

        Strategy:
        - Small/medium markets (<2000 trades): fetch all trades
        - Large markets (2000+ trades): keep newest 2000, sample evenly from older portion

        Args:
            condition_id: Market's conditionId
            max_trades: Maximum total trades to return
            num_windows: Number of time windows to sample older trades from

        Returns:
            Tuple of (list of trades, was_sampled)
        """
        import random

        url = f"{self.data_api_url}/trades"
        batch_size = 500  # API max
        offset = 0

        # Phase 1: Fetch up to 2000 trades to assess market size
        all_trades = []
        while len(all_trades) < 2000:
            params = {'market': condition_id, 'limit': batch_size, 'offset': offset}
            batch = self._make_request(url, params)

            if not batch:
                break

            all_trades.extend(batch)

            if len(batch) < batch_size:
                # We've fetched all trades, no sampling needed
                return all_trades[:max_trades], False

            offset += batch_size
            time.sleep(0.1)

        if len(all_trades) < 2000:
            return all_trades[:max_trades], False

        # Phase 2: Large market - continue fetching all trades for sampling
        # Fetch remaining trades (up to a reasonable limit to avoid huge fetches)
        max_fetch = max(max_trades * 2, 10000)  # Fetch enough to sample from

        while len(all_trades) < max_fetch:
            params = {'market': condition_id, 'limit': batch_size, 'offset': offset}
            batch = self._make_request(url, params)

            if not batch:
                break

            all_trades.extend(batch)

            if len(batch) < batch_size:
                break

            offset += batch_size
            time.sleep(0.1)

        # If we have fewer trades than max_trades, return all
        if len(all_trades) <= max_trades:
            return all_trades, False

        # Phase 3: Sample to get good time coverage
        # Keep newest 2000, sample evenly from the rest
        newest_trades = all_trades[:2000]
        older_trades = all_trades[2000:]

        remaining_budget = max_trades - len(newest_trades)
        if remaining_budget <= 0:
            return newest_trades[:max_trades], True

        if len(older_trades) <= remaining_budget:
            # Can keep all older trades
            sampled = newest_trades + older_trades
        else:
            # Sample evenly across time windows from older trades
            older_windows = min(num_windows, 5)
            window_size = len(older_trades) // older_windows
            samples_per_window = remaining_budget // older_windows

            sampled_older = []
            for i in range(older_windows):
                window_start = i * window_size
                window_end = (i + 1) * window_size if i < older_windows - 1 else len(older_trades)
                window_trades = older_trades[window_start:window_end]

                if len(window_trades) <= samples_per_window:
                    sampled_older.extend(window_trades)
                else:
                    sampled_older.extend(random.sample(window_trades, samples_per_window))

            sampled = newest_trades + sampled_older

        # Sort by timestamp and return
        sampled.sort(key=lambda x: x['timestamp'], reverse=True)
        return sampled[:max_trades], True

    def _fetch_markets_for_window(self,
                                   start_date: str,
                                   end_date: str,
                                   max_markets: int) -> List[Dict]:
        """
        Fetch markets for a specific time window with pagination.

        Args:
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            max_markets: Maximum markets to fetch for this window

        Returns:
            List of market dictionaries
        """
        url = f"{self.gamma_url}/markets"
        batch_size = 100  # API limit per request
        offset = 0
        markets = []

        while len(markets) < max_markets:
            params = {
                'closed': 'true',
                'limit': min(batch_size, max_markets - len(markets)),
                'offset': offset,
                'order': 'volume',
                'ascending': 'false',
                'end_date_min': start_date,
                'end_date_max': end_date,
            }

            batch = self._make_request(url, params)

            if not batch:
                break

            markets.extend(batch)

            if len(batch) < batch_size:
                break

            offset += batch_size
            time.sleep(0.1)

        return markets

    def _fetch_all_markets(self,
                           weeks_back: int,
                           markets_per_window: int) -> List[Dict]:
        """
        Fetch markets across multiple weekly time windows.

        Args:
            weeks_back: Number of weeks to look back
            markets_per_window: Max markets per weekly window

        Returns:
            List of unique market dictionaries (deduplicated by condition_id)
        """
        now = datetime.now(timezone.utc)
        all_markets = []
        seen_condition_ids = set()

        for week in range(weeks_back):
            end_date = now - timedelta(weeks=week)
            start_date = end_date - timedelta(weeks=1)

            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')

            print(f"\nFetching markets from {start_str} to {end_str}...")

            markets = self._fetch_markets_for_window(start_str, end_str, markets_per_window)

            # Deduplicate by condition_id
            new_markets = 0
            for market in markets:
                cid = market.get('conditionId') or market.get('condition_id')
                if cid and cid not in seen_condition_ids:
                    seen_condition_ids.add(cid)
                    all_markets.append(market)
                    new_markets += 1

            print(f"  Found {len(markets)} markets ({new_markets} new, {len(markets) - new_markets} duplicates)")

        return all_markets

    def _collect_trades_for_markets(self,
                                    markets: List[Dict],
                                    max_trades_per_market: int,
                                    save_progress: bool = True) -> tuple[List[Dict], dict]:
        """
        Collect trades for a list of markets.

        Args:
            markets: List of market dictionaries
            max_trades_per_market: Maximum trades to fetch per market
            save_progress: Whether to save progress checkpoints

        Returns:
            Tuple of (list of trade data dicts, stats dict)
        """
        all_trade_data = []
        stats = {
            'markets_with_trades': 0,
            'markets_skipped_no_resolution': 0,
            'markets_skipped_no_trades': 0,
        }

        for i, market in enumerate(markets):
            question = market.get('question', 'Unknown')[:60]
            print(f"\nProcessing market {i+1}/{len(markets)}: {question}...")

            processed_market = self.process_market_for_analysis(market)
            if not processed_market:
                stats['markets_skipped_no_resolution'] += 1
                print(f"  Skipped: No valid resolution data")
                continue

            trades, truncated = self.get_trades_for_market(
                processed_market['condition_id'], max_trades_per_market)
            note = " (truncated)" if truncated else ""

            if not trades:
                stats['markets_skipped_no_trades'] += 1
                print(f"  Skipped: No trades found")
                continue

            print(f"  Found {len(trades)} trades{note}")
            stats['markets_with_trades'] += 1

            all_trade_data.extend(self._process_trades(trades, processed_market))

            # Save progress checkpoint
            if save_progress and (i + 1) % 50 == 0:
                temp_df = pd.DataFrame(all_trade_data)
                temp_df.to_csv(self.output_dir / f'trades_progress_{i+1}.csv', index=False)
                print(f"\n  Progress saved: {len(all_trade_data):,} trades from {stats['markets_with_trades']} markets")

        return all_trade_data, stats

    def collect_by_time_windows(self,
                                weeks_back: int = 8,
                                markets_per_window: int = 100,
                                max_trades_per_market: int = 10000,
                                save_raw: bool = True) -> pd.DataFrame:
        """
        Collect markets across multiple time windows for better coverage.

        Args:
            weeks_back: How many weeks back to collect data
            markets_per_window: Maximum markets to collect per week
            max_trades_per_market: Max trades per market
            save_raw: Save raw JSON data

        Returns:
            DataFrame with trade data
        """
        print("=" * 60)
        print("POLYMARKET DATA COLLECTION (Time Window Sampling)")
        print(f"Weeks back: {weeks_back}, Markets per window: {markets_per_window}")
        print(f"Max trades per market: {max_trades_per_market:,}")
        print("=" * 60)

        # Phase 1: Fetch all markets
        all_markets = self._fetch_all_markets(weeks_back, markets_per_window)
        print(f"\nTotal unique markets: {len(all_markets)}")

        if save_raw:
            with open(self.output_dir / 'raw_markets.json', 'w') as f:
                json.dump(all_markets, f, indent=2)

        # Phase 2: Collect trades for each market
        all_trade_data, stats = self._collect_trades_for_markets(
            all_markets, max_trades_per_market, save_progress=True)

        # Phase 3: Save final dataset
        df = pd.DataFrame(all_trade_data)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.output_dir / f'polymarket_trades_{timestamp}.csv'
        df.to_csv(output_file, index=False)

        self._print_summary(
            df, len(all_markets),
            stats['markets_with_trades'],
            stats['markets_skipped_no_resolution'],
            stats['markets_skipped_no_trades'],
            output_file
        )

        # Show time distribution
        if len(df) > 0:
            df['trade_week'] = df['trade_timestamp'].dt.to_period('W')
            print(f"\nTrades by week:")
            print(df['trade_week'].value_counts().sort_index().tail(10))
            print("=" * 60)

        return df


def main():
    """Example usage"""
    collector = PolymarketSampledCollector(output_dir="polymarket_data")

    df = collector.collect_by_time_windows(
        weeks_back=20,
        markets_per_window=1000,
        max_trades_per_market=1000,
        save_raw=True
    )

    if len(df) > 0:
        print("\nDataset Summary:")
        print(f"Total trades: {len(df)}")
        print(f"Unique markets: {df['condition_id'].nunique()}")
        print(f"Date range: {df['trade_timestamp'].min()} to {df['trade_timestamp'].max()}")


if __name__ == "__main__":
    main()
