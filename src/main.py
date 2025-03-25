# src/main.py
import argparse
import logging
import schedule
import time
import sys
import os
import pandas as pd # Import pandas for type hinting if needed
from typing import Dict, Any # Import Dict and Any

# Ensure the src directory is in the Python path when running main.py directly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.config_loader import load_config
from src.data_fetcher import fetch_historical_data
from src.strategies import Strategy, MovingAverageCrossoverStrategy # Add other strategies here
# from src.strategies import RsiStrategy # Example
from src.backtester import Backtester
from src.exchange import ExchangeInterface, CoinbaseExchange # Add other exchanges here

# --- Strategy Mapping ---
# Maps strategy names in config to their respective classes
STRATEGY_MAP: dict[str, type[Strategy]] = {
    'moving_average_crossover': MovingAverageCrossoverStrategy,
    # 'rsi': RsiStrategy, # Add other strategies here
}

# --- Exchange Mapping ---
EXCHANGE_MAP: dict[str, type[ExchangeInterface]] = {
    'coinbase': CoinbaseExchange,
    # Add other exchanges here
}


def setup_logging(log_level_str: str):
    """Configures basic logging."""
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(level=log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    # Add a handler to also print logs to stdout
    # stream_handler = logging.StreamHandler(sys.stdout)
    # stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    # logging.getLogger().addHandler(stream_handler) # Add to root logger
    logging.info(f"Logging level set to {log_level_str.upper()}")

def get_strategy_instance(config: Dict[str, Any]) -> Strategy | None:
    """Finds the enabled strategy in config and returns an instance."""
    enabled_strategy_name = None
    strategy_params = None
    for name, params in config.get('strategies', {}).items():
        if params and params.get('enabled', False): # Check if params dict exists
            enabled_strategy_name = name
            strategy_params = params
            logging.info(f"Using enabled strategy: {enabled_strategy_name}")
            break

    if not enabled_strategy_name or not strategy_params:
         logging.error("No enabled strategy found in config.")
         return None

    StrategyClass = STRATEGY_MAP.get(enabled_strategy_name)
    if not StrategyClass:
        logging.error(f"Strategy class for '{enabled_strategy_name}' not found in STRATEGY_MAP.")
        return None

    try:
        strategy_instance = StrategyClass(strategy_params)
        logging.info(f"Instantiated strategy: {enabled_strategy_name} with params: {strategy_params}")
        return strategy_instance
    except Exception as e:
        logging.error(f"Error instantiating strategy '{enabled_strategy_name}': {e}")
        return None


def run_backtest(config: Dict[str, Any]):
    """Runs the backtesting process based on the config."""
    logging.info("Starting backtesting mode...")

    backtest_cfg = config.get('backtesting', {})
    trading_cfg = config.get('trading', {})
    ticker = trading_cfg.get('pair', 'BTC-USD')
    start_date = backtest_cfg.get('start_date', '2023-01-01')
    end_date = backtest_cfg.get('end_date', '2024-01-01')
    data_source = backtest_cfg.get('data_source', 'yfinance') # Default to yfinance

    # --- Fetch Data ---
    logging.info(f"Fetching data for {ticker} from {start_date} to {end_date} using {data_source}...")
    data: pd.DataFrame | None = None
    if data_source == 'yfinance':
        data = fetch_historical_data(ticker, start_date, end_date)
    # Add elif for other data sources (e.g., reading from CSV, Coinbase API)
    # elif data_source == 'coinbase':
    #     exchange_name = config.get('exchange', 'coinbase') # Assume default exchange if not specified
    #     ExchangeClass = EXCHANGE_MAP.get(exchange_name)
    #     if not ExchangeClass:
    #          logging.error(f"Exchange class for '{exchange_name}' not found.")
    #          return
    #     exchange = ExchangeClass(config) # Requires API keys for historical data too
    #     # Note: Coinbase v2 granularity needs care, 86400 is daily
    #     data = exchange.get_historical_data(ticker, granularity='86400', start=start_date, end=end_date)
    else:
        logging.error(f"Unsupported data_source specified: {data_source}")
        return

    if data is None:
        logging.error(f"Failed to fetch data for {ticker}. Aborting backtest.")
        return
    logging.info(f"Successfully fetched {len(data)} data points.")

    # --- Get Strategy Instance ---
    strategy_instance = get_strategy_instance(config)
    if not strategy_instance:
        logging.error("Failed to instantiate strategy. Aborting backtest.")
        return

    # --- Generate Signals ---
    logging.info("Generating trading signals...")
    try:
        data_with_signals = strategy_instance.generate_signals(data)
        logging.info("Signals generated successfully.")
    except Exception as e:
        logging.error(f"Error generating signals: {e}")
        return

    # --- Initialize and Run Backtester ---
    logging.info("Initializing backtester...")
    try:
        backtester = Backtester(config, strategy_instance, data_with_signals)
        logging.info("Running backtest simulation...")
        backtester.run() # Run the backtest, results are stored internally
    except Exception as e:
        logging.error(f"Error during backtest initialization or run: {e}")
        return

    # --- Calculate and Display Performance ---
    logging.info("Calculating performance metrics...")
    try:
        performance_metrics = backtester.calculate_performance()
        # Nicer logging for performance
        log_msg = "Backtest Performance:\n"
        for key, value in performance_metrics.items():
            log_msg += f"  - {key}: {value}\n"
        logging.info(log_msg.strip())
    except Exception as e:
        logging.error(f"Error calculating performance: {e}")
        # Continue to plotting if possible

    # --- Plot Results ---
    logging.info("Plotting backtest results...")
    try:
        backtester.plot_results()
        logging.info("Plot displayed (or saved if backend non-interactive).")
    except Exception as e:
        logging.error(f"Error plotting results: {e}")

    logging.info("Backtesting finished.")


def run_live(config: Dict[str, Any]):
    """Runs the live trading bot (Simulated Orders)."""
    logging.info("Starting live trading mode (SIMULATED ORDERS)...")

    # --- Initialize Exchange ---
    exchange_name = config.get('exchange', 'coinbase') # Assume default exchange if not specified
    ExchangeClass = EXCHANGE_MAP.get(exchange_name)
    if not ExchangeClass:
         logging.error(f"Exchange class for '{exchange_name}' not found.")
         return
    exchange = ExchangeClass(config)
    if not exchange.client:
        logging.error("Cannot start live trading: Exchange client not initialized (check API keys).")
        return
    logging.info(f"Initialized exchange: {exchange_name}")

    # --- Get Strategy ---
    strategy_instance = get_strategy_instance(config)
    if not strategy_instance:
        logging.error("Failed to instantiate strategy. Aborting live mode.")
        return

    # --- Trading Parameters ---
    trading_cfg = config.get('trading', {})
    pair = trading_cfg.get('pair', 'BTC-USD')
    # Example: trade every hour. Granularity should match strategy needs.
    trading_interval_minutes = int(trading_cfg.get('interval_minutes', 60))
    # Example: Fixed amount to trade in quote currency (e.g., $10)
    trade_amount_quote = float(trading_cfg.get('trade_amount_quote', 10.0))
    # Example: Amount of base currency to sell (e.g., sell all available) - Use 'all' or a float
    trade_amount_base_sell = trading_cfg.get('trade_amount_base_sell', 'all') # 'all' or float

    logging.info(f"Trading Pair: {pair}")
    logging.info(f"Trading Interval: {trading_interval_minutes} minutes")
    logging.info(f"Trade Amount (Buy Quote): {trade_amount_quote}")
    logging.info(f"Trade Amount (Sell Base): {trade_amount_base_sell}")


    # --- Live Trading Job ---
    def trading_job():
        logging.info(f"----- Running Trading Job for {pair} -----")
        try:
            # 1. Fetch latest data needed for strategy
            #    WARNING: Using yfinance is NOT suitable for live trading due to delays/accuracy.
            #    Use exchange.get_historical_data or ideally a websocket feed.
            #    This is a placeholder structure.
            logging.warning("Using yfinance for recent data - Placeholder, NOT suitable for live trading!")
            # Determine required data length (e.g., max lookback window + buffer)
            required_periods = 50 # Default, adjust based on strategy
            if hasattr(strategy_instance, 'long_window'):
                 required_periods = strategy_instance.long_window + 5
            elif hasattr(strategy_instance, 'period'): # e.g., for RSI
                 required_periods = strategy_instance.period + 5

            # Fetch recent data - Adjust interval/count as needed. yfinance is problematic here.
            # Example: Fetch recent hourly data. Adjust interval as needed.
            # A better approach would fetch hourly/minutely data from the exchange API
            recent_data = fetch_historical_data(ticker=pair, start_date=None, end_date=None, interval='1h') # Placeholder!
            if recent_data is None or len(recent_data) < required_periods:
                 logging.error(f"Could not fetch sufficient recent data ({len(recent_data) if recent_data is not None else 0} < {required_periods}). Skipping job.")
                 return

            # 2. Generate signal on the latest data
            signals = strategy_instance.generate_signals(recent_data)
            latest_signal = signals['signal'].iloc[-1]
            latest_price = signals['close'].iloc[-1] # Price used for signal generation
            latest_timestamp = signals.index[-1]
            logging.info(f"Latest Data Point: {latest_timestamp}, Price: {latest_price:.2f}, Signal: {latest_signal}")

            # 3. Get current balances
            quote_currency = pair.split('-')[1].upper()
            base_currency = pair.split('-')[0].upper()
            quote_balance = exchange.get_account_balance(quote_currency)
            base_balance = exchange.get_account_balance(base_currency)
            logging.info(f"Balances - {quote_currency}: {quote_balance}, {base_currency}: {base_balance}")

            # 4. Simple Position Management (Placeholder - needs persistent state)
            #    In a real bot, track if you are currently holding the base currency.
            #    This example assumes you start flat and only tracks within one job run.
            currently_holding_base = base_balance is not None and base_balance > 0.00001 # Simple check

            # 5. Execute Trade based on Signal (SIMULATED)
            if latest_signal == 1 and not currently_holding_base: # Buy signal
                if quote_balance is not None and quote_balance >= trade_amount_quote:
                    logging.info(f"BUY signal detected. Attempting to buy {trade_amount_quote} {quote_currency} worth of {base_currency}...")
                    order_result = exchange.place_buy_order(pair, amount=trade_amount_quote, order_type='market') # commit=False inside method
                    if order_result:
                        logging.info(f"SIMULATED BUY order placed: {order_result.get('id', 'N/A')}")
                        # TODO: Update persistent position state
                    else:
                        logging.error("SIMULATED BUY order failed.")
                else:
                    logging.warning(f"BUY signal, but insufficient {quote_currency} balance ({quote_balance} < {trade_amount_quote}) or balance fetch failed.")

            elif latest_signal == -1 and currently_holding_base: # Sell signal
                 if base_balance is not None and base_balance > 0:
                     sell_amount = 0.0
                     if trade_amount_base_sell == 'all':
                         sell_amount = base_balance
                     else:
                         try:
                             sell_amount = float(trade_amount_base_sell)
                             if sell_amount > base_balance:
                                 logging.warning(f"Attempting to sell {sell_amount} {base_currency}, but only hold {base_balance}. Selling available amount.")
                                 sell_amount = base_balance
                         except ValueError:
                             logging.error(f"Invalid float value for trade_amount_base_sell: {trade_amount_base_sell}")
                             return # Skip sell

                     if sell_amount > 0: # Ensure there's something to sell
                         logging.info(f"SELL signal detected. Attempting to sell {sell_amount:.8f} {base_currency}...")
                         order_result = exchange.place_sell_order(pair, amount=sell_amount, order_type='market') # commit=False inside method
                         if order_result:
                             logging.info(f"SIMULATED SELL order placed: {order_result.get('id', 'N/A')}")
                             # TODO: Update persistent position state
                         else:
                             logging.error("SIMULATED SELL order failed.")
                     else:
                          logging.info("SELL signal, but calculated sell amount is zero.")
                 else:
                     logging.warning(f"SELL signal, but no {base_currency} balance ({base_balance}) or balance fetch failed.")
            else:
                logging.info("HOLD signal or position/balance prevents action.")

        except Exception as e:
            logging.error(f"Error in trading job: {e}", exc_info=True)
        finally:
             logging.info("----- Trading Job Finished -----")

    # --- Schedule the Job ---
    logging.info(f"Scheduling trading job every {trading_interval_minutes} minutes.")
    schedule.every(trading_interval_minutes).minutes.do(trading_job)

    # Run once immediately for testing
    trading_job()

    while True:
        schedule.run_pending()
        time.sleep(30) # Check schedule every 30 seconds


def main():
    parser = argparse.ArgumentParser(description="Crypto Trading Bot")
    parser.add_argument('--mode', type=str, choices=['backtest', 'live'], default='backtest',
                        help="Operation mode: 'backtest' or 'live'")
    parser.add_argument('--config', type=str, default='config.yaml',
                        help="Path to the configuration file")
    args = parser.parse_args()

    # Define config_path before try block to avoid potential UnboundLocalError
    config_path = args.config
    if not os.path.isabs(config_path):
         config_path = os.path.join(project_root, config_path)

    # Load configuration
    try:
        print(f"Loading configuration from: {config_path}") # Print path before loading
        config = load_config(config_path)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"FATAL: Error loading configuration from {config_path}: {e}")
        sys.exit(1)
    except Exception as e:
         print(f"FATAL: Unexpected error loading configuration: {e}")
         sys.exit(1)


    # Setup logging
    log_level = config.get('log_level', 'INFO')
    setup_logging(log_level)

    logging.info(f"--- Starting Crypto Trading Bot ---")
    logging.info(f"Mode: {args.mode}")
    logging.info(f"Config File: {config_path}")


    if args.mode == 'backtest':
        run_backtest(config)
    elif args.mode == 'live':
        run_live(config)
    else:
        # Should not happen due to argparse choices
        logging.error(f"Invalid mode specified: {args.mode}")
        sys.exit(1)

    logging.info("--- Crypto Trading Bot Finished ---")

if __name__ == "__main__":
    main()