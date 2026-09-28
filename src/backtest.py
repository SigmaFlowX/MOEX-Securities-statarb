import pandas as pd
import numpy as np
from pathlib import Path
from matplotlib import pyplot as plt
from statsmodels.regression.rolling import RollingOLS
import statsmodels.api as sm
from dateutil.relativedelta import relativedelta
import optuna

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

def objective(trial, df, fee):
    df = df.copy()


    z_entry = trial.suggest_float('z_entry', 0.0, 5)
    z_exit = trial.suggest_float('z_exit', 0.0, z_entry)
    z_window = trial.suggest_int('z_window', 0, 100)
    ols_window = trial.suggest_int('ols_window', 10, 1000)

    df = prepare_df(df, z_window, ols_window)

    pnls, _ = run_backtest(df, z_entry, z_exit, fee)


    return sum(pnls)

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
                share_pnl = (open_share[i+1] - pos_entry_prices[0])/pos_entry_prices[0]
                futures_pnl = -pos_entry_a * (open_futures[i+1] - pos_entry_prices[1])/pos_entry_prices[1]

                ts.append(timestamps[i+1])
                pnls.append(share_pnl + futures_pnl - 4 * fee)
        elif pos == -1:
            exit_cond = (
                z[i] < z_exit
            )

            if exit_cond:
                pos = 0
                share_pnl = (pos_entry_prices[0] - open_share[i+1])/pos_entry_prices[0]
                futures_pnl = pos_entry_a * (open_futures[i+1] - pos_entry_prices[1])/pos_entry_prices[1]

                pnls.append(share_pnl + futures_pnl - 4 * fee)
                ts.append(timestamps[i+1])

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

def generate_walk_forward_windows(df, train_months=6, test_months=3):
    windows = []
    start_date = df['timestamp'].min()
    end_date = df['timestamp'].max()

    current_start = start_date

    while True:
        train_start = current_start
        train_end = train_start + relativedelta(months=train_months)
        test_start = train_end
        test_end = test_start + relativedelta(months=test_months)

        if test_end > end_date:
            break

        windows.append((train_start, train_end, test_start, test_end))
        current_start = train_start + relativedelta(months=test_months)

    return windows

def optimize(df, fee, trials=200):
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda trial: objective(trial, df, fee), n_trials=trials, n_jobs=-1)

    return study.best_params

def walk_forward_optimization(df, fee, train_month, test_month, trials=200):
    df = df.copy()

    windows = generate_walk_forward_windows(df, train_month, test_month)

    pnls = [] #not cumulative, assuming fixed trade sizes
    timestamps = []
    for train_start, train_end, test_start, test_end in windows:
        train_df = df.loc[(df['timestamp'] > train_start) & (df['timestamp'] < train_end)].copy()
        test_df = df.loc[(df['timestamp'] > test_start) & (df['timestamp'] < test_end)].copy()

        params = optimize(train_df, fee, trials)

        ols_window = params['ols_window']
        z_entry = params['z_entry']
        z_exit = params['z_exit']
        z_window = params['z_window']

        test_df = prepare_df(test_df, z_window, ols_window)
        test_results = run_backtest(test_df,z_entry, z_exit, fee)

        pnls += test_results[0]
        timestamps += test_results[1]

    plot_equity_curve(pnls, timestamps)


def main():
    name = "SBERF-SBER"

    data = pd.read_csv(DATA_DIR / name)

    data = prepare_df(data, 10, 100)
    walk_forward_optimization(data, fee=0, train_month=1, test_month=1, trials=10)


if __name__ == "__main__":
    main()