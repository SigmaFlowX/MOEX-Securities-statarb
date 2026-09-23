import requests
import json
import pandas as pd


def get_candles(symbol, start_date, end_date, interval=10, engine="stock", market="shares", board="TQBR", show=False):
    url = f"https://iss.moex.com/iss/engines/{engine}/markets/{market}/boards/{board}/securities/{symbol}/candles.json"

    session = requests.Session()
    all_dfs = []
    start = 0
    while True:
        params = {
            "start": start,
            "from": start_date,
            "till": end_date,
            "interval": interval,
        }

        response = session.get(url, params=params, timeout=30)
        data = response.json()

        candles = data.get("candles", {})
        rows = candles.get("data", [])
        cols = candles.get("columns", [])

        all_dfs.append(pd.DataFrame(rows, columns=cols))

        if show:
            print(all_dfs[-1]['begin'].iloc[-1])

        if len(rows) < 500:
            break
        start += 500

    if not all_dfs:
        return pd.DataFrame()

    df = pd.concat(all_dfs, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["begin"])
    df.set_index("timestamp", inplace=True)
    df.drop(columns=["begin"], inplace=True)

    return df

def get_all_futures():
    url = "https://iss.moex.com/iss/statistics/engines/futures/markets/forts/series.json"

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()['series']

    columns = data['columns']
    rows = data["data"]

    futures = [dict(zip(columns, row)) for row in rows]

    return futures


def main():
    print(get_all_futures())

if __name__ == "__main__":
    main()