import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(r"..\Automation\.env"))
page_id = os.getenv("MH_PAGE_ID")
token = os.getenv("MH_PAGE_ACCESS_TOKEN")

# Page info
page_res = requests.get(
    f"https://graph.facebook.com/v21.0/{page_id}",
    params={
        "fields": "id,name,fan_count,followers_count,talking_about_count,verification_status",
        "access_token": token,
    }
).json()

print("=== PAGE OVERVIEW ===")
print("Page Name:", page_res.get("name"))
print("Followers:", page_res.get("followers_count"))
print("Page Likes (Fans):", page_res.get("fan_count"))
print("Talking About Count:", page_res.get("talking_about_count"))
print()

# Published posts in the last week
posts_res = requests.get(
    f"https://graph.facebook.com/v21.0/{page_id}/published_posts",
    params={
        "fields": "id,message,created_time,shares,reactions.summary(true),comments.summary(true)",
        "limit": 10,
        "access_token": token,
    }
).json()

print("=== RECENT POSTS PERFORMANCE (LAST 7 DAYS) ===")
for p in posts_res.get("data", []):
    pid = p["id"]
    msg_lines = p.get("message", "").split("\n")
    headline = msg_lines[0] if msg_lines else "No text"
    created = p.get("created_time")
    reactions = p.get("reactions", {}).get("summary", {}).get("total_count", 0)
    comments = p.get("comments", {}).get("summary", {}).get("total_count", 0)
    shares = p.get("shares", {}).get("count", 0)
    
    # Try fetching post impressions
    ins = requests.get(
        f"https://graph.facebook.com/v21.0/{pid}/insights",
        params={
            "metric": "post_impressions,post_impressions_unique,post_clicks",
            "access_token": token,
        }
    ).json()
    
    metrics = {item["name"]: item["values"][0]["value"] for item in ins.get("data", [])}
    reach = metrics.get("post_impressions_unique", 0)
    impressions = metrics.get("post_impressions", 0)
    clicks = metrics.get("post_clicks", 0)
    
    print(f"Date: {created[:10]} | Reach: {reach} | Impr: {impressions} | React: {reactions} | Comm: {comments} | Shares: {shares} | Clicks: {clicks}")
    print(f"  Headline: {headline}")
    print(f"  URL: https://facebook.com/{pid}")
    print("-" * 60)
