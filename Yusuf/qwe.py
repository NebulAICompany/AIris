import feedparser

# Yahoo Finance RSS feed URL
rss_url = "https://finance.yahoo.com/news/rssindex"

# Parse the RSS feed
feed = feedparser.parse(rss_url)

# Display the latest news titles and links
for entry in feed.entries[:10]:  # Limit to 10 articles
    print(f"Title: {entry.title}")
    print(f"Link: {entry.link}")
    print(f"Published: {entry.published}")
    print("-" * 80)

