# gitlab_utils/constants.py

class GitLabApiUrls:
    BASE_API_V4_PATH = "/api/v4"
    # 예: GROUP_PROJECTS_ENDPOINT = "/groups/{group_id}/projects"
    # 필요한 다른 API 엔드포인트 상수들 추가

class GitLabEnvVariables:
    CI_SERVER_URL = 'CI_SERVER_URL'
    CI_PROJECT_DIR = 'CI_PROJECT_DIR'
    BOOKMARK_DATA_GROUP_ID = 'BOOKMARK_DATA_GROUP_ID'

    ENCRYPTED_PAT = 'ENCRYPTED_PAT'
    PAT_ENCRYPTION_KEY = 'PAT_ENCRYPTION_KEY'

    ENCRYPTED_DEPLOY_TOKEN = 'ENCRYPTED_DEPLOY_TOKEN'
    ENCRYPTION_KEY = 'ENCRYPTION_KEY'
    DEPLOY_TOKEN_USERNAME = 'DEPLOY_TOKEN_USERNAME'
    # 기타 필요한 환경 변수명 추가

class HttpHeaders:
    PRIVATE_TOKEN_HEADER = "Private-Token"
    AUTHORIZATION_HEADER = "Authorization"
    # 기타 필요한 HTTP 헤더 관련 상수

class ApiConstants:
    PER_PAGE_DEFAULT = 100
    # 기타 API 관련 상수