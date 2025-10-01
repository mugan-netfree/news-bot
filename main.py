import feedparser
import time
import requests # A standard library for making HTTP requests
import os # To read environment variables

# --- Configuration ---
NEWS_FEEDS = {
    'Ynet': 'http://www.ynet.co.il/Integration/StoryRss2.xml',
    'N12': 'https://rcs.mako.co.il/rss/32b338439535c310VgnVCM2000002a0c10acRCRD.xml',
    'Walla': 'https://rss.walla.co.il/feed/22',
}

# Use Nitter for Twitter RSS feeds. Find a reliable instance.
TWITTER_FEEDS = {
    'YnetTwitter': 'https://nitter.privacydev.net/ynetalerts/rss'
}

# --- Slack Configuration ---
# The Webhook URL will be read from GitHub Secrets
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

# A file to keep track of links we've already sent
SEEN_LINKS_FILE = "seen_links.txt"

def get_latest_items(feeds):
    all_items = []
    for name, url in feeds.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                all_items.append({
                    'source': name,
                    'title': entry.title.strip(), # Clean up whitespace
                    'link': entry.link
                })
        except Exception:
            pass # Ignore feeds that fail
    return all_items
    
def send_slack_message(message_text):
    if not SLACK_WEBHOOK_URL:
        print("Slack Webhook URL is not set. Cannot send message.")
        return
    
    # Slack uses a JSON payload. The format for links is <URL|Link Text>
    payload = {'text': message_text}
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status() # Will raise an exception for bad status codes
        print("Message sent to Slack successfully.")
    except Exception as e:
        print(f"Failed to send message to Slack: {e}")

def load_seen_links():
    try:
        with open(SEEN_LINKS_FILE, 'r') as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def save_seen_links(links):
    with open(SEEN_LINKS_FILE, 'w') as f:
        for link in links:
            f.write(f"{link}\n")

# --- Main ---
if __name__ == "__main__":
    seen_links = load_seen_links()
    
    all_feeds = {**NEWS_FEEDS, **TWITTER_FEEDS}
    all_items = get_latest_items(all_feeds)
    
    new_items_found = False
    
    for item in reversed(all_items): # Process oldest to newest
        if item['link'] not in seen_links:
            new_items_found = True
            print(f"New item found: [{item['source']}] {item['title']}")
            
            # Format the message for Slack: *Bold Source*, Title, and a clickable link
            message = f"*{item['source']}*\n{item['title']}\n\n<{item['link']}|קרא עוד>"
            
            send_slack_message(message)
            seen_links.add(item['link'])
            time.sleep(1) # Sleep 1 second between messages to avoid being rate-limited
    
    if not new_items_found:
        print("No new items found on this run.")
        
    save_seen_links(seen_links)
