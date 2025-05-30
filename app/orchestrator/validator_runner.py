#!/usr/bin/env python3
"""
북마크 검증 오케스트레이터

이 모듈은 로컬 및 원격 북마크 데이터를 수집하고 검증하는 오케스트레이션 로직을 제공합니다.

주요 기능:
1. 현재 프로젝트의 북마크 데이터 로드
2. 다른 프로젝트에서 북마크 데이터 가져오기
3. 모든 북마크 데이터의 통합 검증 수행

사용 예:
    from app.orchestrator.validator_runner import BookmarkValidationOrchestrator

    # 오케스트레이터 생성
    orchestrator = BookmarkValidationOrchestrator()

    # 북마크 데이터 검증 실행
    exit_code = orchestrator.validate_bookmarks_data(current_dir, fetch_others=True)
"""

import os
import logging
import textwrap

from app.schema_rules.data_schema import BookmarkJsonSchema
# 사용자 정의 모듈 임포트
from app.validators.bookmark_validator import BookmarkValidator
# 환경 변수 상수 임포트
from app.gitlab_utils.gitlab_constants import GitLabEnvVariables
from app.gitlab_utils.gitlab_auth import GitLabAuthenticator

# 로깅 설정
logger = logging.getLogger(__name__)

class DataValidationOrchestrator:
    """
    북마크 데이터 검증을 오케스트레이션하는 클래스
    """

    def __init__(self):
        """
        BookmarkValidationOrchestrator 초기화
        """
        self.authenticator = GitLabAuthenticator()
        self.validator = BookmarkValidator(BookmarkJsonSchema(), self.authenticator)

    def run(self):
        """
        북마크 검증을 실행하는 메인 메서드

        반환값:
            int: 성공 시 0, 실패 시 1
        """
        # 환경 확인
        in_ci, fetch_others, auth_method = self.check_environment()
        is_verified = self.verify_environment_status(in_ci, fetch_others, auth_method)
        if not is_verified:
            return 0

        # 검증 수행
        return self.validator.validate_bookmarks_data()

    def check_environment(self):
        """
        CI 환경 및 필요한 환경 변수를 확인합니다.

        반환값:
            tuple: (in_ci, fetch_others, auth_method)
        """
        # CI 환경에서 실행 중인지 확인
        in_ci = 'CI' in os.environ

        # 다른 프로젝트의 데이터를 가져올지 여부 결정
        # CI 환경에서 실행 중이고 필요한 환경 변수가 설정된 경우에만 실행
        has_pat = self.authenticator.has_pat()
        has_deploy_token = self.authenticator.has_deploy_token()

        fetch_others = (in_ci
                        and os.environ.get(GitLabEnvVariables.CI_SERVER_URL)
                        and os.environ.get(GitLabEnvVariables.BOOKMARK_DATA_GROUP_ID)
                        and (has_deploy_token or has_pat))

        auth_method = "PAT" if has_pat else "Deploy Token" if has_deploy_token else None

        return in_ci, fetch_others, auth_method

    @staticmethod
    def verify_environment_status(in_ci, fetch_others, auth_method):
        """
        환경 상태를 로그에 기록합니다.

        매개변수:
            in_ci (bool): CI 환경에서 실행 중인지 여부
            fetch_others (bool): 다른 프로젝트의 북마크를 가져올지 여부
            auth_method (str): 인증 방법
        """
        if fetch_others:
            logger.info("CI 환경에서 GitLab API 접근 가능 (%s 사용). 모든 프로젝트의 북마크를 검증합니다.", auth_method)
            return True
        else:
            logger.error("CI 환경에서 GitLab API 접근 불가. 데이터 변경을 차단합니다.")
            if in_ci:
                logger.error(textwrap.dedent(f"""
                    프로젝트 간 검증을 활성화하려면 다음 환경 변수를 설정하세요:
                    1. 기본 환경 변수:
                      - {GitLabEnvVariables.CI_SERVER_URL}
                      - {GitLabEnvVariables.BOOKMARK_DATA_GROUP_ID}
                    2. 인증 방법 (하나 이상):
                      - PAT 방식: {GitLabEnvVariables.ENCRYPTED_PAT}, {GitLabEnvVariables.PAT_ENCRYPTION_KEY}
                      - Deploy Token 방식: {GitLabEnvVariables.ENCRYPTED_DEPLOY_TOKEN}, {GitLabEnvVariables.ENCRYPTION_KEY}, {GitLabEnvVariables.DEPLOY_TOKEN_USERNAME}
                    """).strip())
            return False
