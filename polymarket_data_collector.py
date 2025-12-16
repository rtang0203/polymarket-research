"""
Polymarket Data Collector
Collects historical market and trade data for win-rate analysis
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
    Collector for Polymarket market and trade data
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
        """Simple rate limiting to avoid hitting API limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a GET request with error handling"""
        self._rate_limit()
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def get_markets(self,
                   closed: Optional[bool] = None,
                   limit: int = 100,
                   offset: int = 0,
                   **filters) -> List[Dict]:
        """
        Fetch markets from Gamma API

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
            'order': 'volume',  # Order by volume to get active markets
            'ascending': 'false',  # Descending - highest volume first
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
        Fetch all markets with pagination

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

            # Check if we've hit the limit or got fewer results than requested
            if max_markets and len(all_markets) >= max_markets:
                all_markets = all_markets[:max_markets]
                break

            if len(markets) < limit:
                break

            offset += limit
            time.sleep(0.5)  # Be nice to the API

        print(f"Total markets fetched: {len(all_markets)}")
        return all_markets

    def get_all_trades_for_market(self, condition_id: str, max_trades: Optional[int] = None) -> tuple[List[Dict], bool]:
        """
        Fetch trades for a specific market

        Args:
            condition_id: Market's conditionId
            max_trades: Maximum trades to fetch (None for unlimited)

        Returns:
            Tuple of (list of trades, was_truncated)
        """
        all_trades = []
        before = None
        truncated = False

        while True:
            params = {'market': condition_id, 'limit': 100}
            if before:
                params['before'] = before

            url = f"{self.data_api_url}/trades"
            trades = self._make_request(url, params)

            if not trades:
                break

            all_trades.extend(trades)

            # Check if we've hit the max trades limit
            if max_trades and len(all_trades) >= max_trades:
                all_trades = all_trades[:max_trades]
                truncated = True
                break

            if len(trades) < 100:
                break

            # Use the timestamp of the last trade for pagination
            before = trades[-1]['timestamp']
            time.sleep(0.2)

        return all_trades, truncated

    def process_market_for_analysis(self, market: Dict) -> Optional[Dict]:
        """
        Extract relevant information from a market for analysis

        Args:
            market: Market dictionary from Gamma API

        Returns:
            Processed market dictionary with key fields
        """
        # Only process closed markets
        if not market.get('closed', False):
            return None

        # Parse outcomes and prices (they're JSON strings)
        try:
            outcomes = json.loads(market.get('outcomes', '[]'))
            outcome_prices = json.loads(market.get('outcomePrices', '[]'))
        except (json.JSONDecodeError, TypeError):
            return None

        if not outcomes or not outcome_prices:
            return None

        # Find winning outcome (price = "1" or close to 1)
        winning_outcome = None
        tokens = {}
        for i, (outcome, price) in enumerate(zip(outcomes, outcome_prices)):
            try:
                price_float = float(price)
            except (ValueError, TypeError):
                price_float = 0

            is_winner = price_float > 0.99  # Winner has price ~1
            tokens[outcome] = {
                'index': i,
                'winner': is_winner,
            }
            if is_winner:
                winning_outcome = outcome

        if winning_outcome is None:
            return None  # Not properly resolved

        # Extract key fields (note: API uses camelCase)
        processed = {
            'condition_id': market.get('conditionId'),
            'question': market.get('question'),
            'category': market.get('category'),
            'created_at': market.get('createdAt'),
            'end_date': market.get('endDate'),
            'resolved_at': market.get('closedTime'),
            'winning_outcome': winning_outcome,
            'volume': market.get('volumeNum', 0),
            'liquidity': market.get('liquidityNum', 0),
            'tokens': tokens
        }

        return processed

    def collect_dataset(self,
                       num_markets: int = 1000,
                       max_trades_per_market: int = 10000,
                       category: Optional[str] = None,
                       save_raw: bool = True) -> pd.DataFrame:
        """
        Collect a full dataset for analysis

        Args:
            num_markets: Number of markets to collect
            max_trades_per_market: Max trades to collect per market (prevents huge markets from stalling)
            category: Filter by category (e.g., 'politics', 'sports', 'crypto')
            save_raw: Whether to save raw JSON data

        Returns:
            DataFrame with trade data ready for analysis
        """
        print("=" * 60)
        print("POLYMARKET DATA COLLECTION")
        print(f"Max trades per market: {max_trades_per_market:,}")
        print("=" * 60)

        # Step 1: Get resolved markets
        filters = {}
        if category:
            filters['tag'] = category

        markets = self.get_all_markets(
            closed=True,
            max_markets=num_markets,
            **filters
        )

        if save_raw:
            with open(self.output_dir / 'raw_markets.json', 'w') as f:
                json.dump(markets, f, indent=2)

        # Step 2: Process markets and collect trades
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

            condition_id = processed_market['condition_id']

            # Get trades for this market
            trades, was_truncated = self.get_all_trades_for_market(condition_id, max_trades_per_market)

            if not trades:
                markets_skipped_no_trades += 1
                print(f"  Skipped: No trades found")
                continue

            truncation_note = f" (capped at {max_trades_per_market})" if was_truncated else ""
            print(f"  Found {len(trades)} trades{truncation_note}")
            markets_with_trades += 1

            # Process each trade
            for trade in trades:
                # Get outcome from trade (the API provides it directly)
                outcome = trade.get('outcome')
                if not outcome:
                    continue

                # Calculate time to resolution
                trade_timestamp = trade.get('timestamp')
                time_to_resolution = None
                trade_time = None

                if trade_timestamp:
                    trade_time = datetime.fromtimestamp(trade_timestamp, tz=timezone.utc)

                    if processed_market['resolved_at']:
                        try:
                            resolved_str = processed_market['resolved_at']
                            # Handle various timestamp formats
                            if '+' in resolved_str or 'Z' in resolved_str:
                                resolved_str = resolved_str.replace('Z', '+00:00')
                                if resolved_str.endswith('+00'):
                                    resolved_str = resolved_str + ':00'
                            resolved_time = datetime.fromisoformat(resolved_str)
                            if resolved_time.tzinfo is None:
                                resolved_time = resolved_time.replace(tzinfo=timezone.utc)
                            time_to_resolution = (resolved_time - trade_time).total_seconds()
                        except Exception:
                            pass

                # Did this outcome win?
                won = processed_market['tokens'].get(outcome, {}).get('winner', False)

                trade_data = {
                    'condition_id': condition_id,
                    'question': processed_market['question'],
                    'category': processed_market['category'],
                    'trade_timestamp': trade_time,
                    'resolved_at': processed_market['resolved_at'],
                    'time_to_resolution_hours': time_to_resolution / 3600 if time_to_resolution else None,
                    'price': trade.get('price'),
                    'size': trade.get('size'),
                    'side': trade.get('side'),  # BUY or SELL
                    'outcome': outcome,  # Yes or No
                    'won': won,
                    'volume_total': processed_market['volume'],
                }

                all_trade_data.append(trade_data)

            # Save progress periodically
            if (i + 1) % 50 == 0:
                temp_df = pd.DataFrame(all_trade_data)
                temp_df.to_csv(self.output_dir / f'trades_progress_{i+1}.csv', index=False)
                print(f"\n  Progress saved: {len(all_trade_data)} trades from {markets_with_trades} markets")

        # Create final DataFrame
        df = pd.DataFrame(all_trade_data)

        # Save complete dataset
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.output_dir / f'polymarket_trades_{timestamp}.csv'
        df.to_csv(output_file, index=False)

        print(f"\n{'='*60}")
        print(f"Data collection complete!")
        print(f"Markets processed: {len(markets)}")
        print(f"  - With trades: {markets_with_trades}")
        print(f"  - Skipped (no resolution): {markets_skipped_no_resolution}")
        print(f"  - Skipped (no trades): {markets_skipped_no_trades}")
        print(f"Total trades collected: {len(df)}")
        print(f"Saved to: {output_file}")

        # Show trades-per-market distribution
        if len(df) > 0:
            trades_per_market = df.groupby('condition_id').size()
            print(f"\nTrades per market distribution:")
            print(f"  Min: {trades_per_market.min()}, Max: {trades_per_market.max()}, Median: {trades_per_market.median():.0f}")
            print(f"  Markets with <10 trades:  {(trades_per_market < 10).sum()}")
            print(f"  Markets with <50 trades:  {(trades_per_market < 50).sum()}")
            print(f"  Markets with <100 trades: {(trades_per_market < 100).sum()}")
            print(f"  Markets with 100+ trades: {(trades_per_market >= 100).sum()}")

        print(f"{'='*60}")

        return df


def main():
    """Example usage"""
    output_directory = "polymarket_data"
    collector = PolymarketDataCollector(output_dir=output_directory)

    # Collect data for 500 resolved markets (ordered by volume)
    df = collector.collect_dataset(
        num_markets=500,
        max_trades_per_market=10000,  # Cap trades per market to avoid huge markets stalling
        category=None,  # Set to 'politics', 'sports', 'crypto', etc. to filter
        save_raw=True
    )

    if len(df) > 0:
        # Quick summary
        print("\nDataset Summary:")
        print(f"Total trades: {len(df)}")
        print(f"Unique markets: {df['condition_id'].nunique()}")
        print(f"Date range: {df['trade_timestamp'].min()} to {df['trade_timestamp'].max()}")
        print(f"\nCategories:")
        print(df['category'].value_counts())
        print(f"\nOutcomes:")
        print(df['outcome'].value_counts())
        print(f"\nWin rate:")
        print(df['won'].value_counts(normalize=True))
    else:
        print("\nNo trades collected. Check API responses.")


if __name__ == "__main__":
    main()
