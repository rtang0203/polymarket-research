# Polymarket Win Rate Analysis

Analyzing calibration and systematic mispricing in Polymarket prediction markets.

## Quick Start

```bash
# Install dependencies
pip install pandas numpy matplotlib seaborn scipy requests

# Collect data (time-window sampling recommended)
python3 polymarket_sampled_collector.py

# Run analysis
jupyter notebook analysis.ipynb
```

## Data Collection

### Time-Window Collection (Recommended)

```python
from polymarket_sampled_collector import PolymarketSampledCollector

collector = PolymarketSampledCollector(output_dir="polymarket_data")
df = collector.collect_by_time_windows(
    weeks_back=8,               # How many weeks to look back
    markets_per_window=500,     # Markets per week (uses pagination)
    max_trades_per_market=2000, # 1000-2000 recommended
    save_raw=True
)
```

### Simple Collection

```python
from polymarket_data_collector import PolymarketDataCollector

collector = PolymarketDataCollector(output_dir="polymarket_data")
df = collector.collect_dataset(
    num_markets=500,
    max_trades_per_market=2000
)
```

Output: `polymarket_data/polymarket_trades_YYYYMMDD_HHMMSS.csv`

## Analysis

The Jupyter notebook (`analysis.ipynb`) performs:

- **Calibration Analysis**: Win rate vs price paid (are 60¢ contracts winning 60%?)
- **YES vs NO Comparison**: Do YES and NO contracts behave differently?
- **Time Stratification**: Calibration by time-to-resolution (0-24h through 3+ months)
- **Category Analysis**: By market type (politics, sports, crypto, etc.)
- **Weighted vs Unweighted**: Market-weighted analysis to prevent large markets from dominating

## Data Schema

| Column | Description |
|--------|-------------|
| `condition_id` | Market identifier |
| `question` | Market question |
| `category` | Market category |
| `trade_timestamp` | When trade occurred |
| `price` | Price paid (0-1, where 0.65 = 65¢) |
| `size` | Trade size in dollars |
| `side` | BUY or SELL |
| `outcome` | Which outcome traded (Yes/No) |
| `won` | Did this outcome win? |
| `time_to_resolution_hours` | Hours between trade and resolution |

## Interpreting Results

**Perfect calibration**: Win rate = price paid (diagonal line)
- **Above diagonal**: Underpriced (positive edge)
- **Below diagonal**: Overpriced (negative edge)

Example: 60¢ contracts winning 65% → +5¢ edge

## Utilities

```bash
# Combine multiple CSV files and remove duplicates
python3 combine_csvs.py
```

## API Notes

- **Gamma API**: Market metadata (`/markets`)
- **Data API**: Trade history (`/trades`)
- Both use `offset` pagination (not `before` - it's broken)
- Rate limiting: ~100ms between requests

## See Also

- `CLAUDE.md` - Technical documentation
- `FUTURE_ANALYSES.md` - Planned investigations

## Disclaimer

For research and educational purposes only. Trading involves risk.
