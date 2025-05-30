#!/usr/bin/env python3
"""
GitLab 배포 토큰 및 개인 액세스 토큰(PAT)용 토큰 관리자

이 모듈은 app.gitlab_utils.gitlab_auth 모듈의 기능을 사용하여 GitLab 토큰을 관리하고
API 인증 헤더를 생성하는 기능을 제공합니다.

사용 예:
    from app.tokens.token_manager import get_auth_headers_from_env

    # API 인증 헤더 가져오기
    headers = get_auth_headers_from_env()
"""

import logging
import os
import base64
from cryptography.fernet import Fernet
from app.gitlab_utils.gitlab_auth import TokenCipher, GitLabAuthenticator

# 로깅 설정
logger = logging.getLogger(__name__)


class DeployTokenManager:
    """
    배포 토큰 관리 클래스
    """

    def get_headers(self, username, token):
        """
        배포 토큰을 사용하여 GitLab API 인증 헤더를 생성합니다.

        매개변수:
            username (str): 배포 토큰 사용자명
            token (str): 배포 토큰 값

        반환값:
            dict: Basic 인증 헤더 딕셔너리
        """
        auth_str = f"{username}:{token}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        return {"Authorization": f"Basic {encoded_auth}"}

    @staticmethod
    def from_env():
        """
        환경 변수에서 배포 토큰을 가져와 복호화합니다.

        필요 환경 변수:
            ENCRYPTED_DEPLOY_TOKEN: 암호화된 배포 토큰
            ENCRYPTION_KEY: 암호화 키
            DEPLOY_TOKEN_USERNAME: 배포 토큰 사용자명

        반환값:
            tuple: (username, token, headers)
        """
        manager = DeployTokenManager()

        encrypted_token = os.environ.get('ENCRYPTED_DEPLOY_TOKEN')
        encryption_key = os.environ.get('ENCRYPTION_KEY')
        username = os.environ.get('DEPLOY_TOKEN_USERNAME')

        if not all([encrypted_token, encryption_key, username]):
            logger.error("필수 환경 변수 누락: ENCRYPTED_DEPLOY_TOKEN, ENCRYPTION_KEY, DEPLOY_TOKEN_USERNAME")
            raise ValueError(
                "필수 환경 변수 누락: "
                "ENCRYPTED_DEPLOY_TOKEN, ENCRYPTION_KEY, DEPLOY_TOKEN_USERNAME"
            )

        token = TokenCipher(encryption_key).decrypt(encrypted_token)
        headers = manager.get_headers(username, token)

        return username, token, headers


class PATTokenManager:
    """
    개인 액세스 토큰(PAT) 관리 클래스
    """

    def get_headers(self, token):
        """
        개인 액세스 토큰(PAT)을 사용하여 GitLab API 인증 헤더를 생성합니다.

        매개변수:
            token (str): 개인 액세스 토큰

        반환값:
            dict: Private-Token 인증 헤더 딕셔너리
        """
        return {"Private-Token": token}

    @staticmethod
    def from_env():
        """
        환경 변수에서 개인 액세스 토큰(PAT)을 가져와 복호화합니다.

        필요 환경 변수:
            ENCRYPTED_PAT: 암호화된 PAT
            PAT_ENCRYPTION_KEY: PAT 암호화 키

        반환값:
            tuple: (token, headers)
        """
        manager = PATTokenManager()

        encrypted_pat = os.environ.get('ENCRYPTED_PAT')
        encryption_key = os.environ.get('PAT_ENCRYPTION_KEY')

        if not all([encrypted_pat, encryption_key]):
            logger.error("PAT에 필요한 환경 변수 누락: ENCRYPTED_PAT, PAT_ENCRYPTION_KEY")
            raise ValueError(
                "PAT에 필요한 환경 변수 누락: "
                "ENCRYPTED_PAT, PAT_ENCRYPTION_KEY"
            )

        token = TokenCipher(encryption_key).decrypt(encrypted_pat)
        headers = manager.get_headers(token)

        return token, headers


def get_auth_headers_from_env(for_api=False):
    """
    작업 유형에 따라 적절한 인증 헤더를 반환합니다.
    API 호출의 경우 가능한 경우 PAT를 사용하고, 그렇지 않으면 배포 토큰으로 대체합니다.

    매개변수:
        for_api (bool): True이면 API 용도 → PAT 우선 사용

    반환값:
        dict: 인증 헤더
    """
    authenticator = GitLabAuthenticator()

    if for_api:
        # API 작업 시 PAT 우선 사용
        return authenticator.get_api_auth_headers()
    else:
        # 일반 작업은 배포 토큰 사용
        return authenticator.get_general_auth_headers()
