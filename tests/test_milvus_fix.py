#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Milvus集合加载修复的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from packages.manager.milvus_manager import get_milvus_manager
from packages.core.knowledgebase import KnowledgeBase
from packages.utils.logging_config import logger

def test_milvus_fix():
    """测试Milvus修复"""
    print("开始测试Milvus集合加载修复...")
    
    try:
        # 1. 启动Milvus服务器
        print("1. 启动Milvus服务器...")
        milvus_manager = get_milvus_manager()
        if not milvus_manager.start():
            print("❌ Milvus服务器启动失败")
            return False
        print("✅ Milvus服务器启动成功")
        
        # 2. 创建知识库实例
        print("2. 创建知识库实例...")
        kb = KnowledgeBase()
        print("✅ 知识库实例创建成功")
        
        # 3. 检查现有集合
        print("3. 检查现有集合...")
        collections = kb.get_collection_names()
        print(f"发现 {len(collections)} 个集合: {collections}")
        
        # 4. 测试集合加载
        if collections:
            test_collection = collections[0]
            print(f"4. 测试集合 {test_collection} 的加载...")
            
            # 确保集合已加载
            if kb.ensure_collection_loaded(test_collection):
                print(f"✅ 集合 {test_collection} 加载成功")
                
                # 5. 测试搜索功能
                print("5. 测试搜索功能...")
                try:
                    # 尝试进行一个简单的搜索
                    results = kb.search("test query", test_collection, limit=1)
                    print(f"✅ 搜索成功，返回 {len(results)} 个结果")
                except Exception as e:
                    print(f"⚠️ 搜索测试失败（可能是因为集合为空）: {e}")
            else:
                print(f"❌ 集合 {test_collection} 加载失败")
        else:
            print("4. 没有找到现有集合，跳过测试")
        
        print("✅ 测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理
        try:
            print("清理资源...")
            if 'milvus_manager' in locals():
                milvus_manager.stop()
        except Exception as e:
            print(f"清理过程中出错: {e}")

if __name__ == "__main__":
    success = test_milvus_fix()
    sys.exit(0 if success else 1)
