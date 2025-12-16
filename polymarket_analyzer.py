"""
Polymarket Win Rate Analysis
Analyzes the relationship between purchase price and win probability
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from pathlib import Path
from typing import Optional, Tuple

class PolymarketAnalyzer:
    """
    Analyzer for Polymarket trading data
    """
    
    def __init__(self, data_file: str):
        """
        Args:
            data_file: Path to CSV file with trade data
        """
        self.df = pd.read_csv(data_file)
        self.df['trade_timestamp'] = pd.to_datetime(self.df['trade_timestamp'])
        
        # Filter to only BUY orders (we want to know: did what I bought win?)
        self.df = self.df[self.df['side'] == 'BUY'].copy()
        
        print(f"Loaded {len(self.df)} BUY trades from {self.df['condition_id'].nunique()} markets")
    
    def calculate_win_rate_by_price(self, 
                                    price_bins: int = 20,
                                    min_samples: int = 30) -> pd.DataFrame:
        """
        Calculate win rate for each price bucket
        
        Args:
            price_bins: Number of price buckets
            min_samples: Minimum samples required per bucket
        
        Returns:
            DataFrame with price bins, win rates, and confidence intervals
        """
        # Create price bins
        self.df['price_bin'] = pd.cut(
            self.df['price'], 
            bins=price_bins,
            include_lowest=True
        )
        
        # Calculate win rate per bin
        results = []
        for price_bin in self.df['price_bin'].cat.categories:
            bin_data = self.df[self.df['price_bin'] == price_bin]
            
            if len(bin_data) < min_samples:
                continue
            
            n = len(bin_data)
            wins = bin_data['won'].sum()
            win_rate = wins / n
            
            # Calculate 95% confidence interval (Wilson score interval)
            ci_low, ci_high = self._wilson_confidence_interval(wins, n)
            
            results.append({
                'price_bin': price_bin,
                'price_midpoint': price_bin.mid,
                'win_rate': win_rate,
                'ci_low': ci_low,
                'ci_high': ci_high,
                'n_trades': n,
                'n_markets': bin_data['condition_id'].nunique()
            })
        
        return pd.DataFrame(results)
    
    def _wilson_confidence_interval(self, 
                                    successes: int, 
                                    n: int, 
                                    confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calculate Wilson score confidence interval
        More accurate than normal approximation for proportions
        """
        if n == 0:
            return 0, 0
        
        z = stats.norm.ppf((1 + confidence) / 2)
        p = successes / n
        
        denominator = 1 + z**2 / n
        center = (p + z**2 / (2*n)) / denominator
        margin = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denominator
        
        return max(0, center - margin), min(1, center + margin)
    
    def plot_win_rate_vs_price(self, 
                               price_bins: int = 20,
                               min_samples: int = 30,
                               figsize: Tuple[int, int] = (12, 7),
                               save_path: Optional[str] = None):
        """
        Create the main plot: win rate vs price
        
        Args:
            price_bins: Number of price buckets
            min_samples: Minimum samples per bucket
            figsize: Figure size
            save_path: Path to save figure (None to just display)
        """
        results = self.calculate_win_rate_by_price(price_bins, min_samples)
        
        if len(results) == 0:
            print("No data to plot!")
            return
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot win rate
        ax.plot(results['price_midpoint'] * 100, 
               results['win_rate'] * 100, 
               'o-', color='#e31e24', linewidth=2.5, markersize=6,
               label='Observed Win Rate', zorder=3)
        
        # Plot confidence interval
        ax.fill_between(results['price_midpoint'] * 100,
                       results['ci_low'] * 100,
                       results['ci_high'] * 100,
                       alpha=0.3, color='#e31e24', label='95% Confidence Interval')
        
        # Plot perfect calibration line
        x_perfect = np.linspace(0, 100, 100)
        ax.plot(x_perfect, x_perfect, '--', color='#2ecc71', linewidth=2,
               label='Perfect Calibration', zorder=2)
        
        # Styling
        ax.set_xlabel('Contract Price (¢)', fontsize=13, fontweight='bold')
        ax.set_ylabel('Win Percentage', fontsize=13, fontweight='bold')
        ax.set_title('Win Percentage Sorted by Price\n(shaded areas are 95% confidence intervals)', 
                    fontsize=15, fontweight='bold', pad=20)
        
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax.legend(loc='upper left', fontsize=11)
        
        # Add note about sample sizes
        total_trades = self.df.shape[0]
        total_markets = self.df['condition_id'].nunique()
        note_text = (f"Notes: The figure shows the fraction of contracts that won for each price "
                    f"for the full sample of {total_trades:,} trades across {total_markets:,} markets.")
        fig.text(0.1, 0.02, note_text, fontsize=9, style='italic', wrap=True)
        
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.08)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        
        plt.show()
        
        return results
    
    def analyze_by_time_to_resolution(self, time_buckets: list = None):
        """
        Analyze win rates stratified by time to resolution
        
        Args:
            time_buckets: List of time boundaries in hours
                         Default: [0, 24, 24*7, 24*30, 24*90, float('inf')]
        """
        if time_buckets is None:
            time_buckets = [0, 24, 24*7, 24*30, 24*90, float('inf')]
        
        # Filter out trades without time_to_resolution
        df_with_time = self.df[self.df['time_to_resolution_hours'].notna()].copy()
        
        # Create time buckets
        labels = []
        for i in range(len(time_buckets) - 1):
            if time_buckets[i+1] == float('inf'):
                labels.append(f'>{time_buckets[i]/24:.0f}d')
            else:
                labels.append(f'{time_buckets[i]/24:.0f}-{time_buckets[i+1]/24:.0f}d')
        
        df_with_time['time_bucket'] = pd.cut(
            df_with_time['time_to_resolution_hours'],
            bins=time_buckets,
            labels=labels,
            include_lowest=True
        )
        
        # Create subplots
        n_buckets = len(labels)
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        axes = axes.flatten()
        
        for idx, time_label in enumerate(labels):
            if idx >= len(axes):
                break
            
            bucket_data = df_with_time[df_with_time['time_bucket'] == time_label]
            
            if len(bucket_data) < 100:
                axes[idx].text(0.5, 0.5, f'Insufficient data\n(n={len(bucket_data)})',
                             ha='center', va='center', transform=axes[idx].transAxes)
                axes[idx].set_title(f'Time to Resolution: {time_label}')
                continue
            
            # Calculate win rate by price for this time bucket
            analyzer = PolymarketAnalyzer.__new__(PolymarketAnalyzer)
            analyzer.df = bucket_data
            results = analyzer.calculate_win_rate_by_price(price_bins=15, min_samples=20)
            
            # Plot
            ax = axes[idx]
            ax.plot(results['price_midpoint'] * 100, 
                   results['win_rate'] * 100, 
                   'o-', color='#e31e24', linewidth=2, markersize=5)
            
            ax.fill_between(results['price_midpoint'] * 100,
                           results['ci_low'] * 100,
                           results['ci_high'] * 100,
                           alpha=0.3, color='#e31e24')
            
            # Perfect calibration
            x_perfect = np.linspace(0, 100, 100)
            ax.plot(x_perfect, x_perfect, '--', color='#2ecc71', linewidth=1.5, alpha=0.7)
            
            ax.set_xlim(0, 100)
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3)
            ax.set_xlabel('Price (¢)', fontsize=10)
            ax.set_ylabel('Win %', fontsize=10)
            ax.set_title(f'{time_label} (n={len(bucket_data):,})', fontsize=11, fontweight='bold')
        
        # Hide unused subplots
        for idx in range(len(labels), len(axes)):
            axes[idx].set_visible(False)
        
        plt.suptitle('Win Rate vs Price by Time to Resolution', 
                    fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        plt.show()
    
    def analyze_by_category(self, categories: Optional[list] = None):
        """
        Analyze win rates by market category
        
        Args:
            categories: List of categories to analyze (None for top categories)
        """
        if categories is None:
            # Get top 6 categories by number of trades
            categories = self.df['category'].value_counts().head(6).index.tolist()
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        axes = axes.flatten()
        
        for idx, category in enumerate(categories):
            if idx >= len(axes):
                break
            
            category_data = self.df[self.df['category'] == category]
            
            if len(category_data) < 100:
                axes[idx].text(0.5, 0.5, f'Insufficient data\n(n={len(category_data)})',
                             ha='center', va='center', transform=axes[idx].transAxes)
                axes[idx].set_title(f'{category}')
                continue
            
            # Calculate win rate by price
            analyzer = PolymarketAnalyzer.__new__(PolymarketAnalyzer)
            analyzer.df = category_data
            results = analyzer.calculate_win_rate_by_price(price_bins=15, min_samples=20)
            
            # Plot
            ax = axes[idx]
            ax.plot(results['price_midpoint'] * 100, 
                   results['win_rate'] * 100, 
                   'o-', color='#e31e24', linewidth=2, markersize=5)
            
            ax.fill_between(results['price_midpoint'] * 100,
                           results['ci_low'] * 100,
                           results['ci_high'] * 100,
                           alpha=0.3, color='#e31e24')
            
            x_perfect = np.linspace(0, 100, 100)
            ax.plot(x_perfect, x_perfect, '--', color='#2ecc71', linewidth=1.5, alpha=0.7)
            
            ax.set_xlim(0, 100)
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3)
            ax.set_xlabel('Price (¢)', fontsize=10)
            ax.set_ylabel('Win %', fontsize=10)
            ax.set_title(f'{category} (n={len(category_data):,})', fontsize=11, fontweight='bold')
        
        plt.suptitle('Win Rate vs Price by Category', 
                    fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        plt.show()
    
    def analyze_yes_vs_no(self,
                         price_bins: int = 20,
                         min_samples: int = 30,
                         figsize: Tuple[int, int] = (14, 8),
                         save_path: Optional[str] = None):
        """
        Compare YES vs NO contract calibration
        
        Tests whether YES and NO contracts are priced differently
        (e.g., psychological bias toward YES)
        
        Args:
            price_bins: Number of price buckets
            min_samples: Minimum samples per bucket
            figsize: Figure size
            save_path: Path to save figure
        """
        # Separate YES and NO trades
        yes_trades = self.df[self.df['outcome'] == 'Yes'].copy()
        no_trades = self.df[self.df['outcome'] == 'No'].copy()
        
        print(f"\nYES trades: {len(yes_trades):,}")
        print(f"NO trades: {len(no_trades):,}")
        
        if len(yes_trades) < 100 or len(no_trades) < 100:
            print("Insufficient data for YES/NO comparison")
            return
        
        # Analyze each separately
        yes_analyzer = PolymarketAnalyzer.__new__(PolymarketAnalyzer)
        yes_analyzer.df = yes_trades
        yes_results = yes_analyzer.calculate_win_rate_by_price(price_bins, min_samples)
        
        no_analyzer = PolymarketAnalyzer.__new__(PolymarketAnalyzer)
        no_analyzer.df = no_trades
        no_results = no_analyzer.calculate_win_rate_by_price(price_bins, min_samples)
        
        # Create plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        # Left plot: Both on same graph
        ax1.plot(yes_results['price_midpoint'] * 100, 
                yes_results['win_rate'] * 100,
                'o-', color='#3498db', linewidth=2.5, markersize=6,
                label='YES contracts', zorder=3)
        
        ax1.fill_between(yes_results['price_midpoint'] * 100,
                        yes_results['ci_low'] * 100,
                        yes_results['ci_high'] * 100,
                        alpha=0.2, color='#3498db')
        
        ax1.plot(no_results['price_midpoint'] * 100,
                no_results['win_rate'] * 100,
                'o-', color='#e74c3c', linewidth=2.5, markersize=6,
                label='NO contracts', zorder=3)
        
        ax1.fill_between(no_results['price_midpoint'] * 100,
                        no_results['ci_low'] * 100,
                        no_results['ci_high'] * 100,
                        alpha=0.2, color='#e74c3c')
        
        # Perfect calibration line
        x_perfect = np.linspace(0, 100, 100)
        ax1.plot(x_perfect, x_perfect, '--', color='#2ecc71', linewidth=2,
                label='Perfect Calibration', zorder=2)
        
        ax1.set_xlabel('Contract Price (¢)', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Win Percentage', fontsize=12, fontweight='bold')
        ax1.set_title('YES vs NO Contract Calibration', fontsize=14, fontweight='bold')
        ax1.set_xlim(0, 100)
        ax1.set_ylim(0, 100)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left', fontsize=10)
        
        # Right plot: Deviation from perfect calibration
        yes_deviation = (yes_results['win_rate'] - yes_results['price_midpoint']) * 100
        no_deviation = (no_results['win_rate'] - no_results['price_midpoint']) * 100
        
        ax2.plot(yes_results['price_midpoint'] * 100,
                yes_deviation,
                'o-', color='#3498db', linewidth=2.5, markersize=6,
                label='YES contracts')
        
        ax2.plot(no_results['price_midpoint'] * 100,
                no_deviation,
                'o-', color='#e74c3c', linewidth=2.5, markersize=6,
                label='NO contracts')
        
        ax2.axhline(y=0, color='#2ecc71', linestyle='--', linewidth=2,
                   label='Perfect Calibration')
        ax2.fill_between([0, 100], -5, 5, alpha=0.1, color='gray',
                        label='±5¢ range')
        
        ax2.set_xlabel('Contract Price (¢)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Deviation from Perfect (¢)', fontsize=12, fontweight='bold')
        ax2.set_title('Pricing Bias Detection', fontsize=14, fontweight='bold')
        ax2.set_xlim(0, 100)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='best', fontsize=10)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"\nPlot saved to {save_path}")
        
        plt.show()
        
        # Statistical summary
        print("\n" + "="*70)
        print("YES vs NO CALIBRATION COMPARISON")
        print("="*70)
        
        yes_cal_error = np.abs(yes_results['win_rate'] - yes_results['price_midpoint']).mean()
        no_cal_error = np.abs(no_results['win_rate'] - no_results['price_midpoint']).mean()
        
        print(f"\nYES contracts:")
        print(f"  Mean absolute calibration error: {yes_cal_error:.4f} ({yes_cal_error*100:.2f}¢)")
        print(f"  Average deviation: {yes_deviation.mean():.2f}¢")
        print(f"  Trades analyzed: {len(yes_trades):,}")
        
        print(f"\nNO contracts:")
        print(f"  Mean absolute calibration error: {no_cal_error:.4f} ({no_cal_error*100:.2f}¢)")
        print(f"  Average deviation: {no_deviation.mean():.2f}¢")
        print(f"  Trades analyzed: {len(no_trades):,}")
        
        # Interpretation
        print("\nInterpretation:")
        if abs(yes_deviation.mean()) > 2 or abs(no_deviation.mean()) > 2:
            if yes_deviation.mean() < -2:
                print("  ⚠️  YES contracts appear OVERPRICED (win less than price suggests)")
            elif yes_deviation.mean() > 2:
                print("  ✓  YES contracts appear UNDERPRICED (win more than price suggests)")
            
            if no_deviation.mean() < -2:
                print("  ⚠️  NO contracts appear OVERPRICED (win less than price suggests)")
            elif no_deviation.mean() > 2:
                print("  ✓  NO contracts appear UNDERPRICED (win more than price suggests)")
                
            print("\n  → Consider favoring the underpriced side in your trading!")
        else:
            print("  ✓ Both YES and NO contracts appear fairly calibrated")
            print("  → No systematic bias detected")
        
        print("="*70)
        
        return yes_results, no_results
    
    def print_summary_statistics(self):
        """Print summary statistics about the dataset and calibration"""
        print("\n" + "="*70)
        print("DATASET SUMMARY")
        print("="*70)
        
        print(f"\nTotal trades (BUY only): {len(self.df):,}")
        print(f"Unique markets: {self.df['condition_id'].nunique():,}")
        print(f"Date range: {self.df['trade_timestamp'].min()} to {self.df['trade_timestamp'].max()}")
        
        print(f"\nOverall win rate: {self.df['won'].mean():.2%}")
        print(f"Average price paid: {self.df['price'].mean():.3f} ({self.df['price'].mean()*100:.1f}¢)")
        
        print("\nOutcome distribution:")
        print(self.df['outcome'].value_counts())
        
        print("\nCategories:")
        print(self.df['category'].value_counts().head(10))
        
        # Calculate calibration error
        results = self.calculate_win_rate_by_price(price_bins=20, min_samples=30)
        if len(results) > 0:
            calibration_error = np.abs(
                results['win_rate'] - results['price_midpoint']
            ).mean()
            print(f"\nMean absolute calibration error: {calibration_error:.4f} ({calibration_error*100:.2f}¢)")
        
        print("\n" + "="*70)


def main():
    """Example analysis workflow"""
    
    # Load most recent data file
    data_dir = Path("polymarket_data")
    data_files = list(data_dir.glob("polymarket_trades_*.csv"))
    
    if not data_files:
        print("No data files found! Run polymarket_data_collector.py first.")
        return
    
    latest_file = max(data_files, key=lambda p: p.stat().st_mtime)
    print(f"Loading data from: {latest_file}")
    
    # Create analyzer
    analyzer = PolymarketAnalyzer(str(latest_file))
    
    # Print summary
    analyzer.print_summary_statistics()
    
    # Main plot: win rate vs price (all data)
    print("\nGenerating main plot...")
    results = analyzer.plot_win_rate_vs_price(
        price_bins=20,
        min_samples=50,
        save_path='polymarket_data/win_rate_analysis.png'
    )
    
    # Analyze by time to resolution
    print("\nAnalyzing by time to resolution...")
    analyzer.analyze_by_time_to_resolution()
    
    # Analyze by category
    print("\nAnalyzing by category...")
    analyzer.analyze_by_category()
    
    # YES vs NO comparison
    print("\nAnalyzing YES vs NO contracts...")
    yes_results, no_results = analyzer.analyze_yes_vs_no(
        price_bins=20,
        min_samples=30,
        save_path='polymarket_data/yes_vs_no_analysis.png'
    )
    
    # Show calibration table
    print("\nCalibration by Price Bucket:")
    print(results[['price_midpoint', 'win_rate', 'n_trades', 'n_markets']].to_string(index=False))


if __name__ == "__main__":
    main()