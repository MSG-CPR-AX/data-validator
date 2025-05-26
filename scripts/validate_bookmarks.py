#!/usr/bin/env python3
"""
북마크 YAML 검증기

이 스크립트는 bookmark-data 그룹 내 여러 프로젝트의 북마크 YAML 파일을 검증하여
요구되는 형식과 제약 조건을 만족하는지 확인합니다.

검증 규칙:
1. 필수 필드: url, name, category, domain
2. 모든 파일에서 URL 중복 금지 (다른 프로젝트 포함)
3. domain 필드는 URL의 호스트와 일치해야 함
4. categories, tags, packages는 존재할 경우 리스트 형식이어야 함
5. category 값은 A/B 또는 A/B/C 형식을 따라야 함
"""

import os
import sys
import logging
import textwrap

# 사용자 정의 모듈 임포트
from token_manager import get_auth_headers_from_env
from fetch_projects import fetch_all_bookmarks
from yaml_validator import validate_bookmarks, load_current_project_bookmarks

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# 환경 변수 상수
ENV_CI_SERVER_URL = 'CI_SERVER_URL'
ENV_BOOKMARK_DATA_GROUP_ID = 'BOOKMARK_DATA_GROUP_ID'
ENV_ENCRYPTED_PAT = 'ENCRYPTED_PAT'
ENV_PAT_ENCRYPTION_KEY = 'PAT_ENCRYPTION_KEY'
ENV_ENCRYPTED_DEPLOY_TOKEN = 'ENCRYPTED_DEPLOY_TOKEN'
ENV_ENCRYPTION_KEY = 'ENCRYPTION_KEY'
ENV_DEPLOY_TOKEN_USERNAME = 'DEPLOY_TOKEN_USERNAME'

def validate_bookmarks_data(current_dir, fetch_others=True):
    """
    북마크 데이터를 검증하는 함수입니다.

    이 함수는 현재 프로젝트의 북마크 데이터를 로드하고,
    필요한 경우 다른 프로젝트에서의 북마크 데이터도 가져와서 통합적으로 검증합니다.
    검증 중 오류가 발생하면 이를 감지하고, 결과에 따라 적절한 상태를 반환합니다.
    이를 통해 프로젝트 간 북마크 데이터의 일관성과 유효성을 유지할 수 있습니다.
    """
    # 현재 프로젝트에서 북마크 로드
    current_bookmarks, has_errors = load_current_project_bookmarks(current_dir)

    if not current_bookmarks and not fetch_others:
        return 1

    all_bookmarks = current_bookmarks

    # 요청된 경우 다른 프로젝트에서 북마크를 가져옴
    if fetch_others:
        gitlab_url = os.environ.get('CI_SERVER_URL')
        group_id = os.environ.get('BOOKMARK_DATA_GROUP_ID')
        current_project_id = os.environ.get('CI_PROJECT_ID')

        # 환경 변수 확인 - 기본 인증 변수와 PAT 변수 함께 확인
        has_deploy_token = all([
            os.environ.get('ENCRYPTED_DEPLOY_TOKEN'),
            os.environ.get('ENCRYPTION_KEY'),
            os.environ.get('DEPLOY_TOKEN_USERNAME')
        ])

        has_pat = all([
            os.environ.get('ENCRYPTED_PAT'),
            os.environ.get('PAT_ENCRYPTION_KEY')
        ])

        # GitLab URL과 그룹 ID가 있고, 토큰 정보(PAT 또는 Deploy Token)가 있는지 확인
        if all([gitlab_url, group_id]) and (has_deploy_token or has_pat):
            try:
                # API 호출을 위한 인증 헤더 가져오기 (PAT 우선)
                headers = get_auth_headers_from_env(for_api=True)

                logger.info("그룹 %s 내 다른 프로젝트에서 북마크를 가져오는 중...", group_id)
                other_bookmarks = fetch_all_bookmarks(gitlab_url, headers, group_id, current_project_id)
                logger.info("다른 프로젝트에서 %s개의 북마크를 찾았습니다.", len(other_bookmarks))

                all_bookmarks.extend(other_bookmarks)
            except Exception as e:
                logger.error("다른 프로젝트에서 북마크를 가져오는 중 오류 발생: %s", str(e))
                has_errors = True
        else:
            logger.warning("경고: 다른 프로젝트의 북마크를 가져올 수 없습니다. 필요한 환경 변수가 누락되었습니다.")
            missing_vars = []
            if not gitlab_url:
                missing_vars.append("CI_SERVER_URL")
            if not group_id:
                missing_vars.append("BOOKMARK_DATA_GROUP_ID")
            if not has_deploy_token and not has_pat:
                missing_vars.append("인증 토큰 관련 변수 (ENCRYPTED_PAT/PAT_ENCRYPTION_KEY 또는 ENCRYPTED_DEPLOY_TOKEN/ENCRYPTION_KEY/DEPLOY_TOKEN_USERNAME)")
            logger.warning("누락된 변수: %s", ', '.join(missing_vars))

    # 수집된 모든 북마크 검증
    validation_errors = validate_bookmarks(all_bookmarks)
    has_errors = has_errors or validation_errors

    if has_errors:
        logger.error("검증 실패. 위 오류를 확인하세요.")
        return 1

    logger.info("검증 성공. 총 %s개의 북마크를 찾았습니다.", len(all_bookmarks))
    return 0

def main():
    # CI 환경에서 실행 중인지 확인
    in_ci = 'CI' in os.environ

    # 다른 프로젝트의 데이터를 가져올지 여부 결정
    # CI 환경에서 실행 중이고 필요한 환경 변수가 설정된 경우에만 실행
    has_deploy_token = all([
        os.environ.get('ENCRYPTED_DEPLOY_TOKEN'),
        os.environ.get('ENCRYPTION_KEY'),
        os.environ.get('DEPLOY_TOKEN_USERNAME')
    ])

    has_pat = all([
        os.environ.get('ENCRYPTED_PAT'),
        os.environ.get('PAT_ENCRYPTION_KEY')
    ])

    fetch_others = (in_ci
                    and os.environ.get('CI_SERVER_URL')
                    and os.environ.get('BOOKMARK_DATA_GROUP_ID')
                    and (has_deploy_token or has_pat))

    if fetch_others:
        auth_method = "PAT" if has_pat else "Deploy Token"
        logger.info("CI 환경에서 GitLab API 접근 가능 (%s 사용). 모든 프로젝트의 북마크를 검증합니다.", auth_method)
    else:
        logger.info("단독 모드로 실행됩니다. 로컬 YAML 파일만 검증합니다.")
        if in_ci:
            logger.info(textwrap.dedent(f"""
                프로젝트 간 검증을 활성화하려면 다음 환경 변수를 설정하세요:
                1. 기본 환경 변수:
                  - {ENV_CI_SERVER_URL}
                  - {ENV_BOOKMARK_DATA_GROUP_ID}
                2. 인증 방법 (하나 이상):
                  - PAT 방식: {ENV_ENCRYPTED_PAT}, {ENV_PAT_ENCRYPTION_KEY}
                  - Deploy Token 방식: {ENV_ENCRYPTED_DEPLOY_TOKEN}, {ENV_ENCRYPTION_KEY}, {ENV_DEPLOY_TOKEN_USERNAME}
                """).strip())

    # YAML 파일을 검색할 현재 디렉토리 가져오기
    current_dir = os.environ.get('CI_PROJECT_DIR', '.')

    # 검증 수행
    return validate_bookmarks_data(current_dir, fetch_others)

if __name__ == "__main__":
    sys.exit(main())