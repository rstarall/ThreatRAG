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
        """从查询中提取 date_key 过滤条件（支持多日期）"""
        if not self.enabled:
            return {}
            
        filters = {}
        date_keys = self._extract_date_keys(query)  # 改为复数形式，支持多个日期
        if date_keys:
            filters['date_keys'] = date_keys  # 使用 date_keys 键存储列表
        
        logger.info(f"提取的元数据过滤条件: {filters}")
        return filters

    def _extract_date_keys(self, query: str) -> list:
        """从查询中解析所有日期，并返回 'YYYYMMDD' 格式的字符串列表"""
        date_keys = []
        
        # 匹配所有 YYYY年M月D日 格式
        for match in re.finditer(r'(\d{4})年(\d{1,2})月(\d{1,2})日', query):
            year, month, day = map(int, match.groups())
            date_key = f"{year:04d}{month:02d}{day:02d}"
            if date_key not in date_keys:
                date_keys.append(date_key)

        # 匹配所有 YYYY-MM-DD 格式
        for match in re.finditer(r'(\d{4})-(\d{1,2})-(\d{1,2})', query):
            year, month, day = map(int, match.groups())
            date_key = f"{year:04d}{month:02d}{day:02d}"
            if date_key not in date_keys:
                date_keys.append(date_key)

        # 匹配所有 Month Day, Year 格式 (e.g., January 6, 2025)
        month_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})'
        for match in re.finditer(month_pattern, query, re.IGNORECASE):
            month_name, day_str, year_str = match.groups()
            year, day = int(year_str), int(day_str)
            month = self.month_names.get(month_name.lower())
            if month:
                date_key = f"{year:04d}{month:02d}{day:02d}"
                if date_key not in date_keys:
                    date_keys.append(date_key)
        
        # 匹配所有 M月D日 格式 (假设是当前年份)
        for match in re.finditer(r'(\d{1,2})月(\d{1,2})日', query):
            month, day = map(int, match.groups())
            year = datetime.now().year
            date_key = f"{year:04d}{month:02d}{day:02d}"
            if date_key not in date_keys:
                date_keys.append(date_key)
            
        return date_keys

    def build_milvus_filter(self, filters: Dict[str, Any]) -> Optional[str]:
        """构建 Milvus 的 date_key 过滤表达式（支持多日期 OR 逻辑）"""
        if not filters or 'date_keys' not in filters:
            return None
        
        date_keys = filters['date_keys']
        if not date_keys:
            return None
        
        # 如果只有一个日期，使用简单的等号匹配
        if len(date_keys) == 1:
            return f"date_key == '{date_keys[0]}'"
        
        # 如果有多个日期，使用 OR 逻辑连接
        or_conditions = [f"date_key == '{dk}'" for dk in date_keys]
        return "(" + " or ".join(or_conditions) + ")"
