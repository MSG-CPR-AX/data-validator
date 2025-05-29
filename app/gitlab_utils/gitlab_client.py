# gitlab_utils/client.py
import requests
import logging
import os
from urllib.parse import quote
from gitlab_constants import GitLabApiUrls, GitLabEnvVariables, ApiConstants
from gitlab_auth import GitLabAuthenticator # GitLabAuthenticator 임포트

logger = logging.getLogger(__name__)

class BaseGitLabClient:
    def __init__(self, authenticator: GitLabAuthenticator):
        self.gitlab_url = os.environ.get(GitLabEnvVariables.CI_SERVER_URL)
        if not self.gitlab_url:
            raise ValueError(f"{GitLabEnvVariables.CI_SERVER_URL} environment variable not set.")
        self.base_api_url = f"{self.gitlab_url}{GitLabApiUrls.BASE_API_V4_PATH}"
        self.authenticator = authenticator

    def _request(self, method, endpoint, headers, params=None, json_data=None):
        url = f"{self.base_api_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=headers, params=params, json=json_data)
            response.raise_for_status() # HTTP 오류 발생 시 예외 발생
            return response.json() if response.content else None
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {method} {url}: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {method} {url}: {e}")
            raise

class PatApiClient(BaseGitLabClient):
    def __init__(self, authenticator: GitLabAuthenticator):
        super().__init__(authenticator)
        self.headers = self.authenticator.get_api_auth_headers() # PAT 우선 헤더 사용

    def fetch_group_projects(self, group_id):
        # 기존 fetch_group_projects 로직 이전 및 수정
        # 예: endpoint = GitLabApiUrls.GROUP_PROJECTS_ENDPOINT.format(group_id=group_id)
        endpoint = f"/groups/{group_id}/projects"
        params = {"include_subgroups": "true", "per_page": ApiConstants.PER_PAGE_DEFAULT}

        projects = self._request("GET", endpoint, self.headers, params=params)

        if not projects: return []

        return [
            project for project in projects
            if not project['path_with_namespace'].endswith('data-validator')
        ]


    def fetch_project_yaml_files_content(self, project_id, project_path_for_log=None):
        # 기존 fetch_project_yaml_files 로직 이전 및 수정
        # 파일 목록 조회
        tree_endpoint = f"/projects/{project_id}/repository/tree"
        params = {"recursive": "true", "per_page": ApiConstants.PER_PAGE_DEFAULT}
        files = self._request("GET", tree_endpoint, self.headers, params=params)

        if not files: return []

        yaml_files = []
        for file_info in files:
            # files에서 조건에 맞지 않는 데이터가 있는지 검사
            if not (file_info['type'] == 'blob' and file_info['path'].endswith(('.yml', '.yaml'))):
                raise ValueError(f"GitLab 프로젝트({project_id})에 yaml 확장자가 아닌 파일이 존재합니다. file : {file_info}")

            file_path = file_info['path']
            encoded_file_path = quote(file_path, safe='')
            file_content_endpoint = f"/projects/{project_id}/repository/files/{encoded_file_path}/raw"
            # 여기서는 raw content를 가져오므로 _request 대신 requests.get 직접 사용 또는 _request 수정 필요
            try:
                response = requests.get(f"{self.base_api_url}{file_content_endpoint}", headers=self.headers, params={"ref": "main"})
                response.raise_for_status()
                # yaml_files에 파일 경로와 내용을 함께 저장
                yaml_files.append({
                    "path": file_path,
                    "content": response.text,
                    "project_id": project_id,
                    "project_path_for_log": project_path_for_log or f"Project ID: {project_id}"
                })
            except requests.exceptions.HTTPError as e:
                logger.warning(f"Failed to fetch file {file_path} from project {project_id}: {e.response.status_code}")
                raise ValueError(f"Failed to fetch file {file_path} from project {project_id}: {e.response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed for file {file_path} from project {project_id}: {e}")
                raise ValueError(f"Request failed for file {file_path} from project {project_id}: {e}")

        return yaml_files

    def fetch_all_yaml_files_from_group(self, group_id):
        all_yaml_files = [] # YAML 파싱 전의 데이터 (content, 경로 등)
        projects = self.fetch_group_projects(group_id)
        logger.info(f"Found {len(projects)} projects in group {group_id}")

        for project in projects:
            project_id_val = project['id']
            project_path_val = project['path_with_namespace']
            logger.info(f"Fetching YAML files from project: {project_path_val}")

            files_content = self.fetch_project_yaml_files_content(project_id_val, project_path_val)
            all_yaml_files.extend(files_content)
            logger.info(f"Found {len(files_content)} YAML files/contents in {project_path_val}")

        return all_yaml_files # YAML 파싱은 이 데이터를 사용하는 쪽에서 수행

# DeployTokenApiClient는 필요시 유사하게 구현
# class DeployTokenApiClient(BaseGitLabClient):
#     def __init__(self, authenticator: GitLabAuthenticator):
#         super().__init__(authenticator)
#         self.headers = self.authenticator.get_general_auth_headers() # 배포 토큰 헤더 사용
# ... 배포 토큰으로 수행할 작업들 ...