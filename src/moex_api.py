import requests
import json



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