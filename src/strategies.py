from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd


class Strategy(ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, params: dict[str, Any]):
        self.params = params

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates trading signals based on the input data.

        Args:
            data (pd.DataFrame): DataFrame with historical market data,
                                 must include at least a 'close' column.

        Returns:
            pd.DataFrame: The input DataFrame with an added 'signal' column.
                          Signal values: 1 for buy, -1 for sell, 0 for hold.
        """

        pass


class MovingAverageCrossoverStrategy(Strategy):
    """Implements the Moving Average Crossover strategy."""

    def __init__(self, params: dict[str, Any]):
        super().__init__(params)

        self.short_window = int(params.get("short_window", 10))
        self.long_window = int(params.get("long_window", 50))

        if self.short_window >= self.long_window:
            raise ValueError(
                "Short window must be smaller than long window for MA Crossover."
            )

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates buy/sell signals based on MA crossovers.

        Args:
            data (pd.DataFrame): DataFrame with historical market data,
                                 must include a 'close' column.

        Returns:
            pd.DataFrame: DataFrame with 'short_ma', 'long_ma', and 'signal' columns added.
        """

        if "close" not in data.columns:
            raise ValueError(
                "Dataframe must contain 'close' column for MA Crossover strategy."
            )

        signals_df = data.copy()
        signals_df["signal"] = 0.0  # Initialize signal column

        # Calculate moving averages
        signals_df["short_ma"] = (
            signals_df["close"].rolling(window=self.short_window, min_periods=1).mean()
        )
        signals_df["long_ma"] = (
            signals_df["close"].rolling(window=self.long_window, min_periods=1).mean()
        )

        # Generate signals: 1 for buy (short > long), -1 for sell (short < long)

        # Use shift(1) to compare current MA with the previous period's MA to avoid lookahead bias
        # Create a position indicator: 1 if short > long, 0 otherwise
        signals_df["position_indicator"] = np.where(
            signals_df["short_ma"] > signals_df["long_ma"], 1.0, 0.0
        )

        # Calculate the difference between consecutive position indicators to find crossovers

        # A change from 0 to 1 is a buy signal (diff = 1)
        # A change from 1 to 0 is a sell signal (diff = -1)
        signals_df["signal"] = signals_df["position_indicator"].diff()

        # Drop the intermediate 'position_indicator' column
        signals_df = signals_df.drop(columns=["position_indicator"])

        print(
            f"Generated signals using MA Crossover (Short: {self.short_window}, Long: {self.long_window})"
        )

        return signals_df


# Example usage (optional, can be added within if __name__ == '__main__')
if __name__ == "__main__":
    # No need to import numpy again if imported globally
    from data_fetcher import fetch_historical_data

    # Fetch sample data
    test_ticker = "BTC-USD"
    test_start = "2023-01-01"
    test_end = "2024-01-01"
    sample_data = fetch_historical_data(test_ticker, test_start, test_end)

    if sample_data is not None:
        # Define strategy parameters
        ma_params = {"short_window": 20, "long_window": 50}
        ma_strategy = MovingAverageCrossoverStrategy(ma_params)

        # Generate signals
        signals = ma_strategy.generate_signals(sample_data)

        print("\nSignals DataFrame head:")
        print(signals.head())

        print("\nSignals DataFrame tail:")
        print(signals.tail())

        # Check signal distribution (NaNs are expected at the start due to diff())
        print("\nSignal distribution:")
        print(signals["signal"].value_counts(dropna=False))  # Include NaNs

        # Plotting example (requires matplotlib)
        try:
            import matplotlib.pyplot as plt

            plt.figure(figsize=(12, 6))
            plt.plot(signals.index, signals["close"], label="Close Price")
            plt.plot(
                signals.index,
                signals["short_ma"],
                label=f"Short MA ({ma_params['short_window']})",
                alpha=0.7,
            )
            plt.plot(
                signals.index,
                signals["long_ma"],
                label=f"Long MA ({ma_params['long_window']})",
                alpha=0.7,
            )

            # Plot Buy signals (where signal == 1)
            plt.plot(
                signals[signals["signal"] == 1].index,
                signals["short_ma"][signals["signal"] == 1],
                "^",
                markersize=10,
                color="g",
                lw=0,
                label="Buy Signal",
            )

            # Plot Sell signals (where signal == -1)
            plt.plot(
                signals[signals["signal"] == -1].index,
                signals["short_ma"][signals["signal"] == -1],
                "v",
                markersize=10,
                color="r",
                lw=0,
                label="Sell Signal",
            )

            plt.title(f"{test_ticker} MA Crossover Strategy")
            plt.legend()
            plt.show()
        except ImportError:
            print("\nMatplotlib not installed. Skipping plot.")
        except Exception as e:
            print(f"\nError during plotting: {e}")

    else:
        print("Could not fetch sample data for strategy example.")
