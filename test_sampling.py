"""
Test script for trade sampling functionality.
Tests the get_sampled_trades_for_market function on various market sizes.

Usage:
    python test_sampling.py                           # Run default tests
    python test_sampling.py -c <condition_id>         # Test specific market
    python test_sampling.py -c <condition_id> --all   # Compare sampled vs all trades
"""

from polymarket_sampled_collector import PolymarketSampledCollector
from datetime import datetime, timezone  # Used for displaying trade timestamps
import argparse


def test_market(collector: PolymarketSampledCollector, condition_id: str, name: str = "",
                compare_all: bool = False):
    """Test trade sampling on a specific market."""
    print(f"\n{'='*60}")
    print(f"Testing: {name or condition_id[:40]}...")
    print(f"Condition ID: {condition_id}")
    print("="*60)

    # Test sampled function
    print("\n[Sampled fetch]")
    trades, was_sampled = collector.get_sampled_trades_for_market(condition_id)
    print_trade_stats(trades, was_sampled)

    # Optionally compare with get_all_trades
    if compare_all:
        print("\n[Full fetch (for comparison)]")
        all_trades, truncated = collector.get_trades_for_market(condition_id, max_trades=10000)
        print_trade_stats(all_trades, truncated, label="truncated")

    return len(trades), was_sampled


def print_trade_stats(trades: list, flag: bool, label: str = "sampled"):
    """Print statistics about trades."""
    print(f"Result: {len(trades)} trades, {label}={flag}")

    if trades:
        timestamps = [t['timestamp'] for t in trades]
        oldest = datetime.fromtimestamp(min(timestamps), tz=timezone.utc)
        newest = datetime.fromtimestamp(max(timestamps), tz=timezone.utc)
        duration = newest - oldest

        print(f"Time range: {oldest.strftime('%Y-%m-%d %H:%M')} to {newest.strftime('%Y-%m-%d %H:%M')}")
        print(f"Duration: {duration.days} days, {duration.seconds // 3600} hours")

        # Trade price distribution
        prices = [t.get('price', 0) for t in trades]
        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            print(f"Price range: ${min_price:.2f} - ${max_price:.2f} (avg: ${avg_price:.2f})")


def main():
    parser = argparse.ArgumentParser(description="Test trade sampling functionality")
    parser.add_argument("--condition-id", "-c", type=str,
                       help="Specific condition ID to test")
    parser.add_argument("--name", "-n", type=str, default="",
                       help="Name/description for the market")
    parser.add_argument("--all", "-a", action="store_true",
                       help="Also fetch all trades for comparison")
    args = parser.parse_args()

    collector = PolymarketSampledCollector()

    # Test markets with known sizes
    test_markets = [
        # Short-duration high-volume market
        ("0x19bf3cfee2d32930a9a93cfde5db7e135488baae14c0e4c64777530064e7e550",
         "Bitcoin Up or Down (short)"),

        # Multi-day market
        ("0x4ac7d92ca529ed63b1a3f4e502c4a1da24a6f60f9f4483a16c3f85246214ed7b",
         "Biden Old Speech (multi-day)"),
    ]

    if args.condition_id:
        # Test user-specified market
        test_market(collector, args.condition_id, args.name, compare_all=args.all)
    else:
        # Run all test markets
        print("Running tests on known markets...")
        results = []
        for cid, name in test_markets:
            count, sampled = test_market(collector, cid, name, compare_all=args.all)
            results.append((name, count, sampled))

        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        for name, count, sampled in results:
            status = "sampled" if sampled else "all trades"
            print(f"  {name}: {count} trades ({status})")


if __name__ == "__main__":
    main()
