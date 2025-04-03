import pandas as pd
import yfinance as yf


def fetch_historical_data(
    ticker: str, start_date: str, end_date: str, interval: str = "1d"
) -> pd.DataFrame | None:
    """
    Fetches historical market data for a given ticker using yfinance.

    Args:
        ticker (str): The ticker symbol (e.g., 'BTC-USD').
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        interval (str): Data interval (e.g., '1d', '1h'). Note: yfinance crypto
                        support for intervals less than '1d' might be limited.

    Returns:
        Optional[pd.DataFrame]: A pandas DataFrame with the historical data
                                (Open, High, Low, Close, Adj Close, Volume),
                                or None if fetching fails.
                                Index is Datetime.
    """
    print(
        f"Fetching data for {ticker} from {start_date} to {end_date} with interval {interval}..."
    )
    try:
        # Explicitly type hint the expected return type for clarity, though yfinance lacks stubs
        # Set auto_adjust=False to ensure 'Close' column is present instead of just 'Adj Close'
        data: pd.DataFrame | None = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            interval=interval,
            progress=False,
            auto_adjust=False,
        )

        # Check for None first, then empty
        if data is None:
            print(f"Warning: yf.download returned None for {ticker}.")
            return None
        if data.empty:
            print(
                f"Warning: No data found for {ticker} in the specified date range or interval (DataFrame is empty)."
            )
            return None

        # Ensure standard column names (lowercase), handling potential tuples (MultiIndex)
        new_cols = []
        for col in data.columns:
            if isinstance(col, tuple):
                # Join tuple elements (usually strings like ('Adj Close', ''))
                col_str = "_".join(filter(None, map(str, col))).strip(
                    "_"
                )  # Filter out empty strings from tuple
            elif isinstance(col, str):
                col_str = col
            else:
                col_str = str(col)  # Fallback for other types

            # Standardize: lowercase, replace space with underscore
            standardized_col = col_str.lower().replace(" ", "_")

            # Remove ticker suffix if present (e.g., '_btc-usd')
            ticker_suffix = f"_{ticker.lower()}"
            if standardized_col.endswith(ticker_suffix):
                standardized_col = standardized_col[: -len(ticker_suffix)]

            new_cols.append(standardized_col)
        data.columns = new_cols

        print(
            f"Successfully fetched {len(data)} data points."
        )  # len() is safe now due to None/empty checks
        # Removed debug print
        return data

    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None


if __name__ == "__main__":
    # Example usage: Fetch daily BTC-USD data for 2023
    test_ticker = "BTC-USD"
    test_start = "2023-01-01"
    test_end = "2024-01-01"

    historical_data = fetch_historical_data(test_ticker, test_start, test_end)

    if historical_data is not None:
        print("\nSample data:")
        print(historical_data.head())
        print("\nData info:")
        historical_data.info()
    else:
        print(f"\nFailed to fetch data for {test_ticker}.")

    # Example for hourly (might not work for all crypto pairs on yfinance)
    # print("\nAttempting to fetch hourly data (may fail)...")
    # hourly_data = fetch_historical_data(test_ticker, '2024-03-01', '2024-03-05', interval='1h')
    # if hourly_data is not None:
    #     print(hourly_data.head())
