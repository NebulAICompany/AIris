import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from backend.shared.logger import get_logger

logger = get_logger("NEWS_DATABASE")


class NewsDatabase:
    """Manages SQLite database for financial news storage"""

    def __init__(self, db_path: str = "backend/database/financial_news.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()

    def init_database(self):
        """Initialize database with news table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS financial_news (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        unified_title TEXT NOT NULL,
                        unified_description TEXT NOT NULL,
                        sources TEXT NOT NULL,  -- JSON: {"source_name": "url", ...}
                        images TEXT,  -- JSON: {"source_name": {"url": "...", "width": 0, "height": 0}, ...}
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        earliest_published_at TIMESTAMP,
                        latest_published_at TIMESTAMP
                    )
                """
                )

                # Create index for faster link matching
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sources ON financial_news(sources)
                """
                )

                # Create index for date sorting
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_earliest_published 
                    ON financial_news(earliest_published_at DESC)
                """
                )

                conn.commit()
                logger.info("✅ Database initialized successfully")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    def normalize_url(self, url: str) -> str:
        """Normalize URL for comparison by removing variations"""
        try:
            parsed = urlparse(url.lower())

            # Remove www prefix
            domain = parsed.netloc.replace("www.", "")

            # Use https by default
            scheme = "https"

            # Remove query parameters and fragments for comparison
            path = parsed.path.rstrip("/")

            normalized = f"{scheme}://{domain}{path}"
            return normalized

        except Exception:
            # If parsing fails, return original URL lowercased
            return url.lower().strip()

    def extract_links_from_sources(self, sources_json: str) -> List[str]:
        """Extract and normalize all links from sources JSON"""
        try:
            sources = json.loads(sources_json)
            if isinstance(sources, dict):
                links = list(sources.values())
            elif isinstance(sources, list):
                links = sources
            else:
                return []

            # Normalize all links
            return [self.normalize_url(link) for link in links if link]

        except Exception:
            return []

    def find_existing_news_by_links(
        self, new_links: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Find existing news entry that shares any link with new article"""
        if not new_links:
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get all existing news
                cursor.execute("SELECT * FROM financial_news")
                existing_news = cursor.fetchall()

                # Normalize new links
                normalized_new_links = [self.normalize_url(link) for link in new_links]

                for news in existing_news:
                    existing_links = self.extract_links_from_sources(news["sources"])

                    # Check for any match
                    if any(
                        new_link in existing_links for new_link in normalized_new_links
                    ):
                        logger.info(
                            f"🔗 Found existing news match: {news['unified_title']}"
                        )
                        return dict(news)
                return None

        except Exception as e:
            logger.error(f"❌ Error finding existing news: {e}")
            return None

    def save_news_article(self, clustered_news_data: Dict[str, Any]) -> int:
        """Save or update news article in database"""
        try:
            # Extract data from clustered news
            unified_title = clustered_news_data.get("unified_title", "")
            unified_description = clustered_news_data.get("unified_description", "")
            articles = clustered_news_data.get("articles", [])
            available_images = clustered_news_data.get("available_images", [])

            # Build sources dictionary
            sources = {}
            all_links = []
            earliest_published = None
            latest_published = None

            logger.info(f"🔗 Articles: {len(articles)}")
            for article in articles:
                if article.get("source") and article.get("link"):
                    sources[article["source"]] = article["link"]
                    all_links.append(article["link"])

                    # Track publication dates
                    if article.get("published"):
                        try:
                            pub_date = datetime.fromisoformat(
                                article["published"].replace("Z", "+00:00")
                            )
                            if (
                                earliest_published is None
                                or pub_date < earliest_published
                            ):
                                earliest_published = pub_date
                            if latest_published is None or pub_date > latest_published:
                                latest_published = pub_date
                        except:
                            continue

            # Build images dictionary
            images = {}
            for img in available_images:
                source_name = img.get("source", "Unknown")
                images[source_name] = {
                    "url": img.get("url", ""),
                    "width": img.get("width", 0),
                    "height": img.get("height", 0),
                }
            logger.info(f"🔗 Images: {len(images)}")

            # Check if news already exists
            logger.info(f"🔗 All links: {len(all_links)}")
            existing_news = self.find_existing_news_by_links(all_links)
            logger.info(
                f"🔗 Existing news: {len(existing_news) if existing_news else 0}"
            )

            current_time = datetime.now(timezone.utc)

            with sqlite3.connect(self.db_path) as conn:
                if existing_news:
                    # Update existing news
                    existing_id = existing_news["id"]

                    # Merge sources
                    existing_sources = json.loads(existing_news["sources"])
                    merged_sources = {**existing_sources, **sources}

                    # Merge images
                    existing_images = json.loads(existing_news.get("images", "{}"))
                    merged_images = {**existing_images, **images}

                    # Update earliest published date if needed
                    existing_earliest = (
                        datetime.fromisoformat(existing_news["earliest_published_at"])
                        if existing_news["earliest_published_at"]
                        else None
                    )
                    if earliest_published and (
                        not existing_earliest or earliest_published < existing_earliest
                    ):
                        new_earliest = earliest_published
                    else:
                        new_earliest = existing_earliest

                    # Update latest published date if needed
                    existing_latest = (
                        datetime.fromisoformat(existing_news["latest_published_at"])
                        if existing_news["latest_published_at"]
                        else None
                    )
                    if latest_published and (
                        not existing_latest or latest_published > existing_latest
                    ):
                        new_latest = latest_published
                    else:
                        new_latest = existing_latest

                    conn.execute(
                        """
                        UPDATE financial_news 
                        SET sources = ?, 
                            images = ?, 
                            updated_at = ?,
                            earliest_published_at = ?,
                            latest_published_at = ?
                        WHERE id = ?
                    """,
                        (
                            json.dumps(merged_sources),
                            json.dumps(merged_images),
                            current_time.isoformat(),
                            new_earliest.isoformat() if new_earliest else None,
                            new_latest.isoformat() if new_latest else None,
                            existing_id,
                        ),
                    )

                    logger.info(
                        f"📰 Updated existing news: {unified_title} (ID: {existing_id})"
                    )
                    return existing_id

                else:
                    # Insert new news
                    cursor = conn.execute(
                        """
                        INSERT INTO financial_news 
                        (unified_title, unified_description, sources, images, 
                         created_at, updated_at, earliest_published_at, latest_published_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            unified_title,
                            unified_description,
                            json.dumps(sources),
                            json.dumps(images),
                            current_time.isoformat(),
                            current_time.isoformat(),
                            (
                                earliest_published.isoformat()
                                if earliest_published
                                else None
                            ),
                            latest_published.isoformat() if latest_published else None,
                        ),
                    )

                    news_id = cursor.lastrowid
                    logger.info(f"📰 Saved new news: {unified_title} (ID: {news_id})")
                    return news_id

        except Exception as e:
            logger.error(f"❌ Error saving news article: {e}")
            raise

    def get_all_news(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all news from database, ordered by earliest published date (newest first)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT * FROM financial_news 
                    ORDER BY 
                        COALESCE(earliest_published_at, created_at) DESC,
                        created_at DESC
                    LIMIT ? OFFSET ?
                """,
                    (limit, offset),
                )

                news_records = cursor.fetchall()

                # Convert to list of dictionaries with parsed JSON
                news_list = []
                for record in news_records:
                    news_dict = dict(record)

                    # Parse JSON fields
                    try:
                        news_dict["sources"] = json.loads(news_dict["sources"])
                    except:
                        news_dict["sources"] = {}

                    try:
                        news_dict["images"] = json.loads(news_dict.get("images", "{}"))
                    except:
                        news_dict["images"] = {}

                    news_list.append(news_dict)

                logger.info(
                    f"📰 Retrieved {len(news_list)} news articles from database"
                )
                return news_list

        except Exception as e:
            logger.error(f"❌ Error retrieving news: {e}")
            return []

    def get_news_count(self) -> int:
        """Get total count of news articles in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM financial_news")
                count = cursor.fetchone()[0]
                return count
        except Exception as e:
            logger.error(f"❌ Error getting news count: {e}")
            return 0

    def delete_old_news(self, days_to_keep: int = 30):
        """Delete news older than specified days"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM financial_news 
                    WHERE created_at < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    logger.info(f"🗑️ Deleted {deleted_count} old news articles")

        except Exception as e:
            logger.error(f"❌ Error deleting old news: {e}")


# Global database instance
_news_db = None


def get_news_database() -> NewsDatabase:
    """Get or create global news database instance"""
    global _news_db
    if _news_db is None:
        _news_db = NewsDatabase()
    return _news_db
