import time

# src/storage/db/models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean,ForeignKey,Text,func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
from sqlalchemy.orm import relationship


Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)  # 存储哈希后的密码
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, nullable=True)  # 可选字段，用于兼容旧系统
    
    # 添加登录相关字段
    login_failed_count = Column(Integer, default=0)
    login_locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    
      # 添加这一行，定义与 OperationLog 的关系
    operation_logs = relationship("OperationLog", back_populates="user")
    
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "user_id": str(self.user_id) if self.user_id else str(self.id),
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M:%S") if self.last_login else None
        }
    
    def is_login_locked(self):
        if self.login_locked_until and self.login_locked_until > datetime.now():
            return True
        return False
    
    def get_remaining_lock_time(self):
        if not self.login_locked_until:
            return 0
        
        remaining = (self.login_locked_until - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    def increment_failed_login(self):
        self.login_failed_count += 1
        
        # 设置锁定时间，根据失败次数增加锁定时长
        if self.login_failed_count >= 5:
            lock_minutes = min(30, 2 ** (self.login_failed_count - 5))  # 指数增长，最多30分钟
            self.login_locked_until = datetime.now() + timedelta(minutes=lock_minutes)
    
    def reset_failed_login(self):
        self.login_failed_count = 0
        self.login_locked_until = None


class OperationLog(Base):
    """操作日志模型"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operation = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=func.now())

    # 关联用户
    user = relationship("User", back_populates="operation_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "operation": self.operation,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class ChatSession(Base):
    """聊天会话模型"""
    
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(50), nullable=True)  # 会话标题（最大50字符）
    system_prompt = Column(Text, nullable=True)  # 系统提示词
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    is_deleted = Column(Integer, default=0)  # 软删除标记
    
    # 关联消息
    # 注意：user_id 不再是外键，而是直接使用 users.user_id 字段
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def to_dict(self, include_messages=False):
        result = {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "title": self.title,
            "system_prompt": self.system_prompt,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
        }
        if include_messages:
            result["messages"] = [msg.to_dict() for msg in self.messages if msg.is_deleted == 0]
        return result


class ChatMessage(Base):
    """聊天消息模型"""
    
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.session_id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    is_deleted = Column(Integer, default=0)  # 软删除标记
    
    # 扩展字段
    meta = Column(Text, nullable=True)  # JSON格式存储额外元数据
    
    # 关联会话
    session = relationship("ChatSession", back_populates="messages")
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_deleted": self.is_deleted,
            "meta": self.meta,
        }