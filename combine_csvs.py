#!/usr/bin/env python3
"""
Combine all polymarket trade CSVs and remove duplicates.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def combine_csvs(data_dir: str = "polymarket_data", output_name: str = None):
    """
    Combine all polymarket_trades_*.csv files and remove duplicates.

    Args:
        data_dir: Directory containing the CSV files
        output_name: Output filename (default: polymarket_trades_combined_YYYYMMDD.csv)
    """
    data_path = Path(data_dir)
    csv_files = sorted(data_path.glob("polymarket_trades_*.csv"))

    if not csv_files:
        print("No CSV files found!")
        return None

    print(f"Found {len(csv_files)} CSV files:")
    for f in csv_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name} ({size_mb:.1f} MB)")

    # Read and combine all CSVs
    print(f"\nReading files...")
    dfs = []
    for f in csv_files:
        print(f"  Loading {f.name}...")
        df = pd.read_csv(f)
        df['source_file'] = f.name  # Track source for debugging
        dfs.append(df)
        print(f"    {len(df):,} rows")

    combined = pd.concat(dfs, ignore_index=True)
    print(f"\nTotal rows before dedup: {len(combined):,}")

    # Define columns that uniquely identify a trade
    # A trade is unique by: market, timestamp, price, size, side, outcome
    dedup_cols = ['condition_id', 'trade_timestamp', 'price', 'size', 'side', 'outcome']

    # Check for duplicates
    n_dupes = combined.duplicated(subset=dedup_cols).sum()
    print(f"Duplicate rows found: {n_dupes:,}")

    # Remove duplicates (keep first occurrence)
    combined_deduped = combined.drop_duplicates(subset=dedup_cols, keep='first')
    print(f"Total rows after dedup: {len(combined_deduped):,}")

    # Drop the source_file column (was just for debugging)
    combined_deduped = combined_deduped.drop(columns=['source_file'])

    # Sort by trade timestamp
    combined_deduped = combined_deduped.sort_values('trade_timestamp').reset_index(drop=True)

    # Generate output filename
    if output_name is None:
        timestamp = datetime.now().strftime('%Y%m%d')
        output_name = f"polymarket_trades_combined_{timestamp}.csv"

    output_path = data_path / output_name
    combined_deduped.to_csv(output_path, index=False)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nSaved to: {output_path}")
    print(f"File size: {size_mb:.1f} MB")

    # Summary stats
    print(f"\nDataset summary:")
    print(f"  Total trades: {len(combined_deduped):,}")
    print(f"  Unique markets: {combined_deduped['condition_id'].nunique():,}")
    print(f"  Date range: {combined_deduped['trade_timestamp'].min()} to {combined_deduped['trade_timestamp'].max()}")

    return combined_deduped


if __name__ == "__main__":
    combine_csvs()
