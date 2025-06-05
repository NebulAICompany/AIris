import yfinance as yf

def get_finance_data(ticker_symbol: str):
    ticker = yf.Ticker(ticker_symbol)
    data = {
        "current_price": ticker.info.get("regularMarketPrice"),
        "info": ticker.info,
        "history": ticker.history(period="1y").to_dict(),
        "dividends": ticker.dividends.to_dict(),
        "splits": ticker.splits.to_dict(),
    }
    return data

if __name__ == "__main__":

    # get list of news
    news = yf.Search("Google", news_count=10).news
    print(news)
    for item in news:
        print(f"Title: {item.get('title')}")
        print(f"Link: {item.get('link')}")
        print(f"Published: {item.get('providerPublishTime')}")
        print(f"Content: {item.get('contentSnippet', '')}\n")
    # symbol = "AAPL"
    # finance_data = get_finance_data(symbol)
    # print("Current Price:", finance_data["current_price"])

    # print("Company Info:", {k: finance_data["info"][k] for k in ('shortName', 'sector', 'industry') if k in finance_data["info"]})
    # print("Dividends (last 1):", list(finance_data["dividends"].items())[-1:])
    # print("Splits:", finance_data["splits"])
    # print("History (last 1 days):", {k: v for k, v in list(finance_data["history"].items())[-1:]})
