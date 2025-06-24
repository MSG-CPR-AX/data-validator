"""pytest 설정 파일"""

import pytest
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

@pytest.fixture(autouse=True)
def setup_test_environment():
    """모든 테스트에 자동으로 적용되는 환경 설정"""
    # 테스트용 환경 변수 기본값 설정 (최소한의 필수 변수만)
    test_env = {
        'CI_SERVER_URL': 'https://gitlab.test.com',
        'CI_PROJECT_ID': '999',
        'BOOKMARK_DATA_GROUP_ID': '888',
        'CI_PROJECT_DIR': '/tmp/test'
    }
    
    for key, value in test_env.items():
        if key not in os.environ:
            os.environ[key] = value
    
    yield
    
    # 테스트 후 정리는 필요에 따라 추가

@pytest.fixture
def clean_environment():
    """각 테스트마다 깨끗한 환경 변수 상태를 제공하는 fixture"""
    # 암호화 관련 환경 변수들을 일시적으로 제거
    crypto_vars = [
        'ENCRYPTED_PAT',
        'PAT_ENCRYPTION_KEY', 
        'ENCRYPTED_DEPLOY_TOKEN',
        'ENCRYPTION_KEY',
        'DEPLOY_TOKEN_USERNAME'
    ]
    
    original_values = {}
    for var in crypto_vars:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]
    
    yield
    
    # 원래 값 복원
    for var, value in original_values.items():
        os.environ[var] = value