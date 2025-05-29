#!/usr/bin/env python3
"""
북마크 검증 스크립트

이 스크립트는 북마크 데이터의 유효성을 검증하는 진입점입니다.
BookmarkValidationOrchestrator를 사용하여 로컬 및 원격 북마크 데이터를 수집하고 검증합니다.

사용법:
    python scripts/validate_bookmarks.py
"""

import sys
import logging
from app.orchestrator.validator_runner import DataValidationOrchestrator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

def main():
    """
    북마크 검증 메인 함수
    
    반환값:
        int: 성공 시 0, 실패 시 1
    """
    logger.info("북마크 검증 시작")
    
    # 오케스트레이터 생성 및 실행
    orchestrator = DataValidationOrchestrator()
    exit_code = orchestrator.run()
    
    if exit_code == 0:
        logger.info("북마크 검증 완료: 성공")
    else:
        logger.error("북마크 검증 완료: 실패")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())