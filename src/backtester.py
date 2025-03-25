# src/backtester.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional

from src.config_loader import load_config
from src.data_fetcher import fetch_historical_data
from src.strategies import Strategy, MovingAverageCrossoverStrategy # Import specific strategies as needed

class Backtester:
    """
    Simulates a trading strategy on historical data and evaluates its performance.
    """
    def __init__(self, config: Dict[str, Any], strategy_instance: Strategy, data: pd.DataFrame):
        """
        Initializes the Backtester.

        Args:
            config (Dict[str, Any]): The configuration dictionary.
            strategy_instance (Strategy): An instantiated strategy object.
            data (pd.DataFrame): DataFrame containing historical market data with signals.
                                  Must include 'close' and 'signal' columns.
        """
        self.config = config
        self.strategy = strategy_instance
        self.data = data.copy() # Work on a copy to avoid modifying original data
        self.initial_capital = float(config.get('backtesting', {}).get('initial_capital', 10000.0))
        self.trading_pair = config.get('trading', {}).get('pair', 'UNKNOWN')
        self.results: Optional[pd.DataFrame] = None # Initialize results attribute

        if 'close' not in self.data.columns or 'signal' not in self.data.columns:
            raise ValueError("Input data for Backtester must contain 'close' and 'signal' columns.")

    def run(self) -> pd.DataFrame:
        """
        Runs the backtest simulation.

        Returns:
            pd.DataFrame: DataFrame containing the backtest results, including portfolio value over time.
        """
        print(f"\nRunning backtest for {self.trading_pair}...")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")

        # Use self.data directly now that it's a copy
        self.data['position'] = 0.0  # Shares/units held
        self.data['cash'] = self.initial_capital
        self.data['asset_value'] = 0.0
        self.data['portfolio_value'] = self.initial_capital
        self.data['returns'] = 0.0 # Daily returns

        current_position = 0.0 # Shares/units held
        cash = self.initial_capital

        # Use iterrows for explicit row access, though it can be slower for very large datasets
        for index, row in self.data.iterrows():
            # Skip first row if needed depending on signal generation (diff() creates NaN)
            if pd.isna(row['signal']):
                # Carry forward initial state for rows before first signal
                self.data.loc[index, 'cash'] = cash
                self.data.loc[index, 'position'] = current_position
                self.data.loc[index, 'asset_value'] = current_position * row['close'] if not pd.isna(row['close']) else 0
                self.data.loc[index, 'portfolio_value'] = cash + self.data.loc[index, 'asset_value']
                continue

            signal = row['signal']
            close_price = row['close']

            # Find previous portfolio value (handle potential index gaps if any)
            prev_index = self.data.index.get_loc(index) - 1
            if prev_index < 0:
                 prev_portfolio_value = self.initial_capital
            else:
                 prev_portfolio_value = self.data['portfolio_value'].iloc[prev_index]


            # --- Trading Logic ---
            # Buy Signal (and not already long)
            if signal == 1 and cash > 0 and not pd.isna(close_price) and close_price > 0: # Simple: use all cash to buy
                current_position = cash / close_price
                cash = 0.0
                print(f"{index.date()} BUY signal @ {close_price:.2f}. Holding: {current_position:.4f} units.")

            # Sell Signal (and currently long)
            elif signal == -1 and current_position > 0 and not pd.isna(close_price):
                cash = current_position * close_price
                current_position = 0.0
                print(f"{index.date()} SELL signal @ {close_price:.2f}. Cash: ${cash:,.2f}")

            # Update state for the current time step *after* potential trade
            asset_value = current_position * close_price if not pd.isna(close_price) else 0
            current_portfolio_value = cash + asset_value

            self.data.loc[index, 'cash'] = cash
            self.data.loc[index, 'position'] = current_position
            self.data.loc[index, 'asset_value'] = asset_value
            self.data.loc[index, 'portfolio_value'] = current_portfolio_value

            # Calculate returns based on portfolio value change
            if prev_portfolio_value != 0:
                 self.data.loc[index, 'returns'] = (current_portfolio_value / prev_portfolio_value) - 1

        print("Backtest finished.")
        self.results = self.data # Store results internally
        return self.results

    def calculate_performance(self) -> Dict[str, Any]:
        """
        Calculates basic performance metrics from the backtest results.

        Returns:
            Dict[str, Any]: A dictionary containing performance metrics.
        """
        if self.results is None:
            raise RuntimeError("Backtest must be run before calculating performance.")

        final_portfolio_value = self.results['portfolio_value'].iloc[-1]
        total_return_pct = ((final_portfolio_value / self.initial_capital) - 1) * 100

        # Simple Sharpe Ratio (Risk-Free Rate = 0 for simplicity)
        # Exclude initial zero return if present
        daily_returns = self.results['returns'].iloc[1:] # Assuming first return is 0 or NaN
        if daily_returns.std() != 0 and not pd.isna(daily_returns.std()):
             sharpe_ratio = np.sqrt(252) * (daily_returns.mean() / daily_returns.std()) # Annualized (assuming daily data)
        else:
             sharpe_ratio = 0.0

        # Max Drawdown
        rolling_max = self.results['portfolio_value'].cummax()
        daily_drawdown = (self.results['portfolio_value'] / rolling_max) - 1
        max_drawdown_pct = daily_drawdown.min() * 100 if not pd.isna(daily_drawdown.min()) else 0.0

        performance = {
            "Final Portfolio Value": f"${final_portfolio_value:,.2f}",
            "Total Return (%)": f"{total_return_pct:.2f}%",
            "Annualized Sharpe Ratio": f"{sharpe_ratio:.2f}",
            "Max Drawdown (%)": f"{max_drawdown_pct:.2f}%",
        }
        print("\nPerformance Metrics:")
        for key, value in performance.items():
            print(f"- {key}: {value}")
        return performance

    def plot_results(self):
        """
        Plots the portfolio value and buy/sell signals over time.
        """
        if self.results is None:
            raise RuntimeError("Backtest must be run before plotting results.")

        plt.style.use('seaborn-v0_8-darkgrid') # Use a nice style
        plt.figure(figsize=(14, 8))

        # Plot Portfolio Value
        ax1 = plt.subplot(2, 1, 1)
        self.results['portfolio_value'].plot(ax=ax1, label='Portfolio Value', color='blue')
        ax1.set_title(f'{self.trading_pair} Backtest Performance ({self.strategy.__class__.__name__})')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.legend()
        ax1.grid(True)

        # Plot Close Price and Signals
        ax2 = plt.subplot(2, 1, 2, sharex=ax1)
        self.results['close'].plot(ax=ax2, label='Close Price', color='black', alpha=0.8)

        # Plot Buy signals
        buy_signals = self.results[self.results['signal'] == 1]
        ax2.plot(buy_signals.index, self.results.loc[buy_signals.index, 'close'],
                 '^', markersize=8, color='lime', lw=0, label='Buy Signal') # Changed color

        # Plot Sell signals
        sell_signals = self.results[self.results['signal'] == -1]
        ax2.plot(sell_signals.index, self.results.loc[sell_signals.index, 'close'],
                 'v', markersize=8, color='red', lw=0, label='Sell Signal') # Changed color

        ax2.set_ylabel('Price ($)')
        ax2.set_xlabel('Date')
        ax2.legend()
        ax2.grid(True)

        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    try:
        # 1. Load Config
        # Assuming config.yaml is in the parent directory relative to src/
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file_path = os.path.join(project_root, 'config.yaml')
        cfg = load_config(config_file_path)

        # 2. Fetch Data
        backtest_cfg = cfg.get('backtesting', {})
        trading_cfg = cfg.get('trading', {})
        ticker = trading_cfg.get('pair', 'BTC-USD')
        start_date = backtest_cfg.get('start_date', '2023-01-01')
        end_date = backtest_cfg.get('end_date', '2024-01-01')

        data = fetch_historical_data(ticker, start_date, end_date)

        if data is not None:
            # 3. Select and Instantiate Strategy (Example: MA Crossover)
            # Find the first enabled strategy in the config
            enabled_strategy_name = None
            strategy_params = None
            for name, params in cfg.get('strategies', {}).items():
                if params.get('enabled', False):
                    enabled_strategy_name = name
                    strategy_params = params
                    print(f"Using enabled strategy: {enabled_strategy_name}")
                    break # Use the first one found

            if not enabled_strategy_name or not strategy_params:
                 print(f"No enabled strategy found in config. Exiting.")
                 exit()

            # --- Strategy Factory (Simple Example) ---
            if enabled_strategy_name == 'moving_average_crossover':
                strategy_instance = MovingAverageCrossoverStrategy(strategy_params)
            # Add elif for other strategies (e.g., RSI) here
            # elif enabled_strategy_name == 'rsi':
            #     from src.strategies import RsiStrategy # Assuming it exists
            #     strategy_instance = RsiStrategy(strategy_params)
            else:
                raise ValueError(f"Unknown or unsupported strategy specified: {enabled_strategy_name}")
            # --- End Strategy Factory ---


            # 4. Generate Signals
            data_with_signals = strategy_instance.generate_signals(data)

            # 5. Initialize and Run Backtester
            backtester = Backtester(cfg, strategy_instance, data_with_signals)
            results_df = backtester.run()

            # 6. Calculate and Print Performance
            performance_metrics = backtester.calculate_performance()

            # 7. Plot Results
            backtester.plot_results()

        else:
            print(f"Failed to fetch data for {ticker}. Cannot run backtest.")

    except (FileNotFoundError, ValueError, RuntimeError, KeyError) as e:
        print(f"An error occurred during backtesting setup or execution: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")