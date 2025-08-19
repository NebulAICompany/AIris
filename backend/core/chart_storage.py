"""
Chart Storage System - Stores chart HTML separately to avoid context pollution
"""

import uuid
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from backend.shared.logger import get_logger
from backend.shared.constants import DATABASE_DIR

logger = get_logger()

class ChartStorage:
    """Manages storage and retrieval of chart HTML files"""
    
    def __init__(self):
        # Create charts directory
        self.charts_dir = Path(DATABASE_DIR) / "charts"
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for quick access (chart_id -> metadata)
        self.chart_metadata: Dict[str, Dict] = {}
        
        logger.info(f"Chart storage initialized at: {self.charts_dir}")
    
    def store_chart(self, chart_html: str, chart_type: str, symbol: str = None, symbols: list = None) -> str:
        """
        Store chart HTML and return a unique chart ID
        
        Args:
            chart_html: The HTML content of the chart
            chart_type: Type of chart ('interactive' or 'comparison')
            symbol: Single symbol for interactive charts
            symbols: List of symbols for comparison charts
            
        Returns:
            str: Unique chart ID
        """
        chart_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Create chart file
        chart_file = self.charts_dir / f"{chart_id}.html"
        
        try:
            # Write HTML to file
            with open(chart_file, 'w', encoding='utf-8') as f:
                f.write(chart_html)
            
            # Store metadata
            metadata = {
                'chart_id': chart_id,
                'chart_type': chart_type,
                'symbol': symbol,
                'symbols': symbols,
                'created_at': timestamp,
                'file_path': str(chart_file)
            }
            
            self.chart_metadata[chart_id] = metadata
            
            logger.info(f"Chart stored with ID: {chart_id} ({chart_type})")
            return chart_id
            
        except Exception as e:
            logger.error(f"Failed to store chart: {str(e)}")
            # Clean up file if it was created
            if chart_file.exists():
                chart_file.unlink()
            raise
    
    def get_chart(self, chart_id: str) -> Optional[str]:
        """
        Retrieve chart HTML by chart ID
        
        Args:
            chart_id: The unique chart identifier
            
        Returns:
            str: Chart HTML content or None if not found
        """
        if chart_id not in self.chart_metadata:
            logger.warning(f"Chart not found in metadata: {chart_id}")
            return None
        
        metadata = self.chart_metadata[chart_id]
        chart_file = Path(metadata['file_path'])
        
        if not chart_file.exists():
            logger.warning(f"Chart file not found: {chart_file}")
            # Clean up metadata
            del self.chart_metadata[chart_id]
            return None
        
        try:
            with open(chart_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            logger.debug(f"Retrieved chart: {chart_id}")
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to read chart file {chart_id}: {str(e)}")
            return None
    
    def get_chart_metadata(self, chart_id: str) -> Optional[Dict]:
        """Get chart metadata by ID"""
        return self.chart_metadata.get(chart_id)
    
    def list_charts(self, limit: int = 50) -> list:
        """List recent charts with metadata"""
        charts = list(self.chart_metadata.values())
        # Sort by creation time (newest first)
        charts.sort(key=lambda x: x['created_at'], reverse=True)
        return charts[:limit]
    
    def cleanup_old_charts(self, max_age_hours: int = 24):
        """Remove charts older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        charts_to_remove = []
        
        for chart_id, metadata in self.chart_metadata.items():
            if metadata['created_at'] < cutoff_time:
                charts_to_remove.append(chart_id)
        
        for chart_id in charts_to_remove:
            self.delete_chart(chart_id)
        
        if charts_to_remove:
            logger.info(f"Cleaned up {len(charts_to_remove)} old charts")
    
    def delete_chart(self, chart_id: str) -> bool:
        """Delete a chart by ID"""
        if chart_id not in self.chart_metadata:
            return False
        
        metadata = self.chart_metadata[chart_id]
        chart_file = Path(metadata['file_path'])
        
        try:
            # Remove file
            if chart_file.exists():
                chart_file.unlink()
            
            # Remove metadata
            del self.chart_metadata[chart_id]
            
            logger.info(f"Deleted chart: {chart_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete chart {chart_id}: {str(e)}")
            return False

# Global chart storage instance
chart_storage = ChartStorage()