import feedparser
import time
import requests
import os

# ==============================================================================
# --- התאמה אישית: כאן מגדירים את מקורות המידע ---
# ==============================================================================
NEWS_FEEDS = {
    'Ynet': 'http://www.ynet.co.il/Integration/StoryRss2.xml',
    'N12': 'https://rcs.mako.co.il/rss/32b338439535c310VgnVCM2000002a0c10acRCRD.xml',
    'Walla': 'https://rss.walla.co.il/feed/22',
    'ישראל היום': 'https://www.israelhayom.co.il/rss.xml',
}

# חשבונות טוויטר, ערוצי טלגרם ומקורות נוספים
# הערה: השתמשתי כאן ב-Nitter (לטוויטר) ו-RSS-Bridge (לטלגרם). כלים אלו לפעמים לא יציבים.
# אם מקור מסוים מפסיק לעבוד, ייתכן שנצטרך להחליף את הכתובת בעתיד.
SOCIAL_FEEDS = {
    # --- הערוצים שביקשת ---
    'צ׳אט הכתבים N12 (טלגרם)': 'https://rss-bridge.org/bridge01/?action=display&bridge=Telegram&username=N12chat&format=Atom',
    'ערוץ 14 (טוויטר)': 'https://nitter.privacydev.net/now14israel/rss',
    
    # --- המלצות ביטחוניות (טוויטר) ---
    'דובר צה״ל (טוויטר)': 'https://nitter.privacydev.net/idfonline/rss',
    'יוסי יהושוע (פרשן צבאי)': 'https://nitter.privacydev.net/yossi_yehoshua/rss',
    'אמיר בוחבוט (פרשן צבאי)': 'https://nitter.privacydev.net/amirbohbot/rss',
    'טל לב רם (פרשן צבאי)': 'https://nitter.privacydev.net/tallevram/rss',

    # --- המלצות ביטחוניות (טלגרם) ---
    'אבו עלי אקספרס (טלגרם)': 'https://rss-bridge.org/bridge01/?action=display&bridge=Telegram&username=abualiexpress&format=Atom',
    'אינטלי טיימס (טלגרם)': 'https://rss-bridge.org/bridge01/?action=display&bridge=Telegram&username=intellitimes&format=Atom',
    
    # --- חשבונות טוויטר כלליים שהיו קודם ---
    'עמית סגל (טוויטר)': 'https://nitter.privacydev.net/amit_segal/rss'
}
# --- הגדרות מתקדמות ---
# כמה פריטים לשלוח בפעם הראשונה שהסקריפט רץ?
INITIAL_RUN_LIMIT = 20 
# תו מיוחד לשיפור תצוגת RTL (עברית)
RLM = '\u200f'

# ==============================================================================
# --- שאר הקוד (אין צורך לגעת) ---
# ==============================================================================
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
SEEN_LINKS_FILE = "seen_links.txt"

def get_latest_items(feeds):
    all_items = []
    for name, url in feeds.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # published_parsed is a structured time object for sorting
                sort_key = entry.get('published_parsed', time.gmtime())
                all_items.append({
                    'source': name,
                    'title': entry.title.strip(),
                    'link': entry.link,
                    'published_time': sort_key
                })
        except Exception as e:
            print(f"Warning: Could not fetch or parse feed from {name} ({url}). Error: {e}")
            pass
    return all_items
    
def send_slack_message(message_text):
    if not SLACK_WEBHOOK_URL:
        print("Error: Slack Webhook URL is not set.")
        return
    
    payload = {'text': message_text}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error: Failed to send message to Slack: {e}")

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

if __name__ == "__main__":
    is_first_run = not os.path.exists(SEEN_LINKS_FILE)
    seen_links = load_seen_links()
    
    all_feeds = {**NEWS_FEEDS, **TWITTER_FEEDS}
    all_items = get_latest_items(all_feeds)
    
    # Sort all items by publication time, newest first
    all_items.sort(key=lambda x: x['published_time'], reverse=True)
    
    new_items_to_send = []
    for item in all_items:
        if item['link'] not in seen_links:
            new_items_to_send.append(item)
    
    if is_first_run and len(new_items_to_send) > INITIAL_RUN_LIMIT:
        print(f"First run detected. Limiting initial send to {INITIAL_RUN_LIMIT} items.")
        new_items_to_send = new_items_to_send[:INITIAL_RUN_LIMIT]
    
    if not new_items_to_send:
        print("No new items found on this run.")
    else:
        # Send oldest items first to maintain chronological order in Slack
        for item in reversed(new_items_to_send):
            print(f"New item found: [{item['source']}] {item['title']}")
            
            message = (f"{RLM}*{item['source']}*\n"
                       f"{RLM}{item['title']}\n\n"
                       f"<{item['link']}|{RLM}קרא עוד>")
            
            send_slack_message(message)
            seen_links.add(item['link'])
            time.sleep(1.5) # Increased sleep to avoid Slack rate limits on burst
        
    save_seen_links(seen_links)
    print("Run completed.")
