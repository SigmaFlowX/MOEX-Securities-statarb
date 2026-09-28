import pandas as pd
from pathlib import Path
from matplotlib import pyplot as plt
DATA_DIR = Path(__file__).resolve().parent.parent / "data"



def main():
    name = "SBERF-SBER"

    data = pd.read_csv(DATA_DIR / name)
    data.dropna(inplace=True)
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    print(data.columns)
    plt.plot(data['timestamp'], data['close_futures'])
    plt.show()


if __name__ == "__main__":
    main()