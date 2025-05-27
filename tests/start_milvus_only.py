#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立启动Milvus服务器的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ..packages.manager.milvus_manager import get_milvus_manager
from ..packages.utils.logging_config import logger

def start_milvus_only():
    """只启动Milvus服务器"""
    print("启动Milvus服务器...")
    
    try:
        milvus_manager = get_milvus_manager()
        if milvus_manager.start():
            print("✅ Milvus服务器启动成功")
            
            # 保持运行
            print("Milvus服务器正在运行，按Ctrl+C停止...")
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n正在停止Milvus服务器...")
                milvus_manager.stop()
                print("✅ Milvus服务器已停止")
                return True
        else:
            print("❌ Milvus服务器启动失败")
            return False
            
    except Exception as e:
        print(f"❌ 启动过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = start_milvus_only()
    sys.exit(0 if success else 1)
