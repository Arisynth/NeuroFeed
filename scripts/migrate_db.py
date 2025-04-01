#!/usr/bin/env python3
# 数据库迁移脚本 - 规范化article_id

import os
import sys

# 添加项目根目录到路径 - 修复导入路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 直接导入core模块中的NewsDBManager
from core.news_db_manager import NewsDBManager

if __name__ == "__main__":
    print("开始迁移数据库...")
    db_manager = NewsDBManager()
    stats = db_manager.migrate_normalize_article_ids()
    
    print("\n迁移统计:")
    print(f"- 更新的文章记录: {stats.get('news_articles', 0)}")
    print(f"- 更新的丢弃记录: {stats.get('discarded_articles', 0)}")
    print(f"- 更新的发送记录: {stats.get('sent_articles', 0)}")
    print(f"- 移除的重复记录: {stats.get('duplicates_removed', 0)}")
    print(f"- 处理错误: {stats.get('errors', 0)}")
    print("\n数据库迁移完成!")
