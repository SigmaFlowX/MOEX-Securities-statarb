import pandas as pd
from pathlib import Path
from matplotlib import pyplot as plt
from statsmodels.regression.rolling import RollingOLS
import statsmodels.api as sm
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def prepare_df(df, z_window, ols_window):

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.dropna(subset=['timestamp', 'close_share', 'close_futures'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    y = df['close_share']
    x = sm.add_constant(df['close_futures'])

    rols = RollingOLS(y, x, window=ols_window)
    rres = rols.fit()

    params = rres.params
    df['a'] = params['close_futures'].shift(1)
    df['b'] = params['const'].shift(1)
    df['spread'] = df['close_share'] - (df['a'] * df['close_futures'] + df['b'])

    df['spread_mean'] = df['spread'].rolling(z_window).mean()
    df['spread_std'] = df['spread'].rolling(z_window).std()
    df['z_score'] = (df['spread'] - df['spread_mean']) / df['spread_std']

    df = df.dropna()

    return df

def run_backtest(df, z_entry, z_exit, fee):
    open_share = df['open_share'].values
    open_futures = df['open_futures'].values

    z = df['z_score'].values
    a = df['a'].values

    pos = 0
    pnls = []
    pos_entry_prices = None  #(share_price, futures_price) arr
    pos_entry_a = None
    for i in range(len(open_share)-1):
        if pos == 0:
            long_entry_cond = (
                z[i] < -z_entry
            )

            short_entry_cond = (
                z[i] > z_entry
            )

            if long_entry_cond:
                pos = 1
                pos_entry_prices = (open_share[i+1], open_futures[i+1])
                pos_entry_a = a[i]
            elif short_entry_cond:
                pos = -1
                pos_entry_prices = (open_share[i + 1], open_futures[i + 1])
                pos_entry_a = a[i]
        elif pos==1:
            exit_cond =(
                z[i] > -z_exit
            )

            if exit_cond:
                pos = 0
                share_pnl = open_share[i+1] - pos_entry_prices[0]
                futures_pnl = -pos_entry_a * (open_futures[i+1] - pos_entry_prices[1])

                pnls.append(share_pnl + futures_pnl - 4 * fee)
        elif pos == -1:
            exit_cond = (
                z[i] < z_exit
            )

            if exit_cond:
                pos = 0
                share_pnl = pos_entry_prices[0] - open_share[i+1]
                futures_pnl = pos_entry_a * (open_futures[i+1] - pos_entry_prices[1])

                pnls.append(share_pnl + futures_pnl - 4 * fee)


def main():
    name = "SBERF-SBER"

    data = pd.read_csv(DATA_DIR / name)

    data = prepare_df(data, 10, 100)
    run_backtest(data, 2,1, 0.0005)

if __name__ == "__main__":
    main()