from typing import Any

import pandas as pd
from coinbase.wallet.client import Client

# Removed time, datetime

# Note: The 'coinbase' library primarily supports Coinbase (non-Pro/Advanced).
# For Advanced Trade API features (like market orders, limit orders beyond simple buy/sell),
# using a library like 'ccxt' might be necessary. This implementation uses the basic client.


class ExchangeInterface:
    """Abstract base class for exchange interactions."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    def get_current_price(self, pair: str) -> float | None:
        """Gets the current market price for a trading pair."""
        raise NotImplementedError

    def get_account_balance(self, currency: str) -> float | None:
        """Gets the balance for a specific currency."""
        raise NotImplementedError

    def place_buy_order(
        self, pair: str, amount: float, order_type: str
    ) -> dict[str, Any] | None:
        """
        Places a buy order.
        Args:
            pair (str): Trading pair (e.g., BTC-USD).
            amount (float): Amount to buy (either in base or quote currency depending on order_type).
            order_type (str): 'market' or 'limit'. For market, amount is quote currency. For limit, amount is base currency.
        """
        raise NotImplementedError

    def place_sell_order(
        self, pair: str, amount: float, order_type: str
    ) -> dict[str, Any] | None:
        """
        Places a sell order.
        Args:
            pair (str): Trading pair (e.g., BTC-USD).
            amount (float): Amount of base currency to sell.
            order_type (str): 'market' or 'limit'.
        """
        raise NotImplementedError

    def get_historical_data(
        self,
        pair: str,
        granularity: str,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame | None:
        """Gets historical data directly from the exchange (if supported)."""
        raise NotImplementedError


class CoinbaseExchange(ExchangeInterface):
    """Coinbase exchange interaction implementation."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        api_key = config.get("coinbase", {}).get("api_key")
        api_secret = config.get("coinbase", {}).get("api_secret")

        if not api_key or not api_secret or api_key == "YOUR_API_KEY":
            print(
                "Warning: Coinbase API key/secret not configured. Live trading disabled."
            )
            self.client = None
        else:
            try:
                self.client = Client(api_key, api_secret)
                # Test connection by fetching user info
                user = self.client.get_current_user()
                print(
                    f"Successfully connected to Coinbase API for user: {user.get('name', 'N/A')}"
                )
            except Exception as e:
                print(f"Error connecting to Coinbase API: {e}")
                self.client = None

    def get_current_price(self, pair: str) -> float | None:
        """Gets the current buy price from Coinbase."""
        if not self.client:
            print("Coinbase client not initialized. Cannot fetch price.")
            return None
        try:
            # Use get_buy_price for simplicity, could also use get_spot_price
            price_data = self.client.get_buy_price(currency_pair=pair)
            price = float(price_data["amount"])
            print(f"Current {pair} buy price: {price}")
            return price
        except Exception as e:
            print(f"Error fetching current price for {pair} from Coinbase: {e}")
            return None

    def get_account_balance(self, currency: str) -> float | None:
        """Gets the balance for a specific currency (e.g., 'USD', 'BTC')."""
        if not self.client:
            print("Coinbase client not initialized. Cannot fetch balance.")
            return None
        try:
            accounts = self.client.get_accounts()
            for account in accounts.data:
                if account["currency"] == currency.upper():
                    balance = float(account["balance"]["amount"])
                    print(f"Account balance for {currency}: {balance}")
                    return balance
            print(f"Warning: No account found for currency {currency}.")
            return 0.0  # Return 0 if account not found
        except Exception as e:
            print(f"Error fetching account balance for {currency} from Coinbase: {e}")
            return None

    # --- Simplified Order Placement (Market Orders Only via Buy/Sell endpoints) ---
    # Note: These use the basic 'buy'/'sell' endpoints which act like market orders
    # based on spending/selling a specific amount. They might have different fees/slippage
    # compared to Advanced Trade API market orders.

    def place_buy_order(
        self, pair: str, amount: float, order_type: str = "market"
    ) -> dict[str, Any] | None:
        """
        Places a simple market buy order using a specified amount of the quote currency.
        Requires 'wallet:buys:create' permission.

        Args:
            pair (str): Trading pair (e.g., BTC-USD).
            amount (float): The amount of the quote currency (e.g., USD) to spend.
            order_type (str): Ignored for this basic implementation, assumes market buy.

        Returns:
            Optional[Dict[str, Any]]: Dictionary representing the buy transaction, or None on failure.
        """
        if order_type.lower() != "market":
            print(
                "Warning: Basic Coinbase client only supports market-like buys via amount. Proceeding as market buy."
            )

        if not self.client:
            print("Coinbase client not initialized. Cannot place buy order.")
            return None
        try:
            quote_currency = pair.split("-")[1].upper()

            # Find the primary account for the quote currency (e.g., USD wallet)
            accounts = self.client.get_accounts()
            account_id = None
            for acc in accounts.data:
                # Find account matching the quote currency (e.g., USD)
                if (
                    acc["currency"] == quote_currency
                ):  # Use the wallet of the currency you're spending
                    account_id = acc["id"]
                    break
            if not account_id:
                print(f"Error: Account for {quote_currency} not found.")
                return None

            print(
                f"Attempting to place market BUY order for {amount} {quote_currency} worth of {pair.split('-')[0]}..."
            )
            # Use commit=False for testing without executing
            buy = self.client.buy(
                account_id,
                amount=str(amount),
                currency=quote_currency,  # The currency specified in 'amount'
                commit=False,
            )  # SET TO TRUE FOR ACTUAL EXECUTION

            print(f"Buy order details (commit=False): {buy}")
            if buy and buy.get("id"):
                print(f"Simulated BUY order placed successfully (ID: {buy['id']}).")
                # Real scenario: wait and check status via buy.refresh() or get_buy(account_id, buy['id'])
                return buy
            else:
                print("Simulated BUY order failed or returned unexpected response.")
                return None

        except Exception as e:
            print(f"Error placing buy order on Coinbase: {e}")
            return None

    def place_sell_order(
        self, pair: str, amount: float, order_type: str = "market"
    ) -> dict[str, Any] | None:
        """
        Places a simple market sell order for a specified amount of the base currency.
        Requires 'wallet:sells:create' permission.

        Args:
            pair (str): Trading pair (e.g., BTC-USD).
            amount (float): The amount of the base currency (e.g., BTC) to sell.
            order_type (str): Ignored for this basic implementation, assumes market sell.


        Returns:
            dict[str, Any] | None: Dictionary representing the sell transaction, or None on failure.
        """
        if order_type.lower() != "market":
            print(
                "Warning: Basic Coinbase client only supports market-like sells via amount. Proceeding as market sell."
            )

        if not self.client:
            print("Coinbase client not initialized. Cannot place sell order.")
            return None
        try:
            base_currency = pair.split("-")[0].upper()

            # Find the primary account for the base currency (e.g., BTC wallet)
            accounts = self.client.get_accounts()
            account_id = None
            for acc in accounts.data:
                if (
                    acc["currency"] == base_currency
                ):  # Use the wallet of the currency you're selling
                    account_id = acc["id"]
                    break
            if not account_id:
                print(f"Error: Account for {base_currency} not found.")
                return None

            print(
                f"Attempting to place market SELL order for {amount} {base_currency}..."
            )
            # Use commit=False for testing
            sell = self.client.sell(
                account_id,
                amount=str(amount),  # Correct variable used here
                currency=base_currency,  # The currency specified in 'amount'
                commit=False,
            )  # SET TO TRUE FOR ACTUAL EXECUTION

            print(f"Sell order details (commit=False): {sell}")
            if sell and sell.get("id"):
                print(f"Simulated SELL order placed successfully (ID: {sell['id']}).")
                # Real scenario: wait and check status via sell.refresh() or get_sell(account_id, sell['id'])
                return sell
            else:
                print("Simulated SELL order failed or returned unexpected response.")
                return None

        except Exception as e:
            print(f"Error placing sell order on Coinbase: {e}")
            return None

    def get_historical_data(
        self,
        pair: str,
        granularity: str,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame | None:
        """
        Gets historical data (candles) from Coinbase API v2 (get_historic_prices).
        Granularity must be one of [60, 300, 900, 3600, 21600, 86400]. (seconds)
        Returns up to 300 candles ending before 'end' (or now if 'end' is None).
        Does NOT support pagination easily with this endpoint.
        Consider using the Advanced Trade API (e.g., via ccxt) for better historical data access.
        """
        if not self.client:
            print("Coinbase client not initialized. Cannot fetch historical data.")
            return None

        valid_granularities = [60, 300, 900, 3600, 21600, 86400]
        try:
            granularity_sec = int(granularity)
            if granularity_sec not in valid_granularities:
                raise ValueError(
                    f"Invalid granularity. Must be one of {valid_granularities}"
                )
        except ValueError:
            raise ValueError(
                f"Granularity must be an integer in seconds. Got: {granularity}"
            )

        print(
            f"Fetching historical data for {pair} with granularity {granularity_sec}s (max 300 candles)..."
        )
        try:
            # Note: start/end params for get_historic_prices might not work as expected for pagination.
            # This endpoint is simpler but less flexible than Advanced Trade API.
            candles = self.client.get_historic_prices(
                currency_pair=pair,
                granularity=granularity_sec,
                # start=start, # May not be supported or reliable
                # end=end      # May not be supported or reliable
            )

            # Response format is {'prices': [[time, low, high, open, close, volume], ...]}
            if not candles or "prices" not in candles or not candles["prices"]:
                print(f"No historical prices received from Coinbase for {pair}.")
                return None

            prices = candles["prices"]
            print(f"Fetched {len(prices)} candles from Coinbase.")

            # Convert to DataFrame
            df = pd.DataFrame(
                prices, columns=["time", "low", "high", "open", "close", "volume"]
            )
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df = df.set_index("time")
            df = df.astype(float)
            df = df.sort_index()  # Ensure chronological order
            print(f"Converted {len(df)} candles to DataFrame.")
            return df

        except Exception as e:
            print(f"Error fetching historical data from Coinbase: {e}")
            return None


# Example Usage (requires valid API keys in config.yaml for most actions)
if __name__ == "__main__":
    try:
        import os

        # Need to import load_config here when running as script/module main
        from src.config_loader import load_config

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file_path = os.path.join(project_root, "config.yaml")
        cfg = load_config(config_file_path)

        exchange = CoinbaseExchange(cfg)

        if exchange.client:  # Only proceed if client initialized
            # --- Get Price ---
            pair = cfg.get("trading", {}).get("pair", "BTC-USD")
            current_price = exchange.get_current_price(pair)
            if current_price:
                print(f"Retrieved current price for {pair}: {current_price}")

            # --- Get Balance ---
            usd_balance = exchange.get_account_balance("USD")
            base_currency = pair.split("-")[0]
            base_balance = exchange.get_account_balance(base_currency)

            # --- Place Orders (Simulated with commit=False) ---
            if (
                usd_balance is not None and usd_balance > 10
            ):  # Example: Buy $10 worth if balance > $10
                print("\nSimulating Buy Order...")
                # Use 'amount' parameter name
                buy_info = exchange.place_buy_order(pair, amount=10.0)
                # print(f"Simulated Buy Info: {buy_info}")
            else:
                print(
                    "\nSkipping simulated buy (insufficient USD balance or fetch failed)."
                )

            if (
                base_balance is not None and base_balance > 0.0001
            ):  # Example: Sell 0.0001 units if available
                print("\nSimulating Sell Order...")
                # Use 'amount' parameter name
                sell_info = exchange.place_sell_order(pair, amount=0.0001)
                # print(f"Simulated Sell Info: {sell_info}")
            else:
                print(
                    f"\nSkipping simulated sell (insufficient {base_currency} balance or fetch failed)."
                )

            # --- Get Historical Data ---
            print("\nFetching historical data from Coinbase (max 300 candles)...")
            # Fetch last ~300 hours of data (300 candles * 3600s granularity)
            hist_data = exchange.get_historical_data(
                pair, granularity="3600"
            )  # Fetch most recent
            if hist_data is not None:
                print("Sample historical data from Coinbase:")
                print(hist_data.head())
                print(hist_data.tail())
            else:
                print("Could not fetch historical data from Coinbase.")

        else:
            print("\nCoinbase client not initialized. Skipping API calls.")

    except Exception as e:
        print(f"An error occurred in the exchange example: {e}")
