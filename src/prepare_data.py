import pandas as pd
from moex_api import get_all_futures
from moex_api import get_candles
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def prepare_data():
    futures = get_all_futures()

    for i, future in enumerate(futures):

        # if i < 130: #to not rewrite existant data
            #continue

        futures_ticker = future['secid']
        underlying_ticker = future['underlying_asset']

        print(i, len(futures))

        try:
            future_candles = get_candles(
                futures_ticker,
                date(2020, 1, 1),
                date(2026, 9, 23),
                sort='futures'
            )

            if  future_candles.empty: #only works with futures-share pairs  for now
                continue

            underlying_candles = get_candles(
                underlying_ticker,
                future_candles['timestamp'].iloc[0],
                date(2026, 9, 23),
                sort='shares'
            )

            if underlying_candles.empty: #only works with futures-share pairs  for now
                continue

            df = pd.merge_asof(
                underlying_candles,
                future_candles,
                on='timestamp',
                suffixes = ("_futures", "_share"),
                tolerance=pd.Timedelta("5m")
            )


            df = df[['timestamp', 'open_share', 'open_futures','close_share', 'close_futures']]
            df.to_csv(DATA_DIR / f"{futures_ticker}-{underlying_ticker}", index=False)
            print(f"saved {underlying_ticker}")


        except Exception as e:
            print(f"Failed at {future['secid']} \n: {e}")





def main():
    prepare_data()

if __name__ == "__main__":
    main()