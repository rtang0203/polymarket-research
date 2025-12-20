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
        - Large markets (2000+ trades): keep newest 2000, sample from older portion

        Args:
            condition_id: Market's conditionId
            max_trades: Maximum total trades to return
            num_windows: Number of time windows to sample older trades from

        Returns:
            Tuple of (list of trades, was_sampled)
        """
        url = f"{self.data_api_url}/trades"
        batch_size = 500  # API max

        # Phase 1: Fetch first batch to assess market size
        params = {'market': condition_id, 'limit': batch_size}
        batch = self._make_request(url, params)

        if not batch:
            return [], False

        all_probed_trades = list(batch)

        if len(batch) < batch_size:
            return all_probed_trades, False

        before = batch[-1]['timestamp']

        # Phase 2: Continue fetching to 2000 trades
        while len(all_probed_trades) < 2000:
            params = {'market': condition_id, 'limit': batch_size, 'before': before}
            batch = self._make_request(url, params)
            if not batch:
                break

            all_probed_trades.extend(batch)

            if len(batch) < batch_size:
                return all_probed_trades, False

            before = batch[-1]['timestamp']
            time.sleep(0.1)

        if len(all_probed_trades) < 2000:
            return all_probed_trades, False

        # Phase 3: Large market - sample from older portion
        newest_ts = all_probed_trades[0]['timestamp']
        oldest_probed_ts = all_probed_trades[-1]['timestamp']

        # Probe backward to find time range
        oldest_ts = oldest_probed_ts
        probe_count = 0

        while probe_count < 5:
            batch = self._make_request(url, {'market': condition_id, 'limit': batch_size, 'before': oldest_ts})
            if not batch:
                break
            oldest_ts = batch[-1]['timestamp']
            if len(batch) < batch_size:
                break
            probe_count += 1
            time.sleep(0.1)

        # Check if time span is too short to bother sampling
        time_range = newest_ts - oldest_ts
        if time_range < 3600:
            return all_probed_trades[:max_trades], True

        older_time_range = oldest_probed_ts - oldest_ts
        if older_time_range < 3600:
            return all_probed_trades[:max_trades], True

        # Sample from older portion
        remaining_budget = max_trades - len(all_probed_trades)
        if remaining_budget <= 0:
            return all_probed_trades[:max_trades], True

        older_windows = min(num_windows, 5)
        window_size = older_time_range / older_windows
        trades_per_window = remaining_budget // older_windows

        seen_ids = {t.get('transactionHash', str(t['timestamp'])) for t in all_probed_trades}
        older_trades = []

        for i in range(older_windows):
            window_start = oldest_ts + (i * window_size)
            window_end = oldest_ts + ((i + 1) * window_size)

            params = {
                'market': condition_id,
                'limit': batch_size,
                'before': int(window_end) + 1
            }

            window_trades = []
            attempts = 0

            while len(window_trades) < trades_per_window and attempts < 3:
                trades = self._make_request(url, params)
                if not trades:
                    break

                for t in trades:
                    ts = t['timestamp']
                    tx_hash = t.get('transactionHash', str(ts))

                    if ts >= window_start and ts < window_end and tx_hash not in seen_ids:
                        window_trades.append(t)
                        seen_ids.add(tx_hash)
                        if len(window_trades) >= trades_per_window:
                            break

                if len(trades) < batch_size or trades[-1]['timestamp'] < window_start:
                    break

                params['before'] = trades[-1]['timestamp']
                attempts += 1
                time.sleep(0.1)

            older_trades.extend(window_trades)

        combined = all_probed_trades + older_trades
        combined.sort(key=lambda x: x['timestamp'])
        return combined[:max_trades], True

    def collect_by_time_windows(self,
                                weeks_back: int = 8,
                                markets_per_window: int = 100,
                                max_trades_per_market: int = 10000,
                                save_raw: bool = True) -> pd.DataFrame:
        """
        Collect markets across multiple time windows for better coverage.

        Args:
            weeks_back: How many weeks back to collect data
            markets_per_window: Number of markets to collect per week
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

        all_markets = []
        now = datetime.now(timezone.utc)

        # Collect markets from each weekly window
        for week in range(weeks_back):
            end_date = now - timedelta(weeks=week)
            start_date = end_date - timedelta(weeks=1)

            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')

            print(f"\nFetching markets from {start_str} to {end_str}...")

            params = {
                'closed': 'true',
                'limit': markets_per_window,
                'order': 'volume',
                'ascending': 'false',
                'end_date_min': start_str,
                'end_date_max': end_str,
            }

            url = f"{self.gamma_url}/markets"
            markets = self._make_request(url, params)

            if markets:
                print(f"  Found {len(markets)} markets")
                all_markets.extend(markets)
            else:
                print(f"  No markets found")

            time.sleep(0.5)

        print(f"\nTotal markets fetched: {len(all_markets)}")

        if save_raw:
            with open(self.output_dir / 'raw_markets.json', 'w') as f:
                json.dump(all_markets, f, indent=2)

        # Process markets and collect trades
        all_trade_data = []
        markets_with_trades = 0
        markets_skipped_no_resolution = 0
        markets_skipped_no_trades = 0

        for i, market in enumerate(all_markets):
            question = market.get('question', 'Unknown')[:60]
            print(f"\nProcessing market {i+1}/{len(all_markets)}: {question}...")

            processed_market = self.process_market_for_analysis(market)
            if not processed_market:
                markets_skipped_no_resolution += 1
                print(f"  Skipped: No valid resolution data")
                continue

            trades, was_sampled = self.get_sampled_trades_for_market(
                processed_market['condition_id'], max_trades_per_market
            )
            sample_note = " (sampled)" if was_sampled else ""

            if not trades:
                markets_skipped_no_trades += 1
                print(f"  Skipped: No trades found")
                continue

            print(f"  Found {len(trades)} trades{sample_note}")
            markets_with_trades += 1

            all_trade_data.extend(self._process_trades(trades, processed_market))

            if (i + 1) % 50 == 0:
                temp_df = pd.DataFrame(all_trade_data)
                temp_df.to_csv(self.output_dir / f'trades_progress_{i+1}.csv', index=False)
                print(f"\n  Progress saved: {len(all_trade_data)} trades from {markets_with_trades} markets")

        # Save final dataset
        df = pd.DataFrame(all_trade_data)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.output_dir / f'polymarket_trades_{timestamp}.csv'
        df.to_csv(output_file, index=False)

        self._print_summary(df, len(all_markets), markets_with_trades,
                           markets_skipped_no_resolution, markets_skipped_no_trades, output_file)

        # Additional: show time distribution
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
        weeks_back=8,
        markets_per_window=100,
        max_trades_per_market=10000,
        save_raw=True
    )

    if len(df) > 0:
        print("\nDataset Summary:")
        print(f"Total trades: {len(df)}")
        print(f"Unique markets: {df['condition_id'].nunique()}")
        print(f"Date range: {df['trade_timestamp'].min()} to {df['trade_timestamp'].max()}")


if __name__ == "__main__":
    main()
