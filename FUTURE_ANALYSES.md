# Future Analyses

Planned investigations for Polymarket calibration research.

## Phase 1: High Priority

### Round Number Effects
**Hypothesis**: Contracts at X9¢ (69¢, 79¢, 89¢) may be underpriced relative to X0¢ (70¢, 80¢, 90¢)

- Psychological anchoring to round numbers
- Traders may set limit orders at round prices

```python
# Bucket into specific price points
df['price_cent'] = (df['price'] * 100).round().astype(int)

# Compare X9 vs X0 prices
x9_prices = df[df['price_cent'].isin([69, 79, 89])]
x0_prices = df[df['price_cent'].isin([70, 80, 90])]

# Analyze win rates
# Also check: 49 vs 50, 59 vs 60, etc.
```

### Trade Size Analysis
**Hypothesis**: Small trades (retail) are less informed than large trades (whales)

```python
# Define size buckets
micro = df[df['size'] < 10]          # Retail
small = df[(df['size'] >= 10) & (df['size'] < 100)]
medium = df[(df['size'] >= 100) & (df['size'] < 1000)]
large = df[df['size'] >= 1000]       # Whales

# Compare calibration across buckets
# Look for systematic differences
```

### Market Volume/Liquidity Tiers
**Hypothesis**: Thin markets are less efficient than liquid markets

```python
# Define liquidity tiers
ultra_thin = df[df['volume_total'] < 1000]
thin = df[(df['volume_total'] >= 1000) & (df['volume_total'] < 10000)]
medium = df[(df['volume_total'] >= 10000) & (df['volume_total'] < 100000)]
thick = df[df['volume_total'] >= 100000]

# Analyze each tier separately
```

### Market Age at Time of Trade
**Hypothesis**: New markets (<24 hours old) are less efficient

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

---

## Phase 2: Medium Complexity

- Time of day/week effects
- Objective vs subjective market classification
- Temporal evolution (platform maturity over time)
- SELL side analysis (currently only analyzing BUY trades)

## Phase 3: Requires Additional Data

- Historical price snapshots (momentum/volatility analysis)
- Order book data (spreads/liquidity)
- Trader count/diversity metrics
- Related market correlation

## Phase 4: Research Extensions

- News event impact analysis
- Sentiment analysis
- Multi-factor composite models
- Machine learning predictions

---

## Additional Data Sources to Consider

### Historical Price Snapshots
- CLOB API: `/prices-history` endpoint
- Use cases: price momentum, mean reversion, volatility

### Order Book Data
- CLOB API: `/orderbook` or WebSocket streams
- Use cases: spread analysis, liquidity quality, market maker detection

### Trader/Wallet Information
- Aggregate from trade data (wallet addresses are public on-chain)
- Use cases: whale impact, trader diversity metrics

---

## Success Metrics

A valid finding requires:
- Systematic deviation >5¢ from perfect calibration
- Statistically significant (p < 0.05)
- Sample size >100 trades minimum
- Persistent across time periods
- Actionable for trading (>3¢ edge after fees)
