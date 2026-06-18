"""
SQLAlchemy ORM 模型定义

基于 scripts/init-postgres.sql 定义的数据库表结构
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, Text, Integer, BigInteger, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from ..utils.postgres_manager import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = Column(String(255), nullable=False, unique=True, index=True)
    username: Mapped[str] = Column(String(100), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = Column(String(255), nullable=False)
    email: Mapped[Optional[str]] = Column(String(255), nullable=True, index=True)
    display_name: Mapped[Optional[str]] = Column(String(100), nullable=True)
    is_active: Mapped[bool] = Column(Boolean, default=True)
    is_superuser: Mapped[bool] = Column(Boolean, default=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[Dict] = Column("metadata", JSONB, default=dict)

    __table_args__ = (
        Index("ix_user_email_active", "email", "is_active"),
    )

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        result = {
            "id": str(self.id),
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "metadata": self.metadata_
        }
        if not include_sensitive:
            result.pop("password_hash", None)
        return result


class KnowledgeDatabase(Base):
    """知识库数据库表"""
    __tablename__ = "knowledge_databases"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    db_id: Mapped[str] = Column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = Column(String(255), nullable=False)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    creator_id: Mapped[Optional[str]] = Column(String(255), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    status: Mapped[str] = Column(String(50), default="active")
    metadata_: Mapped[Dict] = Column("metadata", JSONB, default=dict)

    documents: Mapped[List["Document"]] = relationship("Document", back_populates="knowledge_db", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "db_id": self.db_id,
            "name": self.name,
            "description": self.description,
            "creator_id": self.creator_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status,
            "metadata": self.metadata_
        }


class Document(Base):
    """文档表"""
    __tablename__ = "documents"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    db_id: Mapped[str] = Column(String(255), ForeignKey("knowledge_databases.db_id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[str] = Column(String(255), nullable=False, index=True)
    title: Mapped[Optional[str]] = Column(String(500), nullable=True)
    content: Mapped[Optional[str]] = Column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = Column(Text, nullable=True)
    file_type: Mapped[Optional[str]] = Column(String(100), nullable=True)
    file_size: Mapped[Optional[int]] = Column(BigInteger, nullable=True)
    chunk_count: Mapped[int] = Column(Integer, default=0)
    creator_id: Mapped[Optional[str]] = Column(String(255), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_: Mapped[Dict] = Column("metadata", JSONB, default=dict)

    knowledge_db: Mapped["KnowledgeDatabase"] = relationship("KnowledgeDatabase", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("db_id", "document_id", name="uq_db_document_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "db_id": self.db_id,
            "document_id": self.document_id,
            "title": self.title,
            "content": self.content,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "chunk_count": self.chunk_count,
            "creator_id": self.creator_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata_
        }


class DocumentChunk(Base):
    """文档块表"""
    __tablename__ = "document_chunks"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[UUID] = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id: Mapped[str] = Column(String(255), nullable=False, index=True)
    content: Mapped[str] = Column(Text, nullable=False)
    chunk_index: Mapped[Optional[int]] = Column(Integer, nullable=True)
    token_count: Mapped[Optional[int]] = Column(Integer, nullable=True)
    creator_id: Mapped[Optional[str]] = Column(String(255), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow)
    metadata_: Mapped[Dict] = Column("metadata", JSONB, default=dict)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "chunk_id": self.chunk_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            "creator_id": self.creator_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata_
        }


class ChatSession(Base):
    """会话表"""
    __tablename__ = "chat_sessions"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = Column(String(255), nullable=False, unique=True, index=True)
    user_id: Mapped[Optional[str]] = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[Optional[str]] = Column(String(500), nullable=True)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow)
    message_count: Mapped[int] = Column(Integer, default=0)
    metadata_: Mapped[Dict] = Column("metadata", JSONB, default=dict)

    messages: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "message_count": self.message_count,
            "metadata": self.metadata_
        }


class ChatMessage(Base):
    """聊天消息表"""
    __tablename__ = "chat_messages"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = Column(String(255), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[str] = Column(String(255), nullable=False)
    role: Mapped[str] = Column(String(50), nullable=False)
    content: Mapped[str] = Column(Text, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow)
    token_count: Mapped[Optional[int]] = Column(Integer, nullable=True)
    metadata_: Mapped[Dict] = Column("metadata", JSONB, default=dict)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "token_count": self.token_count,
            "metadata": self.metadata_
        }


class VectorIndexTask(Base):
    """向量索引任务表"""
    __tablename__ = "vector_index_tasks"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[str] = Column(String(255), nullable=False, unique=True, index=True)
    db_id: Mapped[str] = Column(String(255), ForeignKey("knowledge_databases.db_id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[Optional[UUID]] = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    status: Mapped[str] = Column(String(50), default="pending")
    progress: Mapped[int] = Column(Integer, default=0)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message: Mapped[Optional[str]] = Column(Text, nullable=True)
    metadata_: Mapped[Dict] = Column("metadata", JSONB, default=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "task_id": self.task_id,
            "db_id": self.db_id,
            "document_id": str(self.document_id) if self.document_id else None,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "error_message": self.error_message,
            "metadata": self.metadata_
        }


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_config"

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_key: Mapped[str] = Column(String(255), nullable=False, unique=True, index=True)
    config_value: Mapped[Dict] = Column(JSONB, nullable=False)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "config_key": self.config_key,
            "config_value": self.config_value,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


__all__ = [
    "Base",
    "User",
    "KnowledgeDatabase",
    "Document",
    "DocumentChunk",
    "ChatSession",
    "ChatMessage",
    "VectorIndexTask",
    "SystemConfig",
]
