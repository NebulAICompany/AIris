from typing import List, Dict, Any
from dataclasses import dataclass
from backend.core.agents import create_clustering_agent
from backend.core.prompts import news_clustering_prompt
from backend.shared.logger import get_logger
from backend.utils.news import NewsArticle
from langchain_core.messages import HumanMessage

logger = get_logger("LLM_CLUSTERING")


@dataclass
class ClusterResult:
    """Result from LLM clustering analysis"""

    clusters: List[Dict[str, Any]]
    analysis: str


class LLMNewsClusterer:
    """
    Intelligent news clustering using LLM analysis.
    Understands Turkish financial context and story relationships.
    """

    def __init__(self):
        self.model = "gpt-4o-mini"  # Balance between accuracy and cost

    def _prepare_articles_for_analysis(self, articles: List[NewsArticle]) -> str:
        """
        Efficiently format articles for LLM analysis.
        Optimized for token usage while preserving essential information.
        """
        if not articles:
            return "No articles provided."

        # Create efficient, compact prompt
        prompt = f"""Analyze these {len(articles)} Turkish financial news articles and group them by story:

**Articles:**
"""

        for i, article in enumerate(articles):
            # Ultra-compact format: just index, source, title, and key summary
            title = article.title[:100] + ("..." if len(article.title) > 100 else "")
            summary_snippet = ""
            if article.summary and len(article.summary.strip()) > 10:
                summary_snippet = f" | {article.summary[:80]}..."

            prompt += f"[{i}] {article.source}: {title}{summary_snippet}\n"

        prompt += """
**Task:** Group articles covering the same Turkish financial story/event. 

Be conservative - only cluster truly related stories. You don't need to include all indices."""

        return prompt

    def _create_fallback_result(self, total_articles: int) -> ClusterResult:
        """Create fallback result when LLM parsing fails"""
        return ClusterResult(
            clusters=[], analysis="LLM clustering failed, returning empty clusters"
        )

    async def cluster_articles(self, articles: List[NewsArticle]) -> ClusterResult:
        """
        Main clustering method using LLM analysis.
        Returns structured cluster results.
        """
        if len(articles) <= 1:
            return ClusterResult(
                clusters=[],
                analysis=f"Only {len(articles)} article(s), no clustering needed",
            )

        logger.info(f"Starting LLM-based clustering for {len(articles)} articles")

        try:
            # Create clustering agent
            agent = create_clustering_agent(news_clustering_prompt)

            # Prepare articles for analysis
            analysis_prompt = self._prepare_articles_for_analysis(articles)

            # Log token estimate (rough)
            estimated_tokens = len(analysis_prompt.split()) * 1.3  # Rough estimate
            logger.info(f"Estimated tokens for clustering: ~{estimated_tokens:.0f}")

            # Get LLM analysis with timeout protection
            logger.info("Sending clustering request to LLM...")
            import asyncio

            try:
                # Add timeout to prevent hanging (2 minutes max)
                result = await asyncio.wait_for(
                    agent.ainvoke(
                        {"messages": [HumanMessage(content=analysis_prompt)]}
                    ),
                    timeout=120,  # 2 minutes
                )
                logger.info("LLM response received")
            except asyncio.TimeoutError:
                logger.error("LLM clustering timed out after 2 minutes")
                return self._create_fallback_result(len(articles))

            # Extract structured output (same pattern as main agent)
            if not isinstance(result, dict) or "structured_response" not in result:
                logger.error("No structured_response found in result")
                return self._create_fallback_result(len(articles))

            structured_data = result["structured_response"]
            data = structured_data.model_dump()

            # Extract clusters and analysis
            clusters = data.get("clusters", [])
            analysis = data.get("analysis", "LLM clustering completed")

            logger.info(f"LLM clustering parsed: {len(clusters)} clusters")

            cluster_result = ClusterResult(clusters=clusters, analysis=analysis)

            # Log final results
            multi_clusters = len(
                [
                    c
                    for c in cluster_result.clusters
                    if len(c.get("article_indices", [])) > 1
                ]
            )
            logger.info(
                f"✅ LLM clustering completed: {len(cluster_result.clusters)} total clusters, {multi_clusters} multi-article clusters"
            )

            return cluster_result

        except Exception as e:
            logger.error(f"❌ LLM clustering failed: {e}")
            logger.info("Using fallback: treating each article as individual cluster")
            return self._create_fallback_result(len(articles))


# Global instance for reuse
_clusterer = None


def get_llm_clusterer() -> LLMNewsClusterer:
    """Get global LLM clusterer instance (singleton pattern)"""
    global _clusterer
    if _clusterer is None:
        _clusterer = LLMNewsClusterer()
    return _clusterer


async def cluster_articles_with_llm(articles: List[NewsArticle]) -> ClusterResult:
    """
    Convenience function for LLM-based clustering.

    Args:
        articles: List of news articles to cluster

    Returns:
        ClusterResult with intelligent clusters based on story understanding
    """
    clusterer = get_llm_clusterer()
    return await clusterer.cluster_articles(articles)
