"""
Example: YES vs NO Bias Analysis

This script demonstrates how to check if YES contracts are systematically
priced differently from NO contracts on Polymarket.
"""

import pandas as pd
from pathlib import Path
from polymarket_analyzer import PolymarketAnalyzer

def main():
    """
    Run YES vs NO comparison analysis
    """
    
    # Load most recent data
    data_dir = Path("polymarket_data")
    data_files = list(data_dir.glob("polymarket_trades_*.csv"))
    
    if not data_files:
        print("No data files found!")
        print("Run polymarket_data_collector.py first to collect data.")
        return
    
    latest_file = max(data_files, key=lambda p: p.stat().st_mtime)
    print(f"Loading data from: {latest_file}\n")
    
    # Create analyzer
    analyzer = PolymarketAnalyzer(str(latest_file))
    
    # Run YES vs NO analysis
    print("="*70)
    print("ANALYZING YES VS NO CONTRACT PRICING")
    print("="*70)
    
    yes_results, no_results = analyzer.analyze_yes_vs_no(
        price_bins=20,
        min_samples=30,
        save_path='polymarket_data/yes_vs_no_comparison.png'
    )
    
    # Additional detailed analysis
    print("\n\nDETAILED BREAKDOWN BY PRICE RANGE:")
    print("="*70)
    
    # Compare specific price ranges
    price_ranges = [
        (0.0, 0.3, "Low probability (0-30¢)"),
        (0.3, 0.7, "Medium probability (30-70¢)"),
        (0.7, 1.0, "High probability (70-100¢)")
    ]
    
    for low, high, label in price_ranges:
        yes_in_range = analyzer.df[
            (analyzer.df['outcome'] == 'Yes') & 
            (analyzer.df['price'] >= low) & 
            (analyzer.df['price'] < high)
        ]
        
        no_in_range = analyzer.df[
            (analyzer.df['outcome'] == 'No') & 
            (analyzer.df['price'] >= low) & 
            (analyzer.df['price'] < high)
        ]
        
        if len(yes_in_range) > 0 and len(no_in_range) > 0:
            yes_win_rate = yes_in_range['won'].mean()
            yes_avg_price = yes_in_range['price'].mean()
            yes_edge = yes_win_rate - yes_avg_price
            
            no_win_rate = no_in_range['won'].mean()
            no_avg_price = no_in_range['price'].mean()
            no_edge = no_win_rate - no_avg_price
            
            print(f"\n{label}:")
            print(f"  YES: {len(yes_in_range):,} trades | "
                  f"Avg price: {yes_avg_price*100:.1f}¢ | "
                  f"Win rate: {yes_win_rate*100:.1f}% | "
                  f"Edge: {yes_edge*100:+.1f}¢")
            print(f"  NO:  {len(no_in_range):,} trades | "
                  f"Avg price: {no_avg_price*100:.1f}¢ | "
                  f"Win rate: {no_win_rate*100:.1f}% | "
                  f"Edge: {no_edge*100:+.1f}¢")
            
            if abs(yes_edge - no_edge) > 0.05:  # 5¢ difference
                if yes_edge > no_edge:
                    print(f"  → YES contracts have a {abs(yes_edge - no_edge)*100:.1f}¢ BETTER edge in this range!")
                else:
                    print(f"  → NO contracts have a {abs(yes_edge - no_edge)*100:.1f}¢ BETTER edge in this range!")
    
    print("\n" + "="*70)
    print("\nTRADING IMPLICATIONS:")
    print("="*70)
    
    # Overall comparison
    yes_all = analyzer.df[analyzer.df['outcome'] == 'Yes']
    no_all = analyzer.df[analyzer.df['outcome'] == 'No']
    
    yes_overall_edge = yes_all['won'].mean() - yes_all['price'].mean()
    no_overall_edge = no_all['won'].mean() - no_all['price'].mean()
    
    print(f"\nOverall YES edge: {yes_overall_edge*100:+.2f}¢")
    print(f"Overall NO edge:  {no_overall_edge*100:+.2f}¢")
    
    if abs(yes_overall_edge) > 0.03 or abs(no_overall_edge) > 0.03:
        print("\n📊 SIGNIFICANT BIAS DETECTED!")
        
        if yes_overall_edge > no_overall_edge + 0.02:
            print("   Strategy: FAVOR YES contracts over NO contracts")
            print(f"   Expected advantage: ~{(yes_overall_edge - no_overall_edge)*100:.1f}¢ per trade")
        elif no_overall_edge > yes_overall_edge + 0.02:
            print("   Strategy: FAVOR NO contracts over YES contracts")
            print(f"   Expected advantage: ~{(no_overall_edge - yes_overall_edge)*100:.1f}¢ per trade")
        else:
            print("   Strategy: No clear bias - both sides appear similar")
    else:
        print("\n✓ No significant YES/NO bias detected")
        print("  Markets appear to price YES and NO contracts fairly equally")
    
    # Theoretical check: YES at price P should equal NO at price (1-P)
    print("\n\nTHEORETICAL CONSISTENCY CHECK:")
    print("="*70)
    print("In theory: Buying YES at 60¢ = Buying NO at 40¢")
    print("Testing if this holds in practice...\n")
    
    # Test at several price points
    test_prices = [0.3, 0.4, 0.5, 0.6, 0.7]
    
    for price in test_prices:
        complement_price = 1 - price
        tolerance = 0.05  # ±5¢
        
        yes_at_price = analyzer.df[
            (analyzer.df['outcome'] == 'Yes') &
            (analyzer.df['price'] >= price - tolerance) &
            (analyzer.df['price'] <= price + tolerance)
        ]
        
        no_at_complement = analyzer.df[
            (analyzer.df['outcome'] == 'No') &
            (analyzer.df['price'] >= complement_price - tolerance) &
            (analyzer.df['price'] <= complement_price + tolerance)
        ]
        
        if len(yes_at_price) > 30 and len(no_at_complement) > 30:
            yes_win_rate = yes_at_price['won'].mean()
            no_win_rate = no_at_complement['won'].mean()
            
            print(f"YES at {price*100:.0f}¢ vs NO at {complement_price*100:.0f}¢:")
            print(f"  YES win rate: {yes_win_rate*100:.1f}%")
            print(f"  NO win rate:  {no_win_rate*100:.1f}%")
            print(f"  Difference:   {abs(yes_win_rate - no_win_rate)*100:.1f}¢", end="")
            
            if abs(yes_win_rate - no_win_rate) > 0.05:
                print(" ⚠️ SIGNIFICANT DIFFERENCE!")
            else:
                print(" ✓ Consistent")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
