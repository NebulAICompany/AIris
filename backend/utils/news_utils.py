import re
import html
from pydantic import BaseModel
from typing import List
from backend.shared.logger import get_logger
import feedparser
import datetime
from dateutil import parser as date_parser

logger = get_logger("NEWS_UTILS")

def clean_turkish_text(text):
    """
    Clean Turkish text from HTML entities, CDATA, and encoding issues.
    """
    if not text:
        return ""

    # Debug: log original text if it contains HTML entities
    if "&#" in text:
        logger.debug(f"Processing text with HTML entities: {text[:100]}...")

    # Remove CDATA wrapper if present
    cdata_pattern = r"<!\[CDATA\[(.*?)\]\]>"
    cdata_match = re.search(cdata_pattern, text, re.DOTALL)
    if cdata_match:
        text = cdata_match.group(1).strip()

    # First pass: decode HTML entities (handles &#39;, &amp;, &quot;, etc.)
    text = html.unescape(text)

    # Second pass: handle any remaining numeric HTML entities manually
    # This catches cases where html.unescape might miss some
    numeric_entities = {
        "&#39;": "'",  # Apostrophe
        "&#x27;": "'",  # Apostrophe (hex)
        "&#34;": '"',  # Double quote
        "&#x22;": '"',  # Double quote (hex)
        "&#38;": "&",  # Ampersand
        "&#x26;": "&",  # Ampersand (hex)
        "&#60;": "<",  # Less than
        "&#x3C;": "<",  # Less than (hex)
        "&#62;": ">",  # Greater than
        "&#x3E;": ">",  # Greater than (hex)
        "&#160;": " ",  # Non-breaking space
        "&#xA0;": " ",  # Non-breaking space (hex)
        "&#8217;": "'",  # Right single quotation mark
        "&#8220;": '"',  # Left double quotation mark
        "&#8221;": '"',  # Right double quotation mark
        "&#8211;": "–",  # En dash
        "&#8212;": "—",  # Em dash
    }

    for entity, replacement in numeric_entities.items():
        text = text.replace(entity, replacement)

    # Third pass: use regex to catch any remaining numeric entities
    def replace_numeric_entity(match):
        try:
            num = int(match.group(1))
            return chr(num)
        except (ValueError, OverflowError):
            return match.group(0)  # Return original if conversion fails

    # Handle decimal numeric entities like &#123;
    text = re.sub(r"&#(\d+);", replace_numeric_entity, text)

    # Handle hexadecimal numeric entities like &#x7B;
    def replace_hex_entity(match):
        try:
            num = int(match.group(1), 16)
            return chr(num)
        except (ValueError, OverflowError):
            return match.group(0)  # Return original if conversion fails

    text = re.sub(r"&#x([0-9a-fA-F]+);", replace_hex_entity, text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Normalize whitespace
    text = " ".join(text.split())

    # Handle common encoding issues specific to Turkish
    replacements = {
        "â€™": "'",  # Common encoding issue
        "â€œ": '"',  # Opening quote
        "â€": '"',  # Closing quote
        'â€"': "—",  # Em dash
        'â€"': "–",  # En dash
        "Ä±": "ı",  # Turkish lowercase i
        "Ä°": "İ",  # Turkish uppercase I
        "Åž": "Ş",  # Turkish S
        "ÅŸ": "ş",  # Turkish s
        "Ä°": "İ",  # Turkish I
        "Ã§": "ç",  # Turkish c
        "Ã¼": "ü",  # Turkish u
        "Ã¶": "ö",  # Turkish o
        "Ä±": "ı",  # Turkish i
        "ÄŸ": "ğ",  # Turkish g
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Debug: log final text if we started with HTML entities
    if "&#" in text:
        logger.debug(f"Still contains HTML entities after cleaning: {text[:100]}...")

    return text.strip()


def extract_image_info(entry):
    """
    Extract image information from RSS entry.
    Looks for enclosure tags and img tags in description.
    """
    image_url = ""
    image_width = 0
    image_height = 0

    # Method 1: Check for enclosure tag (main image)
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enclosure in entry.enclosures:
            if enclosure.get("type", "").startswith("image/"):
                image_url = enclosure.get("href", "") or enclosure.get("url", "")
                break

    # Method 2: Extract from img tag in description if no enclosure found
    if not image_url:
        description = entry.get("description", "") or entry.get("summary", "")
        if description:
            # Look for img tag with src attribute
            img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
            img_match = re.search(img_pattern, description, re.IGNORECASE)
            if img_match:
                image_url = img_match.group(1)

                # Try to extract width and height from img tag
                width_pattern = r'width=["\']?(\d+)["\']?'
                height_pattern = r'height=["\']?(\d+)["\']?'

                width_match = re.search(
                    width_pattern, img_match.group(0), re.IGNORECASE
                )
                height_match = re.search(
                    height_pattern, img_match.group(0), re.IGNORECASE
                )

                if width_match:
                    try:
                        image_width = int(width_match.group(1))
                    except ValueError:
                        pass

                if height_match:
                    try:
                        image_height = int(height_match.group(1))
                    except ValueError:
                        pass

    return image_url, image_width, image_height


class NewsArticle(BaseModel):
    title: str
    link: str
    published: str
    summary: str = ""
    source: str = "Dunya Ekonomi"
    image_url: str = ""
    image_width: int = 0
    image_height: int = 0


class NewsResponse(BaseModel):
    articles: List[NewsArticle]
    total_count: int
    last_updated: str

def fetch_and_parse_news(rss_url: str = None) -> List[NewsArticle]:
    logger.info("Fetching finance news from Dünya Gazetesi RSS")

    # Dünya Gazetesi RSS feed URL
    if rss_url is None:
        rss_url = "https://www.dunya.com/rss/ekonomi.xml"

    # Parse the RSS feed with proper encoding handling
    feed = feedparser.parse(rss_url)

    # Ensure proper UTF-8 encoding for Turkish content
    if hasattr(feed, "encoding") and feed.encoding:
        logger.info(f"RSS feed encoding: {feed.encoding}")
    else:
        logger.info("RSS feed encoding not specified, assuming UTF-8")

    # Check if feed was parsed successfully
    if feed.bozo:
        logger.warning(f"RSS feed parse error: {feed.bozo_exception}")

    # Extract news articles and sort by publication date
    news_articles = []
    for entry in feed.entries:
        # Clean the title using comprehensive Turkish text cleaning
        title = clean_turkish_text(entry.get("title", "No title"))

        # Clean the summary/description using comprehensive Turkish text cleaning
        summary = clean_turkish_text(
            entry.get("summary", "") or entry.get("description", "")
        )

        # Extract image information
        image_url, image_width, image_height = extract_image_info(entry)

        article = {
            "title": title,
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": summary,
            "source": "Dünya Gazetesi",
            "image_url": image_url,
            "image_width": image_width,
            "image_height": image_height,
        }
        news_articles.append(article)

    # Sort articles by publication date (newest first)
    

    try:
        news_articles.sort(
            key=lambda x: (
                date_parser.parse(x["published"])
                if x["published"]
                else datetime.min
            ),
            reverse=True,
        )
    except Exception as sort_error:
        logger.warning(f"Could not sort articles by date: {sort_error}")
    return news_articles
