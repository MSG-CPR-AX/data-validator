# gitlab_utils/auth.py
import os
import base64
import logging
from cryptography.fernet import Fernet
from gitlab_constants import GitLabEnvVariables, HttpHeaders # .constants로 상대경로 임포트

logger = logging.getLogger(__name__)

class TokenCipher:
    def __init__(self, key=None):
        processed_key = None
        if key is None:
            processed_key = Fernet.generate_key()
            logger.info("TokenCipher __init__: 새로운 암호화 키가 생성되었습니다.")
        elif isinstance(key, str):
            processed_key = key.encode()
        elif isinstance(key, bytes):
            processed_key = key
        else:
            err_msg = f"키는 bytes, str 또는 None이어야 합니다. 제공된 타입: {type(key).__name__}"
            logger.error(f"TokenCipher __init__: {err_msg}")
            raise TypeError(err_msg)

        self.key = processed_key

        try:
            self.cipher = Fernet(self.key)
        except Exception as e:
            key_prefix_display = str(self.key)[:10] + "..." if self.key is not None else "None"
            logger.error(f"TokenCipher __init__: Fernet 객체 생성 중 오류 발생: {type(e).__name__} - {str(e)}. 키 접두사: {key_prefix_display}")
            raise ValueError(f"TokenCipher __init__: 유효하지 않은 키로 Fernet 객체 생성 실패: {type(e).__name__} - {str(e)}") from e

    def encrypt(self, token_string: str) -> tuple[bytes, bytes]:
        """
        주어진 문자열 토큰을 암호화합니다.

        매개변수:
            token_string (str): 암호화할 토큰 문자열.

        반환값:
            tuple[bytes, bytes]: (암호화된 토큰 바이트, 사용된 암호화 키 바이트).

        예외:
            TypeError: token_string이 문자열이 아닐 경우.
            ValueError: 암호화 실패 시.
        """
        try:
            if not isinstance(token_string, str):
                raise TypeError("토큰은 문자열이어야 합니다")

            encrypted_token = self.cipher.encrypt(token_string.encode())
            return encrypted_token, self.key
        except Exception as e:
            logger.error(f"TokenCipher encrypt: 토큰 암호화 중 오류 발생: {type(e).__name__}")
            logger.error(f"TokenCipher encrypt: 오류 세부 정보: {str(e)}")

            token_prefix = token_string[:5] + "..." if token_string else "None"
            logger.error(f"TokenCipher encrypt: 토큰 접두사: {token_prefix}")

            key_prefix_display = str(self.key)[:10] + "..." if self.key else "None"
            logger.error(f"TokenCipher encrypt: 사용된 키 접두사: {key_prefix_display}")
            raise ValueError(f"TokenCipher encrypt: 토큰 암호화 실패: {type(e).__name__} - {str(e)}") from e

    def decrypt(self, encrypted_token) -> str:
        """
        암호화된 토큰을 복호화합니다.

        매개변수:
            encrypted_token (bytes 또는 str): 암호화된 토큰.

        반환값:
            str: 복호화된 토큰 문자열.

        예외:
            TypeError: encrypted_token이 바이트 또는 문자열이 아닐 경우.
            ValueError: 복호화 실패 시.
        """
        try:
            encrypted_token_bytes: bytes
            if isinstance(encrypted_token, str):
                encrypted_token_bytes = encrypted_token.encode()
            elif isinstance(encrypted_token, bytes):
                encrypted_token_bytes = encrypted_token
            else:
                raise TypeError(f"암호화된 토큰은 바이트 또는 문자열이어야 합니다. 제공된 타입: {type(encrypted_token).__name__}")

            decrypted_token = self.cipher.decrypt(encrypted_token_bytes).decode()
            return decrypted_token
        except Exception as e:
            logger.error(f"TokenCipher decrypt: 토큰 복호화 중 오류 발생: {type(e).__name__}")
            logger.error(f"TokenCipher decrypt: 오류 세부 정보: {str(e)}")

            token_prefix = str(encrypted_token)[:10] + "..." if encrypted_token else "None"
            logger.error(f"TokenCipher decrypt: 암호화 토큰 접두사: {token_prefix}")

            key_prefix_display = str(self.key)[:10] + "..." if self.key else "None"
            logger.error(f"TokenCipher decrypt: 사용된 키 접두사: {key_prefix_display}")
            raise ValueError(f"TokenCipher decrypt: 토큰 복호화 실패: {type(e).__name__} - {str(e)}") from e

class GitLabAuthenticator:
    def __init__(self):
        # 환경 변수에서 토큰 및 키 로드
        self.encrypted_pat = os.environ.get(GitLabEnvVariables.ENCRYPTED_PAT)
        self.pat_encryption_key = os.environ.get(GitLabEnvVariables.PAT_ENCRYPTION_KEY)

        self.encrypted_deploy_token = os.environ.get(GitLabEnvVariables.ENCRYPTED_DEPLOY_TOKEN)
        self.deploy_token_encryption_key = os.environ.get(GitLabEnvVariables.ENCRYPTION_KEY)
        self.deploy_token_username = os.environ.get(GitLabEnvVariables.DEPLOY_TOKEN_USERNAME)

    def has_deploy_token(self):
        return all([
            self.encrypted_deploy_token,
            self.deploy_token_encryption_key,
            self.deploy_token_username
        ])

    def has_pat(self):
        has_pat = all([
            self.encrypted_pat,
            self.pat_encryption_key
        ])

    def _get_decrypted_pat(self):
        if not all([self.encrypted_pat, self.pat_encryption_key]):
            logger.error(f"Missing PAT environment variables: {GitLabEnvVariables.ENCRYPTED_PAT}, {GitLabEnvVariables.PAT_ENCRYPTION_KEY}")
            raise ValueError("Missing PAT environment variables")
        cipher = TokenCipher(key=self.pat_encryption_key)
        return cipher.decrypt(self.encrypted_pat)

    def get_pat_headers(self):
        token = self._get_decrypted_pat()
        return {HttpHeaders.PRIVATE_TOKEN_HEADER: token}

    def _get_decrypted_deploy_token(self):
        if not all([self.encrypted_deploy_token, self.deploy_token_encryption_key, self.deploy_token_username]):
            logger.error(f"Missing Deploy Token environment variables: {GitLabEnvVariables.ENCRYPTED_DEPLOY_TOKEN}, {GitLabEnvVariables.ENCRYPTION_KEY}, {GitLabEnvVariables.DEPLOY_TOKEN_USERNAME}")
            raise ValueError("Missing Deploy Token environment variables")
        cipher = TokenCipher(key=self.deploy_token_encryption_key)
        return cipher.decrypt(self.encrypted_deploy_token)

    def get_deploy_token_headers(self):
        token = self._get_decrypted_deploy_token()
        auth_str = f"{self.deploy_token_username}:{token}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        return {HttpHeaders.AUTHORIZATION_HEADER: f"Basic {encoded_auth}"}

    def get_api_auth_headers(self):
        """API 호출 시 PAT 우선 사용, 없으면 배포 토큰 사용"""
        try:
            return self.get_pat_headers()
        except ValueError:
            logger.warning("PAT not configured. Falling back to Deploy Token for API operations.")
            return self.get_deploy_token_headers()

    def get_general_auth_headers(self):
        """일반 작업 시 배포 토큰 사용"""
        return self.get_deploy_token_headers()
