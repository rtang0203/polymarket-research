"""
Polymarket Data Collector (Simple)
Collects historical market and trade data for win-rate analysis.
Fetches most recent resolved markets ordered by volume.
"""

import requests
import pandas as pd
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional
import json
from pathlib import Path


class PolymarketDataCollector:
    """
    Simple collector for Polymarket market and trade data.
    Fetches most recent resolved markets ordered by volume.
    """

    def __init__(self, output_dir: str = "polymarket_data"):
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.data_api_url = "https://data-api.polymarket.com"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests

    def _rate_limit(self):
        """Simple rate limiting to avoid hitting API limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a GET request with error handling."""
        self._rate_limit()
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def _parse_market_times(self, processed_market: Dict) -> tuple[Optional[datetime], Optional[datetime]]:
        """Parse start and end times from processed market data."""
        start_time = None
        end_time = None

        try:
            start_str = processed_market.get('created_at')
            end_str = processed_market.get('resolved_at')

            if start_str:
                start_str = start_str.replace('Z', '+00:00')
                if start_str.endswith('+00'):
                    start_str = start_str + ':00'
                start_time = datetime.fromisoformat(start_str)
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)

            if end_str:
                end_str = end_str.replace('Z', '+00:00')
                if end_str.endswith('+00'):
                    end_str = end_str + ':00'
                end_time = datetime.fromisoformat(end_str)
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
        except Exception:
            pass

        return start_time, end_time

    def get_markets(self,
                    closed: Optional[bool] = None,
                    limit: int = 100,
                    offset: int = 0,
                    **filters) -> List[Dict]:
        """
        Fetch markets from Gamma API.

        Args:
            closed: Filter by closed/open markets (True/False/None for all)
            limit: Number of markets to fetch per request
            offset: Pagination offset
            **filters: Additional filters (e.g., tag='politics')

        Returns:
            List of market dictionaries
        """
        params = {
            'limit': limit,
            'offset': offset,
            'order': 'volume',
            'ascending': 'false',
            **filters
        }

        if closed is not None:
            params['closed'] = str(closed).lower()

        url = f"{self.gamma_url}/markets"
        data = self._make_request(url, params)

        return data if data else []

    def get_all_markets(self,
                        closed: bool = True,
                        max_markets: Optional[int] = None,
                        **filters) -> List[Dict]:
        """
        Fetch all markets with pagination.

        Args:
            closed: Only get closed markets (True) or open markets (False)
            max_markets: Maximum number of markets to fetch (None for all)
            **filters: Additional filters

        Returns:
            List of all market dictionaries
        """
        all_markets = []
        offset = 0
        limit = 100

        print(f"Fetching {'closed' if closed else 'open'} markets...")

        while True:
            markets = self.get_markets(
                closed=closed,
                limit=limit,
                offset=offset,
                **filters
            )

            if not markets:
                break

            all_markets.extend(markets)
            print(f"Fetched {len(all_markets)} markets so far...")

            if max_markets and len(all_markets) >= max_markets:
                all_markets = all_markets[:max_markets]
                break

            if len(markets) < limit:
                break

            offset += limit
            time.sleep(0.5)

        print(f"Total markets fetched: {len(all_markets)}")
        return all_markets

    def get_trades_for_market(self, condition_id: str, max_trades: Optional[int] = None) -> tuple[List[Dict], bool]:
        """
        Fetch trades for a specific market.

        Args:
            condition_id: Market's conditionId
            max_trades: Maximum trades to fetch (None for unlimited)

        Returns:
            Tuple of (list of trades, was_truncated)
        """
        all_trades = []
        offset = 0
        truncated = False
        batch_size = 500  # API max

        while True:
            params = {'market': condition_id, 'limit': batch_size, 'offset': offset}

            url = f"{self.data_api_url}/trades"
            trades = self._make_request(url, params)

            if not trades:
                break

            all_trades.extend(trades)

            if max_trades and len(all_trades) >= max_trades:
                all_trades = all_trades[:max_trades]
                truncated = True
                break

            if len(trades) < batch_size:
                break

            offset += batch_size
            time.sleep(0.2)

        return all_trades, truncated

    def process_market_for_analysis(self, market: Dict) -> Optional[Dict]:
        """
        Extract relevant information from a market for analysis.

        Args:
            market: Market dictionary from Gamma API

        Returns:
            Processed market dictionary with key fields
        """
        if not market.get('closed', False):
            return None

        try:
            outcomes = json.loads(market.get('outcomes', '[]'))
            outcome_prices = json.loads(market.get('outcomePrices', '[]'))
        except (json.JSONDecodeError, TypeError):
            return None

        if not outcomes or not outcome_prices:
            return None

        winning_outcome = None
        tokens = {}
        for i, (outcome, price) in enumerate(zip(outcomes, outcome_prices)):
            try:
                price_float = float(price)
            except (ValueError, TypeError):
                price_float = 0

            is_winner = price_float > 0.99
            tokens[outcome] = {
                'index': i,
                'winner': is_winner,
            }
            if is_winner:
                winning_outcome = outcome

        if winning_outcome is None:
            return None

        category = market.get('category') or ''
        if not category:
            events = market.get('events', [])
            if events and isinstance(events, list) and len(events) > 0:
                category = events[0].get('category') or ''
        category = str(category) if category else ''

        return {
            'condition_id': market.get('conditionId'),
            'question': market.get('question'),
            'category': category,
            'created_at': market.get('createdAt'),
            'end_date': market.get('endDate'),
            'resolved_at': market.get('closedTime'),
            'winning_outcome': winning_outcome,
            'volume': market.get('volumeNum', 0),
            'liquidity': market.get('liquidityNum', 0),
            'tokens': tokens
        }

    def _process_trades(self, trades: List[Dict], processed_market: Dict) -> List[Dict]:
        """Convert raw trades to analysis-ready format."""
        condition_id = processed_market['condition_id']
        _, resolved_time = self._parse_market_times(processed_market)

        trade_data = []
        for trade in trades:
            outcome = trade.get('outcome')
            if not outcome:
                continue

            trade_timestamp = trade.get('timestamp')
            time_to_resolution = None
            trade_time = None

            if trade_timestamp:
                trade_time = datetime.fromtimestamp(trade_timestamp, tz=timezone.utc)
                if resolved_time:
                    time_to_resolution = (resolved_time - trade_time).total_seconds()

            won = processed_market['tokens'].get(outcome, {}).get('winner', False)

            trade_data.append({
                'condition_id': condition_id,
                'question': processed_market['question'],
                'category': processed_market['category'],
                'trade_timestamp': trade_time,
                'resolved_at': processed_market['resolved_at'],
                'time_to_resolution_hours': time_to_resolution / 3600 if time_to_resolution else None,
                'price': trade.get('price'),
                'size': trade.get('size'),
                'side': trade.get('side'),
                'outcome': outcome,
                'won': won,
                'volume_total': processed_market['volume'],
            })

        return trade_data

    def _print_summary(self, df: pd.DataFrame, markets_processed: int,
                       markets_with_trades: int, markets_skipped_no_resolution: int,
                       markets_skipped_no_trades: int, output_file: Path):
        """Print collection summary."""
        print(f"\n{'='*60}")
        print(f"Data collection complete!")
        print(f"Markets processed: {markets_processed}")
        print(f"  - With trades: {markets_with_trades}")
        print(f"  - Skipped (no resolution): {markets_skipped_no_resolution}")
        print(f"  - Skipped (no trades): {markets_skipped_no_trades}")
        print(f"Total trades collected: {len(df)}")
        print(f"Saved to: {output_file}")

        if len(df) > 0:
            trades_per_market = df.groupby('condition_id').size()
            print(f"\nTrades per market distribution:")
            print(f"  Min: {trades_per_market.min()}, Max: {trades_per_market.max()}, Median: {trades_per_market.median():.0f}")
            print(f"  Markets with <10 trades:  {(trades_per_market < 10).sum()}")
            print(f"  Markets with <50 trades:  {(trades_per_market < 50).sum()}")
            print(f"  Markets with <100 trades: {(trades_per_market < 100).sum()}")
            print(f"  Markets with 100+ trades: {(trades_per_market >= 100).sum()}")

        print(f"{'='*60}")

    def collect_dataset(self,
                        num_markets: int = 1000,
                        max_trades_per_market: int = 10000,
                        category: Optional[str] = None,
                        save_raw: bool = True) -> pd.DataFrame:
        """
        Collect a dataset from the most recent resolved markets (by volume).

        Args:
            num_markets: Number of markets to collect
            max_trades_per_market: Max trades to collect per market
            category: Filter by category (e.g., 'politics', 'sports', 'crypto')
            save_raw: Whether to save raw JSON data

        Returns:
            DataFrame with trade data ready for analysis
        """
        print("=" * 60)
        print("POLYMARKET DATA COLLECTION (Simple)")
        print(f"Markets: {num_markets}, Max trades per market: {max_trades_per_market:,}")
        print("=" * 60)

        # Get resolved markets
        filters = {}
        if category:
            filters['tag'] = category

        markets = self.get_all_markets(closed=True, max_markets=num_markets, **filters)

        if save_raw:
            with open(self.output_dir / 'raw_markets.json', 'w') as f:
                json.dump(markets, f, indent=2)

        # Process markets and collect trades
        all_trade_data = []
        markets_with_trades = 0
        markets_skipped_no_resolution = 0
        markets_skipped_no_trades = 0

        for i, market in enumerate(markets):
            question = market.get('question', 'Unknown')[:60]
            print(f"\nProcessing market {i+1}/{len(markets)}: {question}...")

            processed_market = self.process_market_for_analysis(market)
            if not processed_market:
                markets_skipped_no_resolution += 1
                print(f"  Skipped: No valid resolution data")
                continue

            trades, was_truncated = self.get_trades_for_market(
                processed_market['condition_id'], max_trades_per_market
            )

            if not trades:
                markets_skipped_no_trades += 1
                print(f"  Skipped: No trades found")
                continue

            truncation_note = f" (capped at {max_trades_per_market})" if was_truncated else ""
            print(f"  Found {len(trades)} trades{truncation_note}")
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

        self._print_summary(df, len(markets), markets_with_trades,
                           markets_skipped_no_resolution, markets_skipped_no_trades, output_file)

        return df


def main():
    """Example usage"""
    collector = PolymarketDataCollector(output_dir="polymarket_data")

    df = collector.collect_dataset(
        num_markets=500,
        max_trades_per_market=10000,
        category=None,
        save_raw=True
    )

    if len(df) > 0:
        print("\nDataset Summary:")
        print(f"Total trades: {len(df)}")
        print(f"Unique markets: {df['condition_id'].nunique()}")
        print(f"Date range: {df['trade_timestamp'].min()} to {df['trade_timestamp'].max()}")


if __name__ == "__main__":
    main()
