"""
查询预处理器 - 从用户查询中提取元数据过滤条件
"""

import re
from datetime import datetime
from typing import Dict, Optional, Any
from ..utils import logger


class QueryPreprocessor:
    """查询预处理器 (简化版) - 仅提取日期并生成 date_key 用于过滤"""

    def __init__(self, enabled=True):
        self.enabled = enabled
        
        # 月份名称映射
        self.month_names = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }

    def extract_metadata_filters(self, query: str) -> Dict[str, Any]:
        """从查询中提取 date_key 过滤条件"""
        if not self.enabled:
            return {}
            
        filters = {}
        date_key = self._extract_date_key(query)
        if date_key:
            filters['date_key'] = date_key
        
        logger.info(f"提取的元数据过滤条件: {filters}")
        return filters

    def _extract_date_key(self, query: str) -> Optional[str]:
        """从查询中解析日期，并返回 'YYYYMMDD' 格式的字符串"""
        
        # 匹配 YYYY年M月D日
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', query)
        if match:
            year, month, day = map(int, match.groups())
            return f"{year:04d}{month:02d}{day:02d}"

        # 匹配 YYYY-MM-DD
        match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', query)
        if match:
            year, month, day = map(int, match.groups())
            return f"{year:04d}{month:02d}{day:02d}"

        # 匹配 Month Day, Year (e.g., January 6, 2025)
        month_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})'
        match = re.search(month_pattern, query, re.IGNORECASE)
        if match:
            month_name, day_str, year_str = match.groups()
            year, day = int(year_str), int(day_str)
            month = self.month_names.get(month_name.lower())
            if month:
                return f"{year:04d}{month:02d}{day:02d}"
        
        # 匹配 M月D日 (假设是当前年份)
        match = re.search(r'(\d{1,2})月(\d{1,2})日', query)
        if match:
            month, day = map(int, match.groups())
            year = datetime.now().year
            return f"{year:04d}{month:02d}{day:02d}"
            
        return None

    def build_milvus_filter(self, filters: Dict[str, Any]) -> Optional[str]:
        """构建 Milvus 的 date_key 精确匹配过滤表达式"""
        if not filters or 'date_key' not in filters:
            return None
        
        date_key = filters['date_key']
        # 使用静态字段进行过滤
        return f"date_key == '{date_key}'"
