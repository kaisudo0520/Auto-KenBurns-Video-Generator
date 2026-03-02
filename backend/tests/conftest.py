"""
Pytest 配置文件

提供測試所需的 fixtures 和配置
"""

import sys
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 將 backend 目錄加入 Python 路徑
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 測試用資料庫 - 使用 in-memory
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def test_engine():
    """建立測試用 engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    # 建立 tables - 需要先導入所有模型
    from backend.database.connection import Base
    from backend.models import project, file, image_asset, audio_asset, render_job, settings
    Base.metadata.create_all(bind=engine)

    yield engine

    # 清理
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db(test_engine):
    """建立測試用資料庫"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    yield TestingSessionLocal


@pytest.fixture
def client(test_engine):
    """建立 FastAPI 測試客戶端"""
    from backend.main import app
    from backend import deps
    from sqlalchemy.orm import sessionmaker

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[deps.get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def sample_audio_path(tmp_path):
    """建立測試用的音訊檔案（模擬）"""
    # 注意：實際測試時應使用真實的音訊檔案
    # 這裡建立一個空檔案作為佔位
    audio_path = tmp_path / "test_audio.mp3"
    audio_path.write_bytes(b'fake audio data')

    return str(audio_path)


@pytest.fixture
def sample_images_list():
    """測試用的圖片列表"""
    return [
        {
            "path": "/fake/path/image1.jpg",
            "width": 1920,
            "height": 1080,
            "subject_regions": []
        },
        {
            "path": "/fake/path/image2.jpg",
            "width": 1920,
            "height": 1080,
            "subject_regions": [
                {"type": "head", "bounds": {"x": 0.4, "y": 0.1, "width": 0.2, "height": 0.25}},
                {"type": "body", "bounds": {"x": 0.3, "y": 0.35, "width": 0.4, "height": 0.5}}
            ]
        }
    ]


@pytest.fixture
def sample_audio_list(tmp_path):
    """測試用的音訊列表"""
    audio_files = []

    for i in range(2):
        audio_path = tmp_path / f"test_audio_{i}.mp3"
        audio_path.write_bytes(b'fake audio data')
        audio_files.append(str(audio_path))

    return audio_files


@pytest.fixture
def mock_bpm_analysis():
    """模擬的 BPM 分析結果"""
    from backend.services.kenburns_service import BPMAnalysis

    return BPMAnalysis(
        bpm=120.0,
        beats_per_measure=4,
        beat_duration=0.5,
        onset_times=[0.0, 0.5, 1.0, 1.5, 2.0]
    )
