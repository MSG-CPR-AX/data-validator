#!/usr/bin/env python3
"""
GitLab 배포 토큰 및 개인 액세스 토큰(PAT)용 토큰 관리자

이 모듈은 대칭 암호화(Fernet)를 사용하여 GitLab 토큰을 암호화 및 복호화하는 함수와
API 인증 헤더를 생성하는 기능을 제공합니다.

사용 예:
    from token_manager import encrypt_token, decrypt_token, get_auth_headers_from_env

    # 토큰 암호화
    encrypted_token, key = encrypt_token("your-token")

    # 토큰 복호화
    token = decrypt_token(encrypted_token, key)

    # API 인증 헤더 가져오기
    headers = get_auth_headers_from_env()
"""

import os
import sys
import base64
from cryptography.fernet import Fernet

def encrypt_token(token, key=None):
    """
    Fernet 대칭 암호화를 사용하여 토큰을 암호화합니다.

    매개변수:
        token (str): 암호화할 토큰
        key (bytes, 선택): 암호화 키. 생략 시 새 키가 생성됩니다.

    반환값:
        tuple: (암호화된 토큰, 암호화 키)
    """
    if key is None:
        key = Fernet.generate_key()
    elif isinstance(key, str):
        # 문자열로 제공된 키는 바이트로 인코딩
        key = key.encode()

    cipher = Fernet(key)
    encrypted_token = cipher.encrypt(token.encode())

    return encrypted_token, key

def decrypt_token(encrypted_token, key):
    """
    암호화된 토큰을 복호화합니다.

    매개변수:
        encrypted_token (bytes 또는 str): 암호화된 토큰
        key (bytes 또는 str): 암호화 키

    반환값:
        str: 복호화된 토큰
    """
    try:
        if isinstance(key, str):
            key = key.encode()

        if isinstance(encrypted_token, str):
            encrypted_token = encrypted_token.encode()

        cipher = Fernet(key)
        decrypted_token = cipher.decrypt(encrypted_token).decode()

        return decrypted_token
    except Exception as e:
        print(f"토큰 복호화 중 오류 발생: {type(e).__name__}", file=sys.stderr)
        print(f"오류 세부 정보: {str(e)}", file=sys.stderr)

        # 암호화 토큰 디버깅 정보 (앞 10자만 표시하여 보안 유지)
        token_prefix = str(encrypted_token)[:10] + "..." if encrypted_token else "None"
        print(f"암호화 토큰 접두사: {token_prefix}", file=sys.stderr)

        # 키 디버깅 정보 (앞 10자만 표시하여 보안 유지)
        key_prefix = str(key)[:10] + "..." if key else "None"
        print(f"키 접두사: {key_prefix}", file=sys.stderr)

        # 복호화 실패 시 ValueError로 래핑하여 던짐
        raise ValueError(f"토큰 복호화 실패: {type(e).__name__} - {str(e)}")

def get_deploy_token_headers(username, token):
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

def get_pat_headers(token):
    """
    개인 액세스 토큰(PAT)을 사용하여 GitLab API 인증 헤더를 생성합니다.

    매개변수:
        token (str): 개인 액세스 토큰

    반환값:
        dict: Private-Token 인증 헤더 딕셔너리
    """
    return {"Private-Token": token}

def get_token_from_env():
    """
    환경 변수에서 배포 토큰을 가져와 복호화합니다.

    필요 환경 변수:
        ENCRYPTED_DEPLOY_TOKEN: 암호화된 배포 토큰
        ENCRYPTION_KEY: 암호화 키
        DEPLOY_TOKEN_USERNAME: 배포 토큰 사용자명

    반환값:
        tuple: (username, token, headers)
    """
    encrypted_token = os.environ.get('ENCRYPTED_DEPLOY_TOKEN')
    encryption_key = os.environ.get('ENCRYPTION_KEY')
    username = os.environ.get('DEPLOY_TOKEN_USERNAME')

    if not all([encrypted_token, encryption_key, username]):
        print("필수 환경 변수 누락: ENCRYPTED_DEPLOY_TOKEN, ENCRYPTION_KEY, DEPLOY_TOKEN_USERNAME", file=sys.stderr)
        raise ValueError(
            "필수 환경 변수 누락: "
            "ENCRYPTED_DEPLOY_TOKEN, ENCRYPTION_KEY, DEPLOY_TOKEN_USERNAME"
        )

    token = decrypt_token(encrypted_token, encryption_key)
    headers = get_deploy_token_headers(username, token)

    return username, token, headers

def get_pat_from_env():
    """
    환경 변수에서 개인 액세스 토큰(PAT)을 가져와 복호화합니다.

    필요 환경 변수:
        ENCRYPTED_PAT: 암호화된 PAT
        PAT_ENCRYPTION_KEY: PAT 암호화 키

    반환값:
        tuple: (token, headers)
    """
    encrypted_pat = os.environ.get('ENCRYPTED_PAT')
    encryption_key = os.environ.get('PAT_ENCRYPTION_KEY')

    if not all([encrypted_pat, encryption_key]):
        print("PAT에 필요한 환경 변수 누락: ENCRYPTED_PAT, PAT_ENCRYPTION_KEY", file=sys.stderr)
        raise ValueError(
            "PAT에 필요한 환경 변수 누락: "
            "ENCRYPTED_PAT, PAT_ENCRYPTION_KEY"
        )

    token = decrypt_token(encrypted_pat, encryption_key)
    headers = get_pat_headers(token)

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
    if for_api:
        try:
            # API 작업 시 PAT 우선 시도
            _, headers = get_pat_from_env()
            return headers
        except ValueError:
            # PAT가 없으면 배포 토큰으로 대체
            print("⚠️  PAT이 설정되지 않아 API 작업에 배포 토큰을 사용합니다.")
            _, _, headers = get_token_from_env()
            return headers
    else:
        # 일반 작업은 배포 토큰 사용
        _, _, headers = get_token_from_env()
        return headers