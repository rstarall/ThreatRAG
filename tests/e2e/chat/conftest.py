#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e2e/chat/conftest.py
共享 fixtures
"""

import os
import uuid
import pytest
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(project_root, ".env"))


# ============================================================================
# Session / User Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def unique_session():
    return f"e2e_session_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def unique_user():
    return f"e2e_user_{uuid.uuid4().hex[:8]}"


# ============================================================================
# API Base URL Fixture
# ============================================================================

@pytest.fixture(scope="session")
def api_base_url():
    host = os.getenv("THREATRAG_API_HOST", "127.0.0.1")
    port = os.getenv("THREATRAG_API_PORT", "8000")
    return f"http://{host}:{port}"