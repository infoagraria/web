import feedparser
import json
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

CONFIG_FILE = 'config.json'
TEMPLATE_FILE = 'template.html'
OUTPUT_FILE = 'index.html'
SITEMAP_FILE = 'sitemap.xml'

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def ensure_https(url):
    """Ensures that the URL uses HTTPS instead of HTTP."""
    if url and url.startswith('http://'):
        return url.replace('http://', 'https://', 1)
    return url

def fetch_news_from_feed(rss_url):
    """Fetches news from a single RSS feed. Returns a list of items."""
    print(f"Fetching news from {rss_url}...")
    feed = feedparser.parse(rss_url)

    if feed.bozo:
        print(f"  Warning: RSS feed parsing had issues for {rss_url}.")

    if not feed.entries:
        print(f"  Warning: No entries found in {rss_url}. Skipping.")
        return []

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
            'link': ensure_https(entry.get('link', '#')),
            'summary': entry.get('description', entry.get('summary', '')),
            'published': entry.get('published', ''),
            'published_parsed': entry.get('published_parsed'),  # usado para ordenar
            'image': ensure_https(image_url)
        })
    return items

def fetch_all_news(config):
    """Reads all RSS feeds from config, combines and sorts articles by date."""
    # Soporte para lista de feeds o feed único (compatibilidad hacia atrás)
    rss_urls = config.get('rss_urls', [config.get('rss_url')])

    all_items = []
    for url in rss_urls:
        try:
            all_items.extend(fetch_news_from_feed(url))
        except Exception as e:
            print(f"  ERROR fetching {url}: {e}. Skipping.")

    if not all_items:
        raise Exception("No se encontraron artículos en ningún feed RSS configurado.")

    # Ordenar por fecha de publicación, más reciente primero
    all_items.sort(
        key=lambda x: x.get('published_parsed') or (0,) * 9,
        reverse=True
    )

    print(f"Total articles fetched across all feeds: {len(all_items)}")
    return all_items

def generate_sitemap():
    """Generates a basic sitemap.xml for the project."""
    site_url = "https://infoagraria.com.ar"
    now = datetime.now().strftime('%Y-%m-%d')
    sitemap_content = f'<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap_content += '  <url>\n'
    sitemap_content += f'    <loc>{site_url}/</loc>\n'
    sitemap_content += f'    <lastmod>{now}</lastmod>\n'
    sitemap_content += '    <changefreq>hourly</changefreq>\n'
    sitemap_content += '    <priority>1.0</priority>\n'
    sitemap_content += '  </url>\n'
    sitemap_content += '</urlset>'
    
    with open(SITEMAP_FILE, 'w', encoding='utf-8') as f:
        f.write(sitemap_content)
    print(f"Successfully generated {SITEMAP_FILE}")

def generate_site():
    try:
        config = load_config()
        items = fetch_all_news(config)
        
        # Setup Jinja2
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template(TEMPLATE_FILE)
        
        # Render
        update_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        html_output = template.render(
            site_name=config.get('site_name', 'InfoAgraria'),
            items=items[:40],  # Limit to 40 news items across all feeds
            banners=config.get('banners', {}),
            update_time=update_time
        )
        
        # Atomic-ish write: write to temp first, then rename or just write if simple
        # Since we are on GitHub Actions, a simple write is fine because we'll check status
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(html_output)
            
        generate_sitemap()
            
        print(f"Successfully generated {OUTPUT_FILE} with {len(items)} items at {update_time}")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        # On error, we exit with status 1 to fail the GitHub Action but NOT overwrite index.html
        # if the script failed before the write step.
        exit(1)

if __name__ == "__main__":
    generate_site()
