# Polymarket Win Rate Analysis - Project Status

## Current State

### ✅ Implemented

#### Data Collection

Two collector classes for different use cases:

**Simple Collector (`polymarket_data_collector.py`)**
- `PolymarketDataCollector` class
- Fetches most recent resolved markets ordered by volume
- `collect_dataset()` - main collection method
- Best for: Quick data collection, testing

**Sampled Collector (`polymarket_sampled_collector.py`)**
- `PolymarketSampledCollector` class (extends base)
- Collects markets across multiple time windows (weeks)
- Samples trades from large markets to avoid bias toward recent trades
- `collect_by_time_windows()` - main collection method
- Best for: Comprehensive analysis with good time coverage

**Trade Fetching Behavior:**
- API max batch size: 500 trades per request
- Small/medium markets (<2000 trades): fetches ALL trades
- Large markets (2000+ trades): keeps newest 2000, marks as "sampled"
- The 2000 threshold is effectively a cap for most markets

**Shared Features:**
- **Gamma API Integration**: Fetches resolved markets with metadata
- **Data API Integration**: Collects historical trade data
- **Pagination Support**: Handles large datasets with automatic pagination
- **Rate Limiting**: Built-in delays to respect API limits
- **Progress Saving**: Saves data incrementally to prevent loss
- **Data Structure**: Comprehensive trade-level data with:
  - Market metadata (question, category, volume, liquidity)
  - Trade details (timestamp, price, size, side)
  - Resolution info (outcome, win/loss, time to resolution)
  - Category classification

#### Analysis Capabilities (`polymarket_analyzer.py`)
- **Main Calibration Plot**: Win percentage vs price with confidence intervals
- **YES vs NO Comparison**: Separate analysis of YES and NO contracts
  - Side-by-side calibration curves
  - Deviation from perfect calibration
  - Statistical significance testing
  - Trading recommendations
- **Time Stratification**: Analysis by time-to-resolution buckets
  - 0-24 hours, 1-3 days, 3-7 days, 1-4 weeks, 1-3 months, >3 months
- **Category Analysis**: Win rates across market categories
  - Politics, sports, crypto, etc.
- **Statistical Measures**:
  - Wilson confidence intervals (proper for proportions)
  - Mean absolute calibration error
  - Sample size tracking
- **Visualization**:
  - Publication-quality plots
  - Multiple view formats
  - Automated interpretation

#### Documentation
- **README.md**: Complete installation and usage guide
- **TRADING_GUIDE.md**: Practical guide for finding trading edges
- **YES_NO_ANALYSIS_GUIDE.md**: Detailed interpretation of YES/NO analysis
- **Example Scripts**: Demonstration of key workflows

### 📊 Current Data Coverage

**What We Collect:**
- Resolved markets only (closed with outcomes)
- All BUY trades (current analysis focuses on buys)
- Market metadata: question, category, volume, liquidity, creation date
- Trade data: timestamp, price, size, side (BUY/SELL), outcome
- Resolution data: winning outcome, resolution timestamp
- Derived fields: time_to_resolution_hours

**What We Analyze:**
- Overall calibration (all trades combined)
- YES vs NO split analysis
- Time-to-resolution stratification (6 buckets)
- Category-based analysis
- Confidence intervals at all price points

### 🎯 Key Findings Framework

**Calibration Analysis**:
- Perfect calibration = win rate matches price paid
- Underpriced = win rate > price (positive edge)
- Overpriced = win rate < price (negative edge)

**Statistical Rigor**:
- Minimum sample size filters (default: 30 trades per bucket)
- Wilson confidence intervals (95%)
- Multiple hypothesis testing awareness

---

## 🔬 High Priority: Next Steps to Investigate

### 1. ⭐⭐⭐ Round Number Effects
**Hypothesis**: Contracts at X9¢ (69¢, 79¢, 89¢) may be underpriced relative to X0¢ (70¢, 80¢, 90¢)

**Why investigate:**
- Psychological anchoring to round numbers
- Traders may set limit orders at round prices
- Just-below-round prices might be more efficient/accurate
- Specific user observation: 69/79/89 underpriced vs 70/80/90

**How to analyze:**
```python
# Bucket into specific price points
df['price_cent'] = (df['price'] * 100).round().astype(int)

# Compare X9 vs X0 prices
x9_prices = df[df['price_cent'].isin([69, 79, 89])]
x0_prices = df[df['price_cent'].isin([70, 80, 90])]

# Analyze win rates
# Also check: 49 vs 50, 59 vs 60, etc.
```

**Expected implementation:**
- Create fine-grained price buckets (1¢ resolution)
- Plot win rate for each cent value
- Highlight round vs non-round prices
- Statistical test: X9 vs X0 comparison
- Control for category, time, liquidity

---

### 2. ⭐⭐⭐ Trade Size Analysis
**Hypothesis**: Small trades (retail) are less informed than large trades (whales)

**Why investigate:**
- Retail traders (<$10) may overpay
- Whales (>$1,000) may get better prices or manipulate
- Different trader sophistication levels

**How to analyze:**
```python
# Define size buckets
micro = df[df['size'] < 10]          # Retail
small = df[(df['size'] >= 10) & (df['size'] < 100)]
medium = df[(df['size'] >= 100) & (df['size'] < 1000)]
large = df[df['size'] >= 1000]       # Whales

# Compare calibration across buckets
# Look for systematic differences
```

**What to look for:**
- Do micro trades show worse calibration?
- Do whales get better execution prices?
- Is there a "sophistication premium"?

---

### 3. ⭐⭐⭐ Market Volume/Liquidity Tiers
**Hypothesis**: Thin markets are less efficient than liquid markets

**Why investigate:**
- Low liquidity = wider spreads = more noise
- High volume markets likely arbitraged
- May hide exploitable edges in thin markets

**How to analyze:**
```python
# Define liquidity tiers
ultra_thin = df[df['volume_total'] < 1000]
thin = df[(df['volume_total'] >= 1000) & (df['volume_total'] < 10000)]
medium = df[(df['volume_total'] >= 10000) & (df['volume_total'] < 100000)]
thick = df[df['volume_total'] >= 100000]

# Analyze each tier separately
```

**What to look for:**
- Are thin markets mispriced by >5¢?
- Is there a volume threshold for efficiency?
- Risk/reward tradeoff (thin = more edge but harder to trade)

---

### 4. ⭐⭐⭐ Market Age at Time of Trade
**Hypothesis**: New markets (<24 hours old) are less efficient

**Why investigate:**
- Initial price discovery phase
- Fewer informed traders early
- Information asymmetry

**How to analyze:**
```python
# Calculate market age when trade occurred
df['market_age_hours'] = (
    (df['trade_timestamp'] - df['created_at']).dt.total_seconds() / 3600
)

# Buckets
first_24h = df[df['market_age_hours'] < 24]
day_2_7 = df[(df['market_age_hours'] >= 24) & (df['market_age_hours'] < 168)]
week_2_plus = df[df['market_age_hours'] >= 168]
```

**What to look for:**
- Do first 24 hours show wild mispricing?
- When does market reach "maturity"?
- Opportunity in new markets vs risk

---

## 📋 Additional Data We May Need

### Currently NOT Collected (But Potentially Valuable)

#### 1. Historical Price Snapshots
**What:** Market prices at regular intervals (hourly/daily)
**Why:** 
- Analyze price momentum
- Mean reversion strategies
- Volatility calculations
- Track price changes over time

**How to get:**
- CLOB API: `/prices-history` endpoint
- Snapshot prices at fixed intervals before resolution
- Store as separate time series

**Use cases:**
- "Contracts that spiked 20¢ in last 24h" analysis
- Volatility-based stratification
- Price trend analysis

---

#### 2. Order Book Data
**What:** Bid/ask spreads, depth, liquidity at each price level
**Why:**
- Measure market liquidity more precisely
- Identify manipulation (thin order books)
- Understand execution quality
- Distinguish limit vs market orders

**How to get:**
- CLOB API: `/orderbook` or WebSocket streams
- Snapshot at regular intervals
- Store bid/ask at multiple price levels

**Use cases:**
- Spread-adjusted return analysis
- Liquidity quality metrics
- Market maker presence

---

#### 3. Trader/Wallet Information
**What:** Number of unique traders, wallet addresses, trader volume
**Why:**
- "Wisdom of crowds" requires crowds
- Markets with few traders less reliable
- Identify whale-dominated markets
- Track trader sophistication

**How to get:**
- Aggregate from trade data (wallet addresses)
- Count unique traders per market
- Calculate trader concentration (Gini coefficient)

**Use cases:**
- Markets with <10 traders vs >100 traders
- Whale impact analysis
- Trader diversity metrics

**Privacy note:** Wallet addresses are public on-chain but should be handled carefully

---

#### 4. Market Creation/Metadata Timeline
**What:** When market was created, by whom, initial liquidity
**Why:**
- Market age analysis (already partially have via created_at)
- Creator sophistication
- Initial liquidity provision

**How to get:**
- Gamma API already provides some of this
- May need to enhance collection

**Use cases:**
- New market opportunity window
- Creator track record

---

#### 5. SELL Side Trades
**What:** Currently only analyzing BUY trades
**Why:**
- Complete picture of market activity
- SELL pressure vs BUY pressure
- Different trader types on each side

**Status:** 
- Already collecting, just not analyzing
- Easy to add to analysis

**Use cases:**
- Bid-ask spread analysis
- Seller sophistication
- Market making activity


## 🔧 Technical Enhancements Needed

### For Round Number Analysis
- Fine-grained price bucketing (1¢ resolution)
- Statistical tests for specific price comparisons
- Visualization highlighting round vs non-round

### For Trade Size Analysis  
- Size-based stratification
- Weighted analysis (volume-weighted vs count-weighted)
- Sophistication scoring

### For Market Age Analysis
- Timestamp parsing for market creation
- Age calculation at trade time
- Dynamic bucketing

### For Temporal Analysis
- Time zone handling (UTC vs EST)
- Holiday/event calendars
- Platform growth metrics

---

## 💾 Data Storage Considerations

**Current:**
- CSV files (simple, portable)
- JSON for raw data
- Works well for 100k-1M trades

**Future needs if scaling:**
- Database (SQLite or PostgreSQL)
- Indexed queries for complex filters
- Partitioning by date/category
- Compressed storage for historical data

---

## 🎯 Prioritized Roadmap

### Phase 1: Quick Wins (High Impact, Easy Implementation)
1. Round number effects (69 vs 70, etc.) ⭐⭐⭐
2. Trade size stratification ⭐⭐⭐
3. Market volume tiers ⭐⭐⭐
4. Market age analysis ⭐⭐⭐

### Phase 2: Medium Complexity
5. Time of day/week effects ⭐⭐
6. Objective vs subjective classification ⭐⭐
7. Temporal evolution (early vs late 2024) ⭐⭐
8. SELL side analysis ⭐⭐

### Phase 3: Advanced (Requires Additional Data)
9. Historical price snapshots (momentum/volatility)
10. Order book analysis (spreads/liquidity)
11. Trader count/diversity metrics
12. Related market links

### Phase 4: Research Extensions
13. News event impact
14. Sentiment analysis
15. Multi-factor composite models
16. Machine learning predictions

---

## 📊 Success Metrics

**What constitutes a "finding":**
- Systematic deviation >5¢ from perfect calibration
- Statistically significant (p < 0.05)
- Sample size >100 trades minimum
- Persistent across time periods
- Actionable for trading (>3¢ edge after fees)

**What to avoid:**
- Overfitting to noise
- Small sample conclusions
- Ignoring transaction costs
- Historical edges that no longer exist

---

## 🔄 Iteration Process

1. **Hypothesize**: What might be mispriced?
2. **Implement**: Add analysis code
3. **Validate**: Check on holdout data
4. **Interpret**: What does it mean?
5. **Trade test**: Paper trade or small positions
6. **Monitor**: Track performance vs expectations
7. **Adapt**: Markets evolve, edges disappear

---

## 📝 Notes for Claude

**When implementing new analyses:**
- Always include confidence intervals
- Check sample sizes (warn if <50)
- Compare to perfect calibration baseline
- Provide trading interpretation
- Consider interaction effects
- Document limitations

**Code style:**
- Consistent with existing analyzer
- Clear variable names
- Docstrings for new methods
- Examples in main() function

**Data quality:**
- Validate timestamps
- Handle missing data
- Check for outliers
- Document filtering decisions

---

Last updated: December 2025
Status: Active development
Next review: After implementing Phase 1 analyses