import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import hashlib

BASE_URL = "https://help.zipboard.co"

def get_soup(url):
    """Fetches URL and returns BeautifulSoup object with error handling."""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def scrape_articles():
    print("🚀 Starting Scrape of help.zipboard.co (Help Scout Pattern)...")
    soup = get_soup(BASE_URL)
    
    if not soup:
        print("❌ Failed to load homepage.")
        return

    # 1. Identify all Category Links
    # Help Scout architecture uses /category/ or /collection/ routing
    all_links = soup.find_all('a', href=True)
    category_links = []
    
    seen_urls = set()
    for link in all_links:
        href = link['href']
        # Normalize relative URLs
        full_url = href if href.startswith('http') else BASE_URL + href
        
        if '/category/' in full_url or '/collection/' in full_url:
            if full_url not in seen_urls and full_url != BASE_URL:
                category_links.append((link.get_text(strip=True), full_url))
                seen_urls.add(full_url)

    print(f"✅ Found {len(category_links)} categories. Starting deep scan...")

    articles_data = []

    for cat_name, cat_url in category_links:
        print(f"📂 Scanning Category: {cat_name}...")
        cat_soup = get_soup(cat_url)
        if not cat_soup: continue

        # 2. Extract Article Links
        cat_links = cat_soup.find_all('a', href=True)
        article_links = []
        
        for link in cat_links:
            href = link['href']
            # Help Scout articles follow /article/ pattern
            if '/article/' in href:
                full_url = href if href.startswith('http') else BASE_URL + href
                article_links.append(full_url)

        # Deduplicate
        article_links = list(set(article_links))

        for art_url in article_links:
            art_soup = get_soup(art_url)
            if not art_soup: continue

            # Extract Metadata
            title_tag = art_soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"
            
            # Content extraction from standard Help Scout containers
            content_div = art_soup.find('section', class_='article-body') or art_soup.find('article')
            content_text = content_div.get_text(" ", strip=True) if content_div else ""
            
            # Media check
            images = content_div.find_all('img') if content_div else []
            has_screenshots = "Yes" if len(images) > 0 else "No"
            
            # Generate content hash for change detection in CI/CD pipeline
            content_hash = hashlib.md5(content_text.encode('utf-8')).hexdigest()
            
            # Extract Headers for topic modeling
            headers = [h.get_text(strip=True) for h in art_soup.find_all(['h2', 'h3'])]
            topics = ", ".join(headers[:3]) if headers else "General"

            # Parse Article ID from URL
            try:
                art_id = art_url.split('/article/')[1].split('-')[0]
            except:
                art_id = "N/A"

            # Fetch Real Timestamp from Meta Tags
            meta_date = art_soup.find('meta', property='article:modified_time') or \
                        art_soup.find('meta', property='og:updated_time')
            
            real_date = meta_date.get('content') if meta_date else "N/A"

            if real_date == "N/A":
                time_tag = art_soup.find('time')
                if time_tag:
                    real_date = time_tag.get('datetime') or time_tag.get_text(strip=True)

            articles_data.append({
                "Article ID": art_id,
                "Article Title": title,
                "Category": cat_name,
                "URL": art_url,
                "Last Updated": real_date,
                "Topics Covered": topics,
                "Content Type": "Guide",
                "Word Count": len(content_text.split()),
                "Has Screenshots": has_screenshots,
                "Content Hash": content_hash
            })
            
            time.sleep(0.1) # Rate limiting respect

    # Export to CSV
    df = pd.DataFrame(articles_data)
    df.to_csv("zipboard_help_data.csv", index=False)
    print(f"🎉 DONE! Scraped {len(df)} articles. Saved to zipboard_help_data.csv")

if __name__ == "__main__":
    scrape_articles()