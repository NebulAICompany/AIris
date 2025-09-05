import re
import html
from pydantic import BaseModel
from typing import List, Dict, Optional
from backend.shared.logger import get_logger
import feedparser
import datetime
from dateutil import parser as date_parser
import asyncio
import httpx
from dataclasses import dataclass
import numpy as np

logger = get_logger("NEWS_UTILS")

# Handle pytz import gracefully
try:
    import pytz

    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    logger.warning("pytz not available, using basic timezone handling")


# Financial news RSS sources configuration
@dataclass
class NewsSource:
    name: str
    rss_url: str
    language: str = "tr"  # Default to Turkish


# Clean list of reliable Turkish financial news sources
FINANCIAL_NEWS_SOURCES = [
    NewsSource("NTV Ekonomi", "https://www.ntv.com.tr/ekonomi.rss", "tr"),
    NewsSource(
        "Anadolu Ajansı Ekonomi",
        "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
        "tr",
    ),
    NewsSource("Cumhuriyet Ekonomi", "https://www.cumhuriyet.com.tr/rss/ekonomi", "tr"),
    NewsSource(
        "Milliyet Ekonomi", "https://www.milliyet.com.tr/rss/rssnew/ekonomi.xml", "tr"
    ),
    NewsSource("Sabah Ekonomi", "https://www.sabah.com.tr/rss/ekonomi.xml", "tr"),
    NewsSource("Star Ekonomi", "https://www.star.com.tr/rss/rss.asp?cid=15", "tr"),
    NewsSource("Takvim Ekonomi", "https://www.takvim.com.tr/rss/ekonomi.xml", "tr"),
    NewsSource("Yeni Şafak Ekonomi", "https://www.yenisafak.com/rss?xml=ekonomi", "tr"),
    NewsSource("A Haber Ekonomi", "https://www.ahaber.com.tr/rss/ekonomi.xml", "tr"),
    NewsSource(
        "CNN Türk Ekonomi", "https://www.cnnturk.com/feed/rss/ekonomi/news", "tr"
    ),
    NewsSource("CNBC-e", "https://www.cnbce.com/rss", "tr"),
    NewsSource("Investing.com TR", "https://tr.investing.com/rss/news.rss", "tr"),
    NewsSource("Dünya Gazetesi", "https://www.dunya.com/rss/ekonomi.xml", "tr"),
]


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
    source: str = "Unknown"
    image_url: str = ""
    image_width: int = 0
    image_height: int = 0
    source_language: str = "en"
    available_images: List[dict] = []


class ClusteredNews(BaseModel):
    """Represents a news story that appears across multiple sources"""

    unified_title: str
    unified_description: str
    sources: List[str]
    articles: List[NewsArticle]
    available_images: List[dict] = []
    relevance_score: float = 0.0
    published_earliest: str = ""
    published_latest: str = ""


class NewsResponse(BaseModel):
    clustered_articles: List[ClusteredNews]
    total_clusters: int
    total_articles: int
    last_updated: str


def normalize_datetime(date_str: str) -> datetime.datetime:
    """
    Normalize datetime strings to Turkish timezone (GMT+3) aware datetime objects.
    This ensures proper time display for Turkish users.
    """
    if not date_str:
        if PYTZ_AVAILABLE:
            turkey_tz = pytz.timezone("Europe/Istanbul")
            return datetime.datetime.min.replace(tzinfo=turkey_tz)
        else:
            # GMT+3 offset
            turkey_offset = datetime.timezone(datetime.timedelta(hours=3))
            return datetime.datetime.min.replace(tzinfo=turkey_offset)

    try:
        parsed_date = date_parser.parse(date_str)

        if PYTZ_AVAILABLE:
            turkey_tz = pytz.timezone("Europe/Istanbul")

            # If the date is offset-naive (no timezone info), assume it's Turkish local time
            if parsed_date.tzinfo is None:
                parsed_date = turkey_tz.localize(parsed_date)
            else:
                # Convert any timezone to Turkish time
                parsed_date = parsed_date.astimezone(turkey_tz)
        else:
            # Fallback without pytz - use GMT+3
            turkey_offset = datetime.timezone(datetime.timedelta(hours=3))
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=turkey_offset)
            else:
                parsed_date = parsed_date.astimezone(turkey_offset)

        return parsed_date

    except Exception as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        if PYTZ_AVAILABLE:
            turkey_tz = pytz.timezone("Europe/Istanbul")
            return datetime.datetime.min.replace(tzinfo=turkey_tz)
        else:
            turkey_offset = datetime.timezone(datetime.timedelta(hours=3))
            return datetime.datetime.min.replace(tzinfo=turkey_offset)


async def generate_unified_summary(articles: List[NewsArticle]) -> Dict[str, str]:
    """
    Generate comprehensive unified title and description from multiple articles using AI agent.
    """
    if not articles:
        return {"title": "No title", "description": "No description"}

    if len(articles) == 1:
        return {
            "title": articles[0].title,
            "description": articles[0].summary or "No summary available",
        }

    logger.info(
        f"🤖 Generating comprehensive unified summary for {len(articles)} articles"
    )

    try:
        # Import agent infrastructure
        from backend.core.agents import create_news_summarization_agent
        from backend.core.runner import generate_answer
        from backend.core.prompts import news_summarization_prompt

        # Create specialized summarization agent
        agent = create_news_summarization_agent(
            instructions=news_summarization_prompt,
            web_search_enabled=False,
        )

        # Prepare comprehensive article data for the agent
        sources = list(set([article.source for article in articles]))

        # Collect available images from all articles
        available_images = []
        for i, article in enumerate(articles):
            if article.image_url and article.image_url.strip():
                available_images.append(
                    {
                        "source": article.source,
                        "url": article.image_url,
                        "width": article.image_width,
                        "height": article.image_height,
                        "article_index": i,
                    }
                )

        # Prepare article text with image information
        articles_text = f"""
**Story from {len(articles)} articles across {len(sources)} sources:**

**Available Images ({len(available_images)} total):**
"""

        for img in available_images:
            articles_text += f"- Image from {img['source']}: {img['url']} ({img['width']}x{img['height']})\n"

        articles_text += "\n**Articles:**\n"

        for i, article in enumerate(articles):
            published_info = ""
            if article.published:
                try:
                    from datetime import datetime

                    pub_date = datetime.fromisoformat(
                        article.published.replace("Z", "+00:00")
                    )
                    published_info = (
                        f" (Published: {pub_date.strftime('%Y-%m-%d %H:%M')})"
                    )
                except:
                    published_info = f" (Published: {article.published})"

            image_info = ""
            if article.image_url and article.image_url.strip():
                image_info = f"\n**Image:** {article.image_url} ({article.image_width}x{article.image_height})"

            articles_text += f"""
**Article {i+1} - Source: {article.source}**{published_info}
**Title:** {article.title}
**Content:** {article.summary or "No summary available"}{image_info}
**Link:** {article.link}

"""

        # Create comprehensive analysis prompt
        analysis_prompt = f"""{articles_text}

**Task:** Create a comprehensive unified summary combining ALL information from these {len(articles)} articles.

**Requirements:**
1. Create a unified title that captures the complete story
2. Write a LONG, DETAILED description (500+ words) that includes:
   - Every important detail from all sources
   - All numbers, percentages, dates, and specific data
   - All quotes and statements from officials/analysts
   - Complete context and background information
   - All unique perspectives and angles from different sources
   - Chronological flow of events if applicable

**Turkish Financial Context:** Include relevant context about Turkish financial institutions, economic indicators, and market dynamics where applicable.

Provide your response in JSON format as specified in your instructions."""

        # Get comprehensive summary from agent
        logger.info("📝 Requesting comprehensive summary from AI agent...")
        response = await generate_answer(analysis_prompt, agent)
        logger.info(f"✅ AI summary response received ({len(response)} chars)")

        # Parse JSON response with improved extraction
        import json
        import re

        try:
            # Clean up the response and extract JSON more robustly
            response_clean = response.strip()

            # Method 1: Try to find complete JSON object
            json_pattern = r'\{[^{}]*"unified_title"[^{}]*"unified_description"[^{}]*\}'
            json_match = re.search(json_pattern, response_clean, re.DOTALL)

            json_str = None
            if json_match:
                json_str = json_match.group(0)
            else:
                # Method 2: Extract between first { and last }
                json_start = response_clean.find("{")
                json_end = response_clean.rfind("}") + 1

                if json_start != -1 and json_end > json_start:
                    potential_json = response_clean[json_start:json_end]

                    # Try to fix common JSON formatting issues
                    potential_json = potential_json.replace("\n", " ")
                    potential_json = re.sub(
                        r"\s+", " ", potential_json
                    )  # Multiple spaces to single
                    potential_json = potential_json.replace('": "', '": "').replace(
                        '" : "', '": "'
                    )

                    # Check if it contains our required keys
                    if (
                        "unified_title" in potential_json
                        and "unified_description" in potential_json
                    ):
                        json_str = potential_json

            if json_str:
                # Additional cleanup for common issues
                json_str = json_str.replace('""', '"')  # Fix doubled quotes
                json_str = re.sub(r'",\s*}', '"}', json_str)  # Fix trailing commas

                parsed_response = json.loads(json_str)

                unified_title = parsed_response.get("unified_title", "").strip()
                unified_description = parsed_response.get(
                    "unified_description", ""
                ).strip()

                # Validate the extracted content
                if (
                    unified_title
                    and unified_description
                    and len(unified_description) > 50
                ):
                    logger.info(
                        f"📰 Successfully parsed AI summary: {len(unified_description)} chars"
                    )

                    # Return summary with available images for frontend processing
                    return {
                        "title": unified_title,
                        "description": unified_description,
                        "available_images": available_images,
                    }
                else:
                    logger.warning(
                        f"AI response has insufficient content: title={len(unified_title)}, desc={len(unified_description)}"
                    )

            else:
                logger.warning(
                    "Could not extract valid JSON structure from AI response"
                )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            logger.debug(
                f"Attempted to parse: {json_str[:300] if json_str else 'No JSON extracted'}..."
            )
            logger.debug(f"Full AI response preview: {response_clean[:500]}...")
        except Exception as e:
            logger.warning(f"Unexpected error in JSON parsing: {e}")
            logger.debug(
                f"Full AI response preview: {response_clean[:500] if 'response_clean' in locals() else response[:500]}..."
            )

        # Fallback to intelligent combination if AI fails
        logger.info("🔄 Using intelligent fallback summarization")
        return _create_fallback_summary(articles)

    except Exception as e:
        logger.error(f"❌ AI summarization failed: {e}")
        logger.info("🔄 Using intelligent fallback summarization")
        return _create_fallback_summary(articles)


def _create_fallback_summary(articles: List[NewsArticle]) -> Dict[str, str]:
    """Create intelligent fallback summary when AI agent fails"""
    try:
        sources = list(set([article.source for article in articles]))

        # Create comprehensive title
        longest_title_article = max(articles, key=lambda x: len(x.title))
        unified_title = f"{longest_title_article.title} ({len(sources)} kaynak)"

        # Collect available images
        available_images = []
        for i, article in enumerate(articles):
            if article.image_url and article.image_url.strip():
                available_images.append(
                    {
                        "source": article.source,
                        "url": article.image_url,
                        "width": article.image_width,
                        "height": article.image_height,
                        "article_index": i,
                    }
                )

        # Combine all available content comprehensively
        all_content = []
        for article in articles:
            content_parts = [f"**{article.source}:**", article.title]
            if article.summary and len(article.summary.strip()) > 10:
                content_parts.append(article.summary)
            all_content.append(" ".join(content_parts))

        # Create comprehensive fallback description with basic image placement
        description_parts = [
            f"Bu haber {len(sources)} farklı kaynaktan derlenmiştir: {', '.join(sources)}.",
            "",
        ]

        # Add lead image marker if available
        if available_images:
            description_parts.append("{{IMAGE_LEAD}}")
            description_parts.append("")

        # Add content sections
        mid_content_count = 0
        for i, content in enumerate(all_content):
            description_parts.append(content)

            # Add mid images strategically
            if available_images and mid_content_count < 2 and i < len(all_content) - 1:
                if (i + 1) % 2 == 0:  # Every second article
                    mid_content_count += 1
                    description_parts.append(f"{{{{IMAGE_MID_{mid_content_count}}}}}")
                    description_parts.append("")

        description_parts.append("")
        description_parts.append(
            "Bu kapsamlı haber özeti tüm kaynaklardan gelen bilgileri birleştirmektedir."
        )

        unified_description = "\n".join(description_parts)

        return {
            "title": unified_title,
            "description": unified_description,
            "available_images": available_images,
        }

    except Exception as e:
        logger.warning(f"Even fallback summary failed: {e}")
        return {
            "title": articles[0].title,
            "description": articles[0].summary or "İçerik mevcut değil",
            "available_images": [],
        }


def fetch_single_source_news(
    source: NewsSource, max_articles: int = 20
) -> List[NewsArticle]:
    """Fetch news from a single RSS source"""
    logger.info(f"Fetching news from {source.name}")

    try:
        # Set a proper user agent to avoid blocking
        feedparser.USER_AGENT = "AIris Financial News Aggregator/1.0"

        # All sources are now reliable after removing Yeni Akit

        # Parse the RSS feed with proper encoding handling
        feed = feedparser.parse(source.rss_url)

        # Check if we got any entries at all
        if not hasattr(feed, "entries") or len(feed.entries) == 0:
            logger.warning(f"No entries found in RSS feed for {source.name}")
            return []

        # Check for parsing issues (but be more lenient)
        if feed.bozo:
            # Only log encoding warnings at DEBUG level to reduce noise
            exception_str = str(feed.bozo_exception).lower()
            if "encoding" in exception_str or "us-ascii" in exception_str:
                logger.debug(
                    f"Minor encoding issue for {source.name}: {feed.bozo_exception}"
                )
            else:
                logger.warning(
                    f"RSS feed parse warning for {source.name}: {feed.bozo_exception}"
                )

            # Skip if it's a critical parsing error (not just encoding issues)
            if "not well-formed" in exception_str:
                logger.error(f"Critical XML parsing error for {source.name}, skipping")
                return []

        # Extract news articles
        news_articles = []
        processed_count = 0

        for entry in feed.entries:
            if processed_count >= max_articles:
                break

            try:
                # Clean the title and summary
                if source.language == "tr":
                    title = clean_turkish_text(entry.get("title", "No title"))
                    summary = clean_turkish_text(
                        entry.get("summary", "") or entry.get("description", "")
                    )
                else:
                    title = entry.get("title", "No title")
                    summary = entry.get("summary", "") or entry.get("description", "")

                # Skip articles with no meaningful content
                if not title or title == "No title":
                    continue

                # Extract image information
                image_url, image_width, image_height = extract_image_info(entry)

                # Normalize the published date to Turkish timezone
                published_date = entry.get("published", "")
                if published_date:
                    try:
                        # Convert to Turkish time and format consistently
                        normalized_date = normalize_datetime(published_date)
                        # Format as ISO string for consistent frontend parsing
                        published_date = normalized_date.isoformat()
                    except:
                        # Keep original if normalization fails
                        pass

                article = NewsArticle(
                    title=title,
                    link=entry.get("link", ""),
                    published=published_date,
                    summary=summary,
                    source=source.name,
                    image_url=image_url,
                    image_width=image_width,
                    image_height=image_height,
                    source_language=source.language,
                )
                news_articles.append(article)
                processed_count += 1

            except Exception as entry_error:
                logger.warning(
                    f"Failed to process individual entry from {source.name}: {entry_error}"
                )
                continue

        logger.info(
            f"Successfully fetched {len(news_articles)} articles from {source.name}"
        )
        return news_articles

    except Exception as e:
        logger.error(f"Failed to fetch news from {source.name}: {str(e)}")
        return []


async def fetch_all_sources_news(
    sources: Optional[List[NewsSource]] = None, max_per_source: int = 20
) -> List[NewsArticle]:
    """Fetch news from all configured sources"""
    if sources is None:
        sources = FINANCIAL_NEWS_SOURCES

    all_articles = []

    # Use asyncio to fetch from multiple sources concurrently
    tasks = []
    for source in sources:
        # Run sync function in thread pool
        task = asyncio.get_event_loop().run_in_executor(
            None, fetch_single_source_news, source, max_per_source
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Failed to fetch from {sources[i].name}: {str(result)}")
        else:
            all_articles.extend(result)

    return all_articles


async def cluster_similar_articles(
    articles: List[NewsArticle],
) -> List[List[NewsArticle]]:
    if len(articles) <= 1:
        return [[article] for article in articles]

    try:
        # Use LLM-based clustering for intelligent story grouping
        from backend.utils.llm_clustering import cluster_articles_with_llm

        logger.info(f"🤖 Starting LLM-based clustering for {len(articles)} articles")

        # Get LLM clustering analysis
        cluster_result = await cluster_articles_with_llm(articles)

        # Convert LLM results to article clusters (simplified processing)
        clusters = []
        used_indices = set()

        # Process clustered articles first
        for cluster_info in cluster_result.clusters:
            if "article_indices" in cluster_info:
                article_indices = cluster_info["article_indices"]
                cluster = []
                for idx in article_indices:
                    if (
                        isinstance(idx, int)
                        and 0 <= idx < len(articles)
                        and idx not in used_indices
                    ):
                        cluster.append(articles[idx])
                        used_indices.add(idx)

                if len(cluster) > 0:
                    clusters.append(cluster)
                    theme = cluster_info.get("story_theme", "Unknown theme")
                    logger.debug(f"📰 Cluster '{theme}': {len(cluster)} articles")

        # Add remaining articles as singles
        for i in range(len(articles)):
            if i not in used_indices:
                clusters.append([articles[i]])
                used_indices.add(i)

        # Log final results
        multi_source_clusters = len([c for c in clusters if len(c) > 1])
        logger.info(
            f"✅ Clustering complete: {len(clusters)} total clusters, {multi_source_clusters} multi-source"
        )

        return clusters

    except Exception as e:
        logger.error(f"❌ LLM clustering failed: {e}")
        logger.info("🔄 Fallback: treating each article as individual cluster")
        return [[article] for article in articles]


async def get_aggregated_financial_news(
    sources: Optional[List[NewsSource]] = None, force_refresh: bool = False
) -> NewsResponse:
    from backend.utils.news_database import get_news_database

    logger.info(
        f"Starting aggregated financial news fetch (force_refresh={force_refresh})"
    )

    # Get database instance
    db = get_news_database()

    # If not forcing refresh, try to load from database first
    if not force_refresh:
        logger.info("📀 Loading news from database...")
        news_response = await get_news_from_database(db)

        # If database is empty, do an initial fetch to populate it
        if news_response.total_articles == 0:
            logger.info("📰 Database is empty, performing initial fetch...")
            return await get_aggregated_financial_news(
                sources=sources, force_refresh=True
            )

        return news_response

    # Force refresh: fetch new articles and update database
    logger.info("🔄 Force refresh: fetching new articles from RSS sources...")

    # Fetch all articles from all sources
    all_articles = await fetch_all_sources_news(sources)

    if not all_articles:
        logger.warning("No articles fetched from any source")
        # Return empty response but still check database
        return await get_news_from_database(db)

    # Sort articles by publication date (newest first)
    try:
        all_articles.sort(
            key=lambda x: normalize_datetime(x.published),
            reverse=True,
        )
    except Exception as sort_error:
        logger.warning(f"Could not sort articles by date: {sort_error}")

    deduplicated_articles = []
    for article in all_articles:
        if db.find_existing_news_by_links([article.link]):
            logger.info(f"🔗 Article already exists: {article.link}")
        else:
            deduplicated_articles.append(article)

    logger.info(
        f"🔄 Deduplicated {len(all_articles)} articles to {len(deduplicated_articles)}"
    )
    all_articles = deduplicated_articles

    # Cluster similar articles using embedding-based semantic similarity
    clusters = await cluster_similar_articles(all_articles)

    # Separate multi-source clusters from single articles
    multi_source_clusters = [cluster for cluster in clusters if len(cluster) > 1]

    logger.info(
        f"🔄 Processing {len(multi_source_clusters)} clusters with parallel AI summarization..."
    )

    # Run AI summarization for all clusters in parallel
    clustered_news = []
    if multi_source_clusters:
        try:
            # Create all AI summarization tasks concurrently
            summarization_tasks = [
                generate_unified_summary(cluster) for cluster in multi_source_clusters
            ]

            # Run all AI calls concurrently with timeout
            unified_summaries = await asyncio.wait_for(
                asyncio.gather(*summarization_tasks, return_exceptions=True),
                timeout=180,  # 3 minutes total timeout for all AI calls
            )

            logger.info(
                f"✅ Completed parallel AI summarization for {len(unified_summaries)} clusters"
            )

            # Process results and create ClusteredNews objects
            for cluster, summary_result in zip(
                multi_source_clusters, unified_summaries
            ):
                try:
                    # Handle potential exceptions from individual AI calls
                    if isinstance(summary_result, Exception):
                        logger.warning(
                            f"AI summarization failed for cluster: {summary_result}"
                        )
                        # Use fallback summarization
                        unified_summary = _create_fallback_summary(cluster)
                    else:
                        unified_summary = summary_result

                    sources_list = list(set([article.source for article in cluster]))

                    # Calculate relevance score based on number of sources
                    relevance_score = min(
                        1.0, len(sources_list) / 5.0
                    )  # Max score at 5+ sources

                    # Get earliest and latest publication dates
                    published_dates = []
                    for article in cluster:
                        if article.published:
                            try:
                                parsed_date = normalize_datetime(article.published)
                                published_dates.append(parsed_date)
                            except:
                                continue

                    earliest_date = (
                        min(published_dates).isoformat() if published_dates else ""
                    )
                    latest_date = (
                        max(published_dates).isoformat() if published_dates else ""
                    )

                    clustered_news.append(
                        ClusteredNews(
                            unified_title=unified_summary["title"],
                            unified_description=unified_summary["description"],
                            sources=sources_list,
                            articles=cluster,
                            available_images=unified_summary.get(
                                "available_images", []
                            ),
                            relevance_score=relevance_score,
                            published_earliest=earliest_date,
                            published_latest=latest_date,
                        )
                    )

                except Exception as e:
                    logger.error(f"Failed to process cluster: {e}")
                    continue

        except asyncio.TimeoutError:
            logger.error("❌ AI summarization timed out after 3 minutes")
            # Fallback: process clusters with basic summarization
            for cluster in multi_source_clusters:
                try:
                    unified_summary = _create_fallback_summary(cluster)
                    sources_list = list(set([article.source for article in cluster]))
                    relevance_score = min(1.0, len(sources_list) / 5.0)

                    published_dates = []
                    for article in cluster:
                        if article.published:
                            try:
                                parsed_date = normalize_datetime(article.published)
                                published_dates.append(parsed_date)
                            except:
                                continue

                    earliest_date = (
                        min(published_dates).isoformat() if published_dates else ""
                    )
                    latest_date = (
                        max(published_dates).isoformat() if published_dates else ""
                    )

                    clustered_news.append(
                        ClusteredNews(
                            unified_title=unified_summary["title"],
                            unified_description=unified_summary["description"],
                            sources=sources_list,
                            articles=cluster,
                            available_images=unified_summary.get(
                                "available_images", []
                            ),
                            relevance_score=relevance_score,
                            published_earliest=earliest_date,
                            published_latest=latest_date,
                        )
                    )
                except Exception as e:
                    logger.error(f"Even fallback processing failed: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Parallel AI summarization failed: {e}")
            # Emergency fallback
            for cluster in multi_source_clusters:
                try:
                    unified_summary = _create_fallback_summary(cluster)
                    sources_list = list(set([article.source for article in cluster]))
                    relevance_score = min(1.0, len(sources_list) / 5.0)

                    clustered_news.append(
                        ClusteredNews(
                            unified_title=unified_summary["title"],
                            unified_description=unified_summary["description"],
                            sources=sources_list,
                            articles=cluster,
                            available_images=unified_summary.get(
                                "available_images", []
                            ),
                            relevance_score=relevance_score,
                            published_earliest="",
                            published_latest="",
                        )
                    )
                except:
                    continue

    # Sort clustered news by relevance score (most sources first)
    clustered_news.sort(key=lambda x: x.relevance_score, reverse=True)

    logger.info(f"Created {len(clustered_news)} clusters")

    # Save clustered articles to database
    saved_count = 0
    for cluster in clustered_news:
        try:
            # Convert cluster to database format
            cluster_data = {
                "unified_title": cluster.unified_title,
                "unified_description": cluster.unified_description,
                "articles": [
                    {
                        "source": article.source,
                        "link": article.link,
                        "published": article.published,
                        "title": article.title,
                        "summary": article.summary,
                    }
                    for article in cluster.articles
                ],
                "available_images": cluster.available_images,
            }

            db.save_news_article(cluster_data)
            saved_count += 1

        except Exception as e:
            logger.error(f"❌ Failed to save cluster to database: {e}")
            continue

    logger.info(f"💾 Saved/updated {saved_count} news articles to database")

    # Return fresh data from database
    return await get_news_from_database(db)


async def get_news_from_database(db) -> NewsResponse:
    """Load news from database and convert to NewsResponse format"""
    try:
        # Get news from database
        db_news = db.get_all_news(limit=50)  # Get latest 50 news articles

        if not db_news:
            logger.info("📰 No news found in database")
            return NewsResponse(
                clustered_articles=[],
                total_clusters=0,
                total_articles=0,
                last_updated=datetime.datetime.now().isoformat(),
            )

        # Convert database records to ClusteredNews objects
        clustered_articles = []
        for news_record in db_news:
            try:
                # Convert sources back to articles format for frontend compatibility
                articles = []
                sources_dict = news_record.get("sources", {})

                for source_name, source_url in sources_dict.items():
                    # Create article object from stored data
                    article = NewsArticle(
                        title=news_record["unified_title"],
                        link=source_url,
                        published=news_record.get("earliest_published_at", ""),
                        summary=news_record["unified_description"],
                        source=source_name,
                        image_url="",  # Will be handled through available_images
                        image_width=0,
                        image_height=0,
                        source_language="tr",
                    )
                    articles.append(article)

                # Convert images back to available_images format
                available_images = []
                images_dict = news_record.get("images", {})

                for source_name, image_data in images_dict.items():
                    if isinstance(image_data, dict) and image_data.get("url"):
                        available_images.append(
                            {
                                "source": source_name,
                                "url": image_data["url"],
                                "width": image_data.get("width", 0),
                                "height": image_data.get("height", 0),
                                "article_index": 0,  # Default since we're not tracking this in DB
                            }
                        )

                # Create ClusteredNews object
                cluster = ClusteredNews(
                    unified_title=news_record["unified_title"],
                    unified_description=news_record["unified_description"],
                    sources=list(sources_dict.keys()),
                    articles=articles,
                    available_images=available_images,
                    relevance_score=min(1.0, len(sources_dict) / 5.0),
                    published_earliest=news_record.get("earliest_published_at", ""),
                    published_latest=news_record.get("latest_published_at", ""),
                )

                clustered_articles.append(cluster)

            except Exception as e:
                logger.error(f"Error converting database record to ClusteredNews: {e}")
                continue

        total_articles = sum(len(cluster.articles) for cluster in clustered_articles)

        logger.info(
            f"📰 Loaded {len(clustered_articles)} clustered articles from database ({total_articles} total articles)"
        )

        return NewsResponse(
            clustered_articles=clustered_articles,
            total_clusters=len(clustered_articles),
            total_articles=total_articles,
            last_updated=datetime.datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"❌ Error loading news from database: {e}")
        # Return empty response on error
        return NewsResponse(
            clustered_articles=[],
            total_clusters=0,
            total_articles=0,
            last_updated=datetime.datetime.now().isoformat(),
        )


def format_news_context(news_context: dict) -> str:
    """
    Format news context into a structured string for the agent.
    """
    context_parts = []

    # Basic news information
    if news_context.get("title"):
        context_parts.append(f"News Title: {news_context['title']}")

    if news_context.get("summary"):
        context_parts.append(f"News Summary: {news_context['summary']}")

    if news_context.get("content"):
        context_parts.append(f"News Content: {news_context['content']}")

    if news_context.get("source"):
        context_parts.append(f"News Source: {news_context['source']}")

    if news_context.get("sources") and isinstance(news_context["sources"], list):
        sources_str = ", ".join(news_context["sources"])
        context_parts.append(f"News Sources: {sources_str}")

    if news_context.get("published"):
        context_parts.append(f"Published: {news_context['published']}")

    if news_context.get("url"):
        context_parts.append(f"News URL: {news_context['url']}")

    # Cluster data if available
    if news_context.get("cluster_data"):
        cluster = news_context["cluster_data"]
        if cluster.get("unified_title"):
            context_parts.append(f"Cluster Title: {cluster['unified_title']}")
        if cluster.get("unified_description"):
            context_parts.append(
                f"Cluster Description: {cluster['unified_description']}"
            )
        if cluster.get("articles") and len(cluster["articles"]) > 1:
            context_parts.append(
                f"Related Articles: {len(cluster['articles'])} articles in this cluster"
            )

    return "\n\n".join(context_parts)
