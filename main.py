import os
import praw
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF

PDF_OUTPUT_FILE = "daily_crypto_summary.pdf"

REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET = os.environ["REDDIT_CLIENT_SECRET"]
REDDIT_USER_AGENT = os.environ["REDDIT_USER_AGENT"]

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

KEYWORDS = ["new signal", "long", "buy", "enc"]
TOKENS = ["BTC", "ETH", "DOGE", "SOL", "SHIB", "XRP", "ADA"]

def simulate_price_change():
    import random
    return round(random.uniform(-0.5, 1.5), 2)

def extract_token(text):
    for token in TOKENS:
        if token.lower() in text.lower():
            return token
    return None

def scrape_reddit():
    posts = []
    for submission in reddit.subreddit("CryptoCurrency+CryptoMoonShots+Altcoin").new(limit=100):
        text = f"{submission.title} {submission.selftext}"
        if any(k in text.lower() for k in KEYWORDS):
            token = extract_token(text)
            if token:
                posts.append({
                    "user": submission.author.name if submission.author else "unknown",
                    "text": submission.title,
                    "token": token,
                    "timestamp": datetime.utcfromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
                    "price_change_24h": simulate_price_change()
                })
    df = pd.DataFrame(posts)
    df["success"] = df["price_change_24h"] > 0.1
    return df

def compute_trust_scores(df):
    stats = df.groupby("user").agg(
        total_posts=("success", "count"),
        successful_posts=("success", "sum")
    )
    stats["trust_score"] = (stats["successful_posts"] / stats["total_posts"]).round(2)
    return stats.sort_values("trust_score", ascending=False).head(10)

def generate_summary(df, top_users):
    summaries = []
    for user in top_users.index:
        user_posts = df[df["user"] == user]
        if user_posts.empty:
            summaries.append(f"{user} did not post any tracked advice.")
            continue
        coins = user_posts["token"].unique()
        summary = f"{user} posted {len(user_posts)} times:\nCoins mentioned: {', '.join(coins)}\n"
        for _, row in user_posts.iterrows():
            summary += f"- {row['text']} (Token: {row['token']}, Change: {row['price_change_24h']:+.2f})\n"
        summaries.append(summary)
    return "\n\n".join(summaries)

def create_pdf_report(summary_text, filename):
    def safe(text):
        return text.encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for line in summary_text.split("\\n"):
        pdf.multi_cell(0, 10, safe(line))
    pdf.output(filename)
    print(f"[+] PDF report saved to: {filename}")

def main():
    print("[+] Scraping Reddit...")
    df = scrape_reddit()
    if df.empty:
        print("[!] No posts matched.")
        return
    top_users = compute_trust_scores(df)
    summary = generate_summary(df, top_users)
    create_pdf_report(summary, PDF_OUTPUT_FILE)

if __name__ == "__main__":
    main()
