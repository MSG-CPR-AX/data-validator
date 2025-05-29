#!/usr/bin/env python3
"""
북마크 YAML 유효성 검사기

이 모듈은 북마크 YAML 데이터가 요구되는 형식과 제약 조건을 만족하는지 검사하는 클래스를 제공합니다.

검사 규칙:
1. 필수 필드: url, name, domain, category, packages
2. 모든 파일(다른 프로젝트 포함)에서 URL 중복 금지
3. domain 필드는 URL의 호스트와 일치해야 함
4. packages는 key와 children을 가진 객체의 리스트여야 함 (빈 리스트 허용)
5. meta 필드는 선택적이며 추가 속성을 허용함

사용 예:
    from app.validators.bookmark_validator import SchemaLoader, BookmarkValidator

    # 스키마 로더 생성
    schema_loader = SchemaLoader()
    schema = schema_loader.load_schema()

    # 북마크 검증기 생성
    validator = BookmarkValidator(schema)

    # 북마크 리스트 유효성 검사
    has_errors = validator.validate_bookmarks(bookmarks)

    # 현재 프로젝트의 북마크 로드 및 검증
    bookmarks, has_errors = validator.load_current_project_bookmarks(current_dir)
"""
import os
import logging

from app.gitlab_utils.gitlab_auth import GitLabAuthenticator
from app.gitlab_utils.gitlab_fetcher import GitLabBookmarkFetcher
from app.schemas.data_schema import BookmarkJsonSchema

from app.gitlab_utils.gitlab_constants import GitLabEnvVariables

# 로깅 설정
logger = logging.getLogger(__name__)


class BookmarkValidator:
    """
    북마크 YAML 데이터의 유효성을 검사하는 클래스
    """

    def __init__(self, schema=None, authenticator=None):
        """
        BookmarkValidator 초기화

        매개변수:
            schema (dict, 선택): 사용할 JSON 스키마. 없으면 SchemaLoader로 로드
        """
        if schema is None:
            self.schema = BookmarkJsonSchema().schema
        else:
            self.schema = schema

        if authenticator is None:
            self.authenticator = GitLabAuthenticator()
        else:
            self.authenticator = authenticator

        self.fetcher = GitLabBookmarkFetcher(self.authenticator)

    def validate_bookmarks_data(self):
        """
        북마크 데이터를 검증하는 메서드입니다.

        이 메서드는 현재 프로젝트의 북마크 데이터를 로드하고,
        필요한 경우 다른 프로젝트에서의 북마크 데이터도 가져와서 통합적으로 검증합니다.
        검증 중 오류가 발생하면 이를 감지하고, 결과에 따라 적절한 상태를 반환합니다.
        이를 통해 프로젝트 간 북마크 데이터의 일관성과 유효성을 유지할 수 있습니다.

        매개변수:
            current_dir (str): 현재 프로젝트 디렉토리
            fetch_others (bool): 다른 프로젝트의 북마크도 가져올지 여부

        반환값:
            int: 성공 시 0, 실패 시 1
        """
        # 요청된 경우 다른 프로젝트에서 북마크를 가져옴
        gitlab_url = os.environ.get(GitLabEnvVariables.CI_SERVER_URL)
        group_id = os.environ.get(GitLabEnvVariables.BOOKMARK_DATA_GROUP_ID)

        # 환경 변수 확인 - 기본 인증 변수와 PAT 변수 함께 확인
        has_deploy_token = self.authenticator.has_deploy_token()
        has_pat = self.authenticator.has_pat()

        all_bookmarks = []
        # GitLab URL과 그룹 ID가 있고, 토큰 정보(PAT 또는 Deploy Token)가 있는지 확인
        if all([gitlab_url, group_id]) and (has_deploy_token or has_pat):
            try:
                logger.info("그룹 %s 내 다른 프로젝트에서 북마크를 가져오는 중...", group_id)
                all_bookmarks = self.fetcher.fetch_all_bookmarks(group_id)
                logger.info("다른 프로젝트에서 %s개의 북마크를 찾았습니다.", len(all_bookmarks))
            except Exception as e:
                logger.error("다른 프로젝트에서 북마크를 가져오는 중 오류 발생: %s", str(e))
                has_errors = True
        else:
            logger.warning("경고: 다른 프로젝트의 북마크를 가져올 수 없습니다. 필요한 환경 변수가 누락되었습니다.")
            missing_vars = []
            if not gitlab_url:
                missing_vars.append(GitLabEnvVariables.CI_SERVER_URL)
            if not group_id:
                missing_vars.append(GitLabEnvVariables.BOOKMARK_DATA_GROUP_ID)
            if not has_deploy_token and not has_pat:
                missing_vars.append("인증 토큰 관련 변수 (ENCRYPTED_PAT/PAT_ENCRYPTION_KEY 또는 ENCRYPTED_DEPLOY_TOKEN/ENCRYPTION_KEY/DEPLOY_TOKEN_USERNAME)")
            logger.warning("누락된 변수: %s", ', '.join(missing_vars))
            has_errors = True

        # 수집된 모든 북마크 검증
        validation_errors = self.schema.validate_bookmarks(all_bookmarks)

        if has_errors or validation_errors:
            logger.error("검증 실패. 위 오류를 확인하세요.")
            return 1

        logger.info("검증 성공. 총 %s개의 북마크를 찾았습니다.", len(all_bookmarks))
        return 0

