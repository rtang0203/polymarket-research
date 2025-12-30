# Polymarket Win Rate Analysis

Project analyzing calibration and systematic mispricing in Polymarket prediction markets.

## Project Structure

```
polymarket_data_collector.py    # Base collector class
polymarket_sampled_collector.py # Extended collector with time-window sampling
analysis.ipynb                  # Main analysis notebook
combine_csvs.py                 # Utility to combine/dedupe CSV files
polymarket_data/                # Output directory for collected data
```

## Data Collection

### PolymarketDataCollector (base class)
- Fetches resolved markets from Gamma API
- Collects trades from Data API using offset pagination
- `collect_dataset()` - simple collection of recent markets by volume

### PolymarketSampledCollector (extends base)
- `collect_by_time_windows()` - main collection method
- Fetches markets across multiple weekly windows with pagination
- Deduplicates markets by condition_id
- `get_sampled_trades_for_market()` - samples from large markets

**Key parameters:**
- `weeks_back`: Number of weeks to collect
- `markets_per_window`: Max markets per weekly window (uses pagination)
- `max_trades_per_market`: Trade limit per market (1000-2000 recommended)

## Analysis (analysis.ipynb)

### Market-Weighted Calibration
- Inverse weights trades by market size to prevent large markets from dominating
- `weight_cap=100`: Markets with 100+ trades contribute equally, smaller markets downweighted
- Addresses variance problem in small markets

### Analyses Performed
- **Main Calibration**: Win rate vs price (weighted and unweighted comparison)
- **YES vs NO**: Separate calibration curves for each contract type
- **Time to Resolution**: Stratified by 0-24h, 1-3d, 3-7d, 1-4w, 1-3m, 3m+
- **Category Analysis**: By market category (politics, sports, crypto, etc.)

### Statistical Methods
- Wilson confidence intervals (proper for proportions)
- Minimum sample size filters (30-50 trades per bucket)
- Mean absolute calibration error metric

## Data Schema

CSV columns:
- `condition_id`: Market identifier
- `question`, `category`: Market metadata
- `trade_timestamp`, `resolved_at`: Timestamps
- `time_to_resolution_hours`: Derived field
- `price`: 0-1 (0.65 = 65¢)
- `size`: Trade size in dollars
- `side`: BUY or SELL
- `outcome`: Which outcome traded (Yes/No)
- `won`: Boolean - did this outcome win?
- `volume_total`: Total market volume

## APIs Used

- **Gamma API**: `https://gamma-api.polymarket.com/markets` (market metadata)
- **Data API**: `https://data-api.polymarket.com/trades` (trade history)

Both use `offset` parameter for pagination. The `before` timestamp parameter is broken.

## Notes

- Analysis focuses on BUY trades ("Did what I bought win?")
- SELL trades collected but not currently analyzed
- See FUTURE_ANALYSES.md for planned investigations

## TODO:
- refactor code, clean it up
- collect more data