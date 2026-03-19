import feedparser
import json
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

CONFIG_FILE = 'config.json'
TEMPLATE_FILE = 'template.html'
OUTPUT_FILE = 'index.html'

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_news(rss_url):
    print(f"Fetching news from {rss_url}...")
    feed = feedparser.parse(rss_url)
    
    if feed.bozo:
        print("Warning: RSS feed parsing had issues.")
    
    # If no entries, it might be an error or empty feed
    if not feed.entries:
        raise Exception("No entries found in the RSS feed.")
        
    items = []
    for entry in feed.entries:
        # Extract image from enclosure if available
        image_url = ''
        if 'enclosures' in entry and len(entry.enclosures) > 0:
            image_url = entry.enclosures[0].get('url', '')
        elif 'links' in entry:
            for link in entry.links:
                if link.get('rel') == 'enclosure' or 'image' in link.get('type', ''):
                    image_url = link.get('href', '')
                    break

        items.append({
            'title': entry.get('title', 'Sin título'),
            'link': entry.get('link', '#'),
            'summary': entry.get('description', entry.get('summary', '')),
            'published': entry.get('published', ''),
            'image': image_url
        })
    return items

def generate_site():
    try:
        config = load_config()
        items = fetch_news(config['rss_url'])
        
        # Setup Jinja2
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template(TEMPLATE_FILE)
        
        # Render
        update_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        html_output = template.render(
            site_name=config.get('site_name', 'InfoAgraria'),
            items=items[:20],  # Limit to 20 news items
            banners=config.get('banners', {}),
            update_time=update_time
        )
        
        # Atomic-ish write: write to temp first, then rename or just write if simple
        # Since we are on GitHub Actions, a simple write is fine because we'll check status
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(html_output)
            
        print(f"Successfully generated {OUTPUT_FILE} with {len(items)} items at {update_time}")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        # On error, we exit with status 1 to fail the GitHub Action but NOT overwrite index.html
        # if the script failed before the write step.
        exit(1)

if __name__ == "__main__":
    generate_site()
