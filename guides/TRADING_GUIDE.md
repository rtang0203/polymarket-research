# Finding Trading Edges: Critical Considerations

## Top Priority Analyses for Trading Opportunities

### 1. TIME TO RESOLUTION (Most Important!)

**Why it matters**: A 60¢ contract 3 months before resolution is VERY different from 60¢ one hour before.

**What to look for**:
- **Short-term (< 1 day)**: Markets should be highly efficient. Little edge available.
- **Medium-term (1 week - 1 month)**: MOST OPPORTUNITY for mispricing
- **Long-term (> 3 months)**: High variance, hard to distinguish skill from luck

**How to analyze**:
```python
analyzer.analyze_by_time_to_resolution(
    time_buckets=[0, 24, 24*3, 24*7, 24*14, 24*30, 24*90, float('inf')]
)
```

**What systematic mispricing looks like**:
- Medium-term contracts at 65-75¢ consistently winning 80%+ → underpriced
- Long-term contracts at 20-30¢ consistently winning 40%+ → underpriced

---

### 2. MARKET CATEGORY EFFICIENCY

**Why it matters**: Different markets have different levels of sophistication.

**Likely efficient** (hard to find edges):
- Major sports events (NBA, NFL)
- High-profile politics (Presidential elections)
- Well-followed crypto events

**Potentially less efficient** (opportunity for edges):
- Niche tech predictions
- Obscure political races
- Entertainment/pop culture
- New/emerging categories

**How to analyze**:
```python
analyzer.analyze_by_category()
```

---

### 3. LIQUIDITY STRATIFICATION

**Why it matters**: Low liquidity = higher spreads = more noise in prices.

**What to look for**:
- Markets with < $1,000 volume: Potentially mispriced but risky
- Markets with $10,000+ volume: More reliable price signals
- Very high volume (>$100k): Probably well-arbitraged

**Implementation**:
```python
# Add to analyzer
high_liq = df[df['volume_total'] > 10000]
low_liq = df[df['volume_total'] < 1000]
```

---

### 4. PRICE EXTREMES (Under/Overconfidence)

**Why it matters**: People often misprice tail events.

**What to look for**:
- **5-15¢ contracts**: Are they winning more than their price suggests? (Underpriced tails)
- **85-95¢ contracts**: Are they winning less than their price suggests? (Overconfident)

**Common patterns**:
- Long-shot bias: People overpay for unlikely outcomes (5¢ contracts win < 5%)
- Favorite bias: People underpay for likely outcomes (90¢ contracts win > 90%)

---

### 5. TIMING EFFECTS

**Market maturity** matters:
- **First 24 hours**: Prices can be wild, high spreads
- **After 1 week**: More informed, but still exploitable
- **Last 24 hours**: Usually very efficient

**News sensitivity**:
- Markets that react to scheduled events (earnings, elections) 
- vs. Markets that depend on continuous information

---

## Red Flags (When NOT to Trade)

### Statistical Red Flags
1. **Small sample size**: < 50 trades in a price bucket
2. **Wide confidence intervals**: Overlapping with perfect calibration
3. **Inconsistent across time periods**: Edge disappears in recent data

### Market Structure Red Flags  
1. **Very thin markets**: < $500 total volume
2. **Extreme spreads**: > 10¢ difference between bid/ask
3. **Single large trade**: One whale moving the entire market
4. **No recent trades**: Market might be stale/abandoned

### Category Red Flags
1. **Highly correlated markets**: Many similar questions (not independent samples)
2. **Subjective resolution**: Unclear how market will resolve
3. **Delayed resolution**: Takes months to resolve after event occurs

---

## Calculating Expected Value (EV)

For a contract priced at P with true win probability W:

**EV = W × $1 + (1-W) × $0 - P**

Example:
- Price: 60¢ (P = 0.60)
- True win rate: 65% (W = 0.65)
- EV = 0.65 × 1.00 - 0.60 = **+5¢ per dollar bet**

**Minimum edges worth trading**:
- Need to overcome fees (~1-2%)
- Need to overcome spread (~1-5%)
- Need buffer for estimation error
- **Rule of thumb**: Look for 5-10¢+ edges minimum

---

## Sample Size Requirements

For statistical confidence:

| Confidence Level | Minimum Trades per Bucket |
|-----------------|---------------------------|
| Low confidence  | 30                        |
| Medium confidence| 100                      |
| High confidence | 300+                      |

**At price extremes** (< 10¢ or > 90¢):
- Need even MORE samples due to lower base rates
- Confidence intervals will be wider

---

## Quick Profitability Check

Given an edge of E (in decimal) and price P:

**ROI per trade = E / P**

Example:
- 60¢ contract, 5¢ edge
- ROI = 0.05 / 0.60 = 8.3% per trade

**After fees** (~2%):
- Net ROI = 8.3% - 2% = 6.3%

**Minimum ROI targets**:
- Single trades: > 5% after fees
- Portfolio approach: > 3% after fees (with volume)

---

## Workflow for Finding Edges

1. **Collect data** (500-1000+ resolved markets)
   ```bash
   python polymarket_data_collector.py
   ```

2. **Generate main calibration plot**
   - Look for systematic deviations from diagonal
   - Note which price ranges

3. **Stratify by time-to-resolution**
   - Focus on 1 week - 1 month window
   - This is where edges are most likely

4. **Stratify by category**  
   - Identify inefficient categories
   - Avoid hyper-efficient categories (major sports)

5. **Check sample sizes**
   - Ignore buckets with < 50 trades
   - Wider CI at extremes is normal

6. **Calculate expected value**
   - For each identified edge
   - Account for fees and spreads
   - Minimum 5¢ edge after costs

7. **Validate on recent data**
   - Does edge persist in last 3 months?
   - Or was it a historical artifact?

8. **Start small**
   - Test with small positions
   - Track your own performance
   - Adjust based on results

---

## Advanced: Composite Scoring

Combine multiple signals for stronger predictions:

**High-confidence trade characteristics**:
- ✓ 1-2 week time to resolution
- ✓ Inefficient category (tech, entertainment)
- ✓ Medium liquidity ($5k-$50k volume)
- ✓ Price in 60-75¢ range winning 80%+
- ✓ Large sample size (100+ trades in bucket)
- ✓ Consistent across recent time periods
- ✓ Clear resolution criteria

**Avoid trading when**:
- ✗ < 48 hours to resolution (too efficient)
- ✗ > 3 months to resolution (too much uncertainty)
- ✗ Major sports event (too efficient)
- ✗ < $1k volume (too thin)
- ✗ Small sample size (< 30 trades)
- ✗ Edge only appears in old data
- ✗ Subjective resolution

---

## Reality Check

**Before you trade based on this analysis**:

1. **Markets adapt**: If you find an edge, others might too. It may disappear.

2. **Transaction costs**: Fees, spreads, and slippage eat into profits.

3. **Liquidity risk**: Can you actually get filled at the prices you want?

4. **Bankroll management**: Never risk more than 1-5% of your bankroll per trade.

5. **Polymarket-specific risks**:
   - Platform risk (technical issues, closure)
   - Resolution disputes
   - Regulatory changes
   - Withdrawal limits

6. **Your own biases**: 
   - Are you finding edges or seeing patterns in noise?
   - Backtest on out-of-sample data
   - Track live performance vs expectations

**The best approach**: Start by paper trading (tracking hypothetical bets) before risking real money.
