# Polymarket Win Rate Analysis

Analysis of win rates vs purchase prices on Polymarket to identify systematic mispricing.

## Overview

This project collects historical trade data from Polymarket and analyzes whether contracts at certain prices are systematically over/undervalued.

## Installation

```bash
pip install pandas numpy matplotlib seaborn scipy requests
```

## Usage

### 1. Collect Data

Two collection methods are available:

#### Option A: Simple Collection (Most Recent Markets)

```bash
python3 polymarket_data_collector.py
```

This fetches the most recent resolved markets ordered by volume. Fast but biased toward recent data.

```python
from polymarket_data_collector import PolymarketDataCollector

collector = PolymarketDataCollector(output_dir="polymarket_data")
df = collector.collect_dataset(
    num_markets=500,           # Number of markets to collect
    max_trades_per_market=10000,
    category=None,             # 'politics', 'sports', 'crypto', etc.
    save_raw=True
)
```

#### Option B: Time-Window Collection (Recommended)

```bash
python3 polymarket_sampled_collector.py
```

This collects markets across multiple weeks for better time coverage, and samples trades from large markets.

```python
from polymarket_sampled_collector import PolymarketSampledCollector

collector = PolymarketSampledCollector(output_dir="polymarket_data")
df = collector.collect_by_time_windows(
    weeks_back=8,              # How many weeks to go back
    markets_per_window=100,    # Markets per week (800 total)
    max_trades_per_market=10000,
    save_raw=True
)
```

**Trade Fetching Behavior:**
- Markets with <2000 trades: ALL trades are fetched
- Markets with 2000+ trades: keep newest 2000, sample from older portion if applicable
- API fetches 500 trades per request (max allowed)

**Output:** Data saved to `polymarket_data/polymarket_trades_YYYYMMDD_HHMMSS.csv`

### 2. Analyze Data

```bash
python3 polymarket_analyzer.py
```

This will:
- Load the most recent dataset
- Generate win rate vs price plots
- Analyze by time-to-resolution
- Analyze by market category
- Calculate calibration statistics

## Data Structure

The collected CSV contains:
- `condition_id`: Market identifier
- `question`: Market question
- `category`: Market category (politics, sports, etc.)
- `trade_timestamp`: When the trade occurred
- `resolved_at`: When the market resolved
- `time_to_resolution_hours`: Hours between trade and resolution
- `price`: Price paid (0-1, where 0.65 = 65¢)
- `size`: Trade size in dollars
- `side`: BUY or SELL
- `outcome`: Which outcome was traded (Yes/No)
- `won`: Boolean - did this outcome win?
- `volume_total`: Total market volume

## Key Methodological Considerations

### What This Analysis Captures

1. **Calibration**: Are markets well-calibrated? (Do 60¢ contracts win 60% of the time?)
2. **Systematic mispricing**: Are certain price ranges consistently over/undervalued?
3. **Time effects**: Do prices become more accurate closer to resolution?
4. **Category effects**: Are some market types less efficient than others?

### What This Analysis Misses

#### 1. **Selection Bias in Trades**
- You're only seeing executed trades, not limit orders that never filled
- High liquidity might indicate strong disagreement vs consensus
- Missing data on rejected/canceled orders

#### 2. **Information Asymmetry Over Time**
- A contract at 60¢ three months out is very different from 60¢ one day out
- Later trades have more information → should be more accurate
- **Solution**: Stratify by `time_to_resolution`

#### 3. **Market Microstructure**
- Bid-ask spreads vary by liquidity
- Thin markets can have misleading prices
- Large trades can move markets temporarily
- **Recommendation**: Filter by minimum volume or trade size

#### 4. **Correlated Outcomes**
- Multiple markets can be linked (e.g., election markets)
- Single news events can resolve many markets simultaneously
- Not all data points are independent
- **Impact**: Confidence intervals may be overstated

#### 5. **YES vs NO Asymmetry**
Current implementation only looks at BUY trades. In theory, buying NO at 40¢ should be equivalent to buying YES at 60¢, but in practice:
- Liquidity might differ between sides
- Psychological biases might favor YES or NO
- **Recommendation**: Analyze separately and compare

#### 6. **Survivorship Bias**
- Only resolved markets are included
- Markets that never resolved or were invalidated are excluded
- Very long-dated markets might have different characteristics

#### 7. **Sample Size at Extremes**
- Fewer trades occur at 5¢ and 95¢ than at 50¢
- Small sample sizes → wide confidence intervals
- **Current handling**: Minimum sample size filter (default: 30 trades per bucket)

#### 8. **Market Manipulation**
- Large traders ("whales") can artificially move prices
- Wash trading or coordinated activity
- **Impact**: Some price points may not reflect genuine probability

#### 9. **Fee Structure**
- Polymarket charges fees on trades
- Fees affect effective returns even with perfect calibration
- Not captured in simple win rate analysis

#### 10. **Temporal Changes**
- Market efficiency may improve over time as platform matures
- User base composition changes
- **Recommendation**: Analyze by time period (early 2024 vs late 2024)

## Interpreting Results

### Perfect Calibration
If markets are perfectly calibrated, the win rate line should follow the diagonal:
- 50¢ contracts → 50% win rate
- 70¢ contracts → 70% win rate

### Identifying Edges

**Positive edge** (underpriced):
- Win rate > price (line above diagonal)
- Example: 60¢ contracts win 65% of the time → +5¢ edge

**Negative edge** (overpriced):
- Win rate < price (line below diagonal)
- Example: 40¢ contracts win 35% of the time → -5¢ edge

### Statistical Significance
- Check confidence intervals (shaded regions)
- Wider intervals at extremes due to smaller sample sizes
- Only act on deviations that are statistically significant

## Advanced Analysis Ideas

### 1. Liquidity Stratification
```python
# Filter by volume
high_liquidity = df[df['volume_total'] > 10000]
low_liquidity = df[df['volume_total'] < 1000]
```

### 2. Recency Analysis
```python
# Compare recent vs old markets
recent = df[df['trade_timestamp'] > '2024-06-01']
older = df[df['trade_timestamp'] < '2024-06-01']
```

### 3. Size-Weighted Analysis
Weight each trade by its size rather than counting all trades equally.

### 4. Expected Value Calculation
```python
# For a 60¢ contract with 65% win rate:
EV = 0.65 * 1.00 + 0.35 * 0.00 - 0.60 = +0.05 (5¢ edge)
```

### 5. Kelly Criterion for Bet Sizing
Once you identify an edge, use Kelly criterion to determine optimal position size.

### 6. Composite Score
Combine multiple signals:
- Time to resolution
- Market category  
- Liquidity level
- Recent price movement

## Testing

Test the sampling functionality:

```bash
python3 test_sampling.py                           # Run default tests
python3 test_sampling.py -c <condition_id>         # Test specific market
python3 test_sampling.py -c <condition_id> --all   # Compare sampled vs full fetch
```

## Rate Limiting

The data collector implements basic rate limiting:
- 100ms between requests
- Additional 0.5s sleep between market pagination
- 0.1-0.2s sleep between trade pagination

For large-scale collection, monitor for HTTP 429 (rate limit) responses.

## Data API Endpoints Used

1. **Gamma API** (market metadata):
   - `GET https://gamma-api.polymarket.com/markets`
   - No authentication required for read-only access
   
2. **Data API** (trade history):
   - `GET https://data-api.polymarket.com/trades`
   - No authentication required

## Troubleshooting

**"No data files found"** 
→ Run `polymarket_data_collector.py` first

**"Insufficient data" in plots**
→ Collect more markets or reduce `min_samples` parameter

**Rate limit errors**
→ Increase sleep times in collector or reduce batch size

**Memory issues with large datasets**
→ Process in chunks using the progress save feature

## Future Enhancements

- [ ] Real-time data collection via WebSocket
- [ ] Machine learning for price prediction
- [ ] Backtesting framework for trading strategies
- [ ] Integration with Polymarket CLOB API for automated trading
- [ ] Portfolio optimization across multiple markets
- [ ] Sentiment analysis from market comments

## Legal Disclaimer

This tool is for research and educational purposes only. Trading on prediction markets involves risk. Past performance does not guarantee future results. Check Polymarket's Terms of Service and your local regulations before trading.

## References

- Polymarket API Documentation: https://docs.polymarket.com/
- Gamma API: https://gamma-api.polymarket.com
- Polymarket GitHub: https://github.com/Polymarket
