import snscrape.modules.twitter as sntwitter
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF

PDF_OUTPUT_FILE = "daily_crypto_summary.pdf"

def scrape_tweets():
    since_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    query = f'"$500 a day" OR "double your crypto" OR "get rich quick" lang:en since:{since_date}'
    tweets = []
    for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
        if i >= 100:
            break
        tweets.append({
            "user": tweet.user.username,
            "text": tweet.content,
            "timestamp": tweet.date.strftime('%Y-%m-%d %H:%M:%S'),
            "token": extract_token(tweet.content),
            "price_change_24h": simulate_price_change()
        })
    df = pd.DataFrame(tweets)
    df["success"] = df["price_change_24h"] > 0.1
    df.dropna(subset=["token"], inplace=True)
    return df

def extract_token(text):
    for token in ["BTC", "ETH", "DOGE", "SOL", "SHIB", "XRP", "ADA"]:
        if token.lower() in text.lower():
            return token
    return None

def simulate_price_change():
    import random
    return round(random.uniform(-0.5, 1.5), 2)

def compute_trust_scores(df):
    stats = df.groupby("user").agg(total=("success", "count"), success=("success", "sum"))
    stats["trust_score"] = (stats["success"] / stats["total"]).round(2)
    return stats.sort_values("trust_score", ascending=False).head(10)

def generate_summary(df, top_users):
    cutoff = datetime.now() - timedelta(hours=24)
    summaries = []
    for user in top_users.index:
        posts = df[(df["user"] == user) & (pd.to_datetime(df["timestamp"]) >= cutoff)]
        if posts.empty:
            summaries.append(f"{user} did not post any tracked crypto advice in the last 24h.")
            continue
        summary = f"{user} posted {len(posts)} times in the last 24h:\n"
        for _, row in posts.iterrows():
            summary += f"- {row['text']}\n  Token: {row['token']}, Change: {row['price_change_24h']:+.2f}\n"
        summaries.append(summary)
    return "\n\n".join(summaries)

def create_pdf_report(summary_text, filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in summary_text.split("\n"):
        pdf.multi_cell(0, 10, line)
    pdf.output(filename)
    print(f"[+] PDF report saved to: {filename}")

def main():
    print("[+] Scraping tweets...")
    df = scrape_tweets()
    if df.empty:
        print("[!] No tweets matched the filter.")
        return
    top_users = compute_trust_scores(df)
    summary = generate_summary(df, top_users)
    create_pdf_report(summary, PDF_OUTPUT_FILE)

if __name__ == "__main__":
    main()
