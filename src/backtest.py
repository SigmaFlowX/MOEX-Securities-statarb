import pandas as pd
from pathlib import Path
from matplotlib import pyplot as plt
from statsmodels.regression.rolling import RollingOLS
import statsmodels.api as sm
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def prepare_df(df, z_window, ols_window):
    df.dropna(inplace=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    y = df['close_share']
    x = sm.add_constant(df['close_futures'])

    rols = RollingOLS(y, x, window=ols_window)
    rres = rols.fit()

    params = rres.params
    df['a'] = params['close_futures']
    df['b'] = params['const']
    df['spread'] = y - (df['a'] * df['close_futures'] + df['b'])

    df['spread_mean'] = df['spread'].rolling(z_window).mean()
    df['spread_std'] = df['spread'].rolling(z_window).std()
    df['z_score'] = (df['spread'] - df['spread_mean']) / df['spread_std']

    df = df.dropna()

    return df


def main():
    name = "SBERF-SBER"

    data = pd.read_csv(DATA_DIR / name)

    data = prepare_df(data, 10, 10)

    plt.plot(data['timestamp'], data['spread'])
    plt.show()

if __name__ == "__main__":
    main()