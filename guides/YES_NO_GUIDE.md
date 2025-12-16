# YES vs NO Analysis Guide

## Understanding the YES/NO Comparison Plots

When you run `analyzer.analyze_yes_vs_no()`, you'll get two plots side-by-side:

### Plot 1: Win Rate vs Price (Both Sides)

This shows the calibration curves for YES and NO contracts on the same graph.

**What to look for:**

```
Perfect Scenario (No Bias):
100|                    
   |           /
   |         /
   |       / ●●  (Both YES and NO follow diagonal)
50 |     /●●
   |   /●●
   | /●●
 0 +--------
   0   50  100

Both lines overlay the diagonal = Fair pricing
```

```
YES Overpriced Scenario:
100|                    
   |           /
   |         /●  (NO line)
   |       /●●
50 |     /●
   |   /●   ● (YES line below diagonal)
   | /   ●●
 0 +--------
   0   50  100

Blue (YES) below diagonal = YES contracts overpriced
Red (NO) above diagonal = NO contracts underpriced
```

```
YES Underpriced Scenario:
100|                    
   |           /
   |         /  ●● (YES line)
   |       /●●
50 |     / ●
   |   /●   ● (NO line below diagonal)
   | /●●
 0 +--------
   0   50  100

Blue (YES) above diagonal = YES contracts underpriced
Red (NO) below diagonal = NO contracts overpriced
```

### Plot 2: Deviation from Perfect Calibration

This shows how far each side deviates from perfect calibration.

**Reading the plot:**

```
Y-axis: Deviation in cents
+10¢ |     ●    ← Underpriced (wins 10¢ more than price)
     |   ●
     | ●
  0¢ ├─────●───── Perfect calibration
     |       ●
     |         ●
-10¢ |           ● ← Overpriced (wins 10¢ less than price)
     +──────────────
     0¢  50¢  100¢
```

**Interpretation:**

- **Points above 0**: Contracts win MORE than their price suggests (underpriced)
- **Points below 0**: Contracts win LESS than their price suggests (overpriced)
- **Gray band (±5¢)**: Normal variation, not actionable
- **Outside gray band**: Potential systematic mispricing

## Real-World Scenarios

### Scenario 1: "YES Optimism Bias"

People prefer betting on positive outcomes ("Yes, this will happen").

**What you'd see:**
- YES contracts: -3¢ to -5¢ deviation (overpriced)
- NO contracts: +3¢ to +5¢ deviation (underpriced)

**Trading strategy:**
- Avoid YES contracts
- Favor NO contracts
- Expected edge: 3-5¢ per trade

**Why it happens:**
- Psychological preference for affirmative bets
- More liquidity on YES side pushes prices up
- Casual bettors prefer YES

### Scenario 2: "Contrarian Bias"

Sophisticated traders favor NO (betting against outcomes).

**What you'd see:**
- YES contracts: +3¢ to +5¢ deviation (underpriced)
- NO contracts: -3¢ to -5¢ deviation (overpriced)

**Trading strategy:**
- Favor YES contracts
- Avoid NO contracts
- Expected edge: 3-5¢ per trade

**Why it happens:**
- Smart money concentrates on NO side
- Retail traders avoid contrarian positions

### Scenario 3: "No Systematic Bias"

Markets are efficient across both sides.

**What you'd see:**
- Both YES and NO: ±1¢ to ±2¢ deviation
- Lines follow diagonal closely
- Deviations within gray band

**Trading strategy:**
- No bias to exploit
- Focus on other factors (category, timing, liquidity)

## Statistical Output Interpretation

The script will print:

```
YES vs NO CALIBRATION COMPARISON
====================================

YES contracts:
  Mean absolute calibration error: 0.0234 (2.34¢)
  Average deviation: -2.15¢
  Trades analyzed: 45,234

NO contracts:
  Mean absolute calibration error: 0.0198 (1.98¢)
  Average deviation: +2.32¢
  Trades analyzed: 38,761

Interpretation:
  ⚠️  YES contracts appear OVERPRICED
  ✓  NO contracts appear UNDERPRICED
  → Consider favoring NO contracts in your trading!
```

**Key metrics:**

1. **Mean absolute calibration error**: How far off from perfect on average
   - < 2¢: Very good calibration
   - 2-5¢: Moderate miscalibration
   - > 5¢: Significant miscalibration

2. **Average deviation**: Directional bias
   - Negative: Overpriced (wins less than price)
   - Positive: Underpriced (wins more than price)
   - Magnitude: Size of the edge

3. **Trades analyzed**: Sample size
   - > 10,000: Very reliable
   - 1,000-10,000: Moderately reliable
   - < 1,000: Less reliable

## Price Range Breakdown

The example script analyzes three ranges:

### Low Probability (0-30¢)
Long-shot bets. Look for:
- Which side (YES/NO) is more overpriced at extremes?
- Are people overpaying for unlikely YES outcomes?

### Medium Probability (30-70¢)
Most liquid range. Look for:
- Consistent bias across the curve
- Largest sample sizes = most reliable

### High Probability (70-100¢)
Near-certain outcomes. Look for:
- Overconfidence on favorite outcomes
- Which side captures the "sure thing" premium better

## Theoretical Consistency Test

The script tests: **YES at P% = NO at (100-P)%**

Example:
- Buying YES at 60¢ should be exactly the same as buying NO at 40¢
- Both express the belief that YES has a 60% chance

**If this holds:**
```
YES at 60¢ wins: 60%
NO at 40¢ wins: 40% (which is same as YES winning 60%)
Difference: 0¢ ✓
```

**If YES is systematically overpriced:**
```
YES at 60¢ wins: 55% (overpriced by 5¢)
NO at 40¢ wins: 45% (underpriced by 5¢, YES wins 55%)
Difference: ~0¢ ✓ Consistent bias
```

**If there's an inconsistency:**
```
YES at 60¢ wins: 55%
NO at 40¢ wins: 40% (YES wins 60%)
Difference: 5¢ ⚠️ Market inefficiency!
```

This could indicate arbitrage opportunities or market fragmentation.

## Trading Implications

### Small Bias (1-3¢)
- Probably not worth trading on alone
- Combine with other signals (time, category, liquidity)
- Focus on high-volume opportunities

### Moderate Bias (3-5¢)
- Tradable edge after fees
- Apply consistently across many trades
- Size positions appropriately

### Large Bias (>5¢)
- Strong signal if sample size is large
- Verify with recent data (might be historical artifact)
- Could be category-specific or time-specific
- Potentially very profitable

### No Bias (0-1¢)
- Markets are efficient across both sides
- Don't waste time trying to exploit YES/NO differences
- Focus on other sources of edge

## Combining with Other Analyses

YES/NO bias might interact with:

1. **Time to resolution**: Bias might only appear in long-dated markets
2. **Category**: Some categories might have YES bias, others NO bias
3. **Liquidity**: Low-liquidity markets might show larger biases
4. **Market type**: Binary vs multi-outcome markets

**Advanced workflow:**
```python
# Check if bias varies by time to resolution
for time_range in ['1_week', '1_month', '3_months']:
    subset = df[df['time_bucket'] == time_range]
    # Run YES/NO analysis on subset
    # Compare results
```

## Common Pitfalls

1. **Sample size too small**: Need 1000+ trades per side minimum
2. **Old data**: Bias in 2023 might not exist in 2024
3. **Ignoring fees**: 2% fee turns 3¢ edge into 1¢ edge
4. **Forgetting spread**: Bid-ask spread eats into profits
5. **Over-fitting**: Seeing patterns in noise

## Next Steps After Finding Bias

1. **Verify on recent data**: Split data into train/test periods
2. **Check across categories**: Is it universal or category-specific?
3. **Consider market dynamics**: Why would this bias exist?
4. **Calculate breakeven**: What edge do you need after fees?
5. **Test with small positions**: Paper trade or start small
6. **Track performance**: Compare actual vs expected results

Remember: Past calibration doesn't guarantee future performance!