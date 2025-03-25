# Crypto Trading Bot Framework

This project provides a basic framework for developing, backtesting, and (simulated) live trading cryptocurrency strategies in Python. It features a modular design allowing for easy extension with new strategies and exchange integrations.

## Features

*   **Strategy Backtesting:** Simulate trading strategies on historical market data (`yfinance` supported out-of-the-box).
*   **Performance Evaluation:** Calculate key metrics like Total Return, Sharpe Ratio, and Max Drawdown.
*   **Results Visualization:** Plot portfolio value, close prices, and buy/sell signals using Matplotlib.
*   **Configuration Driven:** Control settings via a central `config.yaml` file (API keys, trading pairs, strategy parameters, backtesting dates, etc.).
*   **Modular Strategy Design:** Abstract base class (`Strategy`) to easily implement and plug in new trading logic (e.g., `MovingAverageCrossoverStrategy` included).
*   **Exchange Interface:** Abstract base class (`ExchangeInterface`) for interacting with exchanges (e.g., `CoinbaseExchange` using the `coinbase` v2 API included).
*   **Simulated Live Trading:** Basic scheduler (`schedule` library) to run trading logic periodically, fetches recent data, generates signals, and simulates placing orders on Coinbase (using `commit=False`).
*   **Logging:** Configurable logging to monitor bot activity.

## Project Structure

```
├── src
│   ├── backtester.py       # Runs strategy simulations on historical data
│   ├── config_loader.py    # Loads configuration from config.yaml
│   ├── data_fetcher.py     # Fetches historical market data (using yfinance)
│   ├── exchange.py         # Handles communication with crypto exchanges (Coinbase v2 included)
│   ├── main.py             # Main entry point, argument parsing, orchestration
│   └── strategies.py       # Defines trading strategy logic (MA Crossover example)
├── config.yaml             # Configuration file (API keys, strategy params, etc.)
└── requirements.txt        # Python package dependencies
```

## Requirements

*   Python 3.8+ (recommended)
*   Required libraries are listed in `requirements.txt`:
    *   `requests`
    *   `PyYAML`
    *   `pandas`
    *   `numpy`
    *   `schedule`
    *   `coinbase` (for Coinbase v2 API)
    *   `yfinance` (for historical data)
    *   `matplotlib` (for plotting)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the bot:**
    *   Open the `config.yaml` file.
    *   **Crucially, replace `YOUR_API_KEY` and `YOUR_API_SECRET` under the `coinbase` section with your actual Coinbase API credentials.** You can generate these on the Coinbase website under API settings.
        *   **Required Permissions:** Ensure your API key has permissions like `wallet:user:read`, `wallet:accounts:read`, `wallet:buys:create`, `wallet:sells:create` for the exchange functionality to work correctly (even in simulation mode for checking balances/placing test orders).
    *   Adjust the `trading` pair (e.g., `BTC-USD`, `ETH-EUR`).
    *   Enable/disable strategies under the `strategies` section and configure their parameters (e.g., `short_window`, `long_window` for MA Crossover).
    *   Configure `backtesting` parameters like `start_date`, `end_date`, and `initial_capital`.
    *   Set the desired `log_level` (`INFO`, `DEBUG`, `WARNING`, `ERROR`).

## Usage

The main entry point is `src/main.py`. You can run the bot in different modes using command-line arguments.

### Backtesting Mode

This mode runs your enabled strategy against historical data defined in `config.yaml`, calculates performance metrics, and plots the results.

```bash
python src/main.py --mode backtest --config config.yaml
```

*   `--mode backtest`: Specifies running in backtesting mode (this is the default if `--mode` is omitted).
*   `--config config.yaml`: Specifies the path to the configuration file (default is `config.yaml` in the project root).

The backtester will:
1.  Load configuration.
2.  Fetch historical data (using `yfinance` by default).
3.  Instantiate the enabled strategy.
4.  Generate trading signals.
5.  Run the backtest simulation.
6.  Print performance metrics to the console.
7.  Display plots showing portfolio value and trades (requires a graphical environment).

### Live (Simulated) Mode

This mode runs the trading logic on a schedule, fetches recent data, generates signals, and **simulates** placing orders on the configured exchange (currently Coinbase).

⚠️ **IMPORTANT:** By default, live mode **simulates** orders using `commit=False` in `src/exchange.py`. **No real trades will be executed.**

⚠️ **DATA SOURCE WARNING:** The current live mode example uses `yfinance` to fetch recent data. **`yfinance` data can have significant delays and is NOT suitable for reliable live trading.** For actual live deployment, you should modify `run_live` in `src/main.py` to use real-time data feeds (e.g., exchange websockets) or fetch recent candle data directly from the exchange API (`exchange.get_historical_data`).

```bash
python src/main.py --mode live --config config.yaml
```

*   `--mode live`: Specifies running in live trading mode.
*   `--config config.yaml`: Path to the configuration file.

The live mode will:
1.  Load configuration and initialize the exchange client (requires valid API keys).
2.  Instantiate the enabled strategy.
3.  Schedule a trading job based on `trading: interval_minutes` in `config.yaml`.
4.  Periodically (and once on startup):
    *   Fetch recent market data (**using `yfinance` - see warning above**).
    *   Generate the latest trading signal.
    *   Check account balances on the exchange.
    *   **Simulate** placing buy/sell orders based on the signal and available balance.
    *   Log actions and potential errors.

**To enable actual live trading (USE WITH EXTREME CAUTION):**
1.  You MUST modify the `place_buy_order` and `place_sell_order` methods in `src/exchange.py`.
2.  Change `commit=False` to `commit=True` within the `self.client.buy(...)` and `self.client.sell(...)` calls.
3.  Ensure your data source in `run_live` (`src/main.py`) is reliable and timely for live trading.
4.  Thoroughly test your strategy and configuration before committing real funds.

## Strategies

Trading strategies are defined in `src/strategies.py`.

*   All strategies should inherit from the abstract base class `Strategy`.
*   They must implement the `generate_signals(self, data: pd.DataFrame) -> pd.DataFrame` method.
*   This method takes a pandas DataFrame with market data (must include 'close') and returns the DataFrame with an added 'signal' column (1 for buy, -1 for sell, 0 for hold).
*   To add a new strategy:
    1.  Create a new class inheriting from `Strategy` in `src/strategies.py`.
    2.  Implement the `__init__` method to accept parameters and the `generate_signals` method with your logic.
    3.  Add the strategy class to the `STRATEGY_MAP` dictionary in `src/main.py`.
    4.  Add configuration parameters for your strategy under the `strategies` section in `config.yaml` and set `enabled: true` to use it.

## Exchanges

Exchange interactions are managed via `src/exchange.py`.

*   The `ExchangeInterface` defines the methods that any exchange implementation should provide (e.g., `get_current_price`, `get_account_balance`, `place_buy_order`, `place_sell_order`).
*   `CoinbaseExchange` is provided as an example implementation using the `coinbase` library (for the standard Coinbase V2 API).
    *   **Note:** This library supports basic buy/sell operations but may not cover all features of the Coinbase Advanced Trade API (like specific limit order types). For Advanced Trade features, consider using a library like `ccxt`.
*   To add support for a new exchange:
    1.  Create a new class inheriting from `ExchangeInterface` in `src/exchange.py`.
    2.  Implement the required methods using the exchange's API library.
    3.  Add the exchange class to the `EXCHANGE_MAP` dictionary in `src/main.py`.
    4.  Update `config.yaml` with necessary API keys/settings for the new exchange and configure `main.py` to use it if desired.

## Disclaimer

Trading cryptocurrencies involves significant risk. This software is provided "as is" without warranty of any kind. The authors are not responsible for any financial losses incurred using this framework. Always backtest thoroughly and understand the risks before deploying any trading bot with real funds. The default live mode is strictly for simulation.
