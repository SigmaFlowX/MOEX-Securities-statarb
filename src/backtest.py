import pandas as pd
import numpy as np
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
    timestamps = df['timestamp'].values

    z = df['z_score'].values
    a = df['a'].values

    pos = 0
    pnls = []
    ts = []
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

                ts.append(timestamps[i])
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
                ts.append(timestamps[i])

    return pnls, ts

def plot_equity_curve(pnls, ts):

    equity = pd.Series(np.cumsum(pnls), index=pd.to_datetime(ts))

    running_max = equity.cummax()
    drawdown = equity - running_max

    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                              gridspec_kw={'height_ratios': [3, 1]})

    axes[0].plot(equity.index, equity.values, label='Equity', color='steelblue')
    axes[0].set_ylabel('Cumulative PnL')
    axes[0].set_title('Equity Curve')
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].fill_between(drawdown.index, drawdown.values, 0, color='indianred', alpha=0.6)
    axes[1].set_ylabel('Drawdown')
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    plt.show()

    print(f"Total PnL: {equity.iloc[-1]:.2f}")
    print(f"Max Drawdown: {drawdown.min():.2f}")
    print(f"Num trades: {len(pnls)}")
    print(f"Win rate: {(np.array(pnls) > 0).mean():.2%}")
    if np.std(pnls) > 0:
        sharpe_per_trade = np.mean(pnls) / np.std(pnls)
        print(f"Sharpe per trade: {sharpe_per_trade:.3f}")

    return equity, drawdown

def main():
    name = "SBERF-SBER"

    data = pd.read_csv(DATA_DIR / name)

    data = prepare_df(data, 10, 100)
    pnl, ts = run_backtest(data, 2,1, 0.005)

    plot_equity_curve(pnl, ts)

if __name__ == "__main__":
    main()