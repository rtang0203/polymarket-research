import pandas as pd

# Load full dataset
df = pd.read_csv('polymarket_data/polymarket_trades_combined_20251230.csv')

# Sample 1500 markets, keep all their trades
sampled_markets = df['condition_id'].drop_duplicates().sample(n=1500, random_state=42)
df_sample = df[df['condition_id'].isin(sampled_markets)]

# Check size
print(f"Sampled {df_sample['condition_id'].nunique()} markets")
print(f"Total trades: {len(df_sample):,}")
print(f"Estimated size: ~{len(df_sample) / len(df) * 1.06:.2f} GB")

# Save
df_sample.to_csv('polymarket_trades_sample.csv', index=False)