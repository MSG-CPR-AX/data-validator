
#!/usr/bin/env python3
"""
GitLab 프로젝트 및 파일 수집기

이 모듈은 적절한 인증을 통해 GitLab API를 사용하여
그룹 내의 프로젝트 목록과 각 프로젝트의 YAML 파일을 수집하는 기능을 제공합니다.

사용 예:
    from fetch_projects import fetch_group_projects, fetch_project_yaml_files

    # 인증 헤더 가져오기
    from token_manager import get_auth_headers_from_env
    headers = get_auth_headers_from_env(for_api=True)

    # 그룹 내 프로젝트 가져오기
    projects = fetch_group_projects(gitlab_url, headers, group_id)

    # 프로젝트 내 YAML 파일 가져오기
    yaml_files = fetch_project_yaml_files(gitlab_url, headers, project_id)
"""
import logging
import yaml
import requests
from urllib.parse import quote
from token_manager import get_auth_headers_from_env

# 로깅 설정
logger = logging.getLogger(__name__)

def fetch_group_projects(gitlab_url, headers, group_id, exclude_project_id=None):
    """
    GitLab API를 사용하여 그룹 내 모든 프로젝트를 조회합니다.

    매개변수:
        gitlab_url (str): GitLab 인스턴스 URL
        headers (dict): 인증 헤더
        group_id (str): 조회 대상 그룹 ID
        exclude_project_id (str, 선택): 제외할 프로젝트 ID

    반환값:
        list: 프로젝트 정보 딕셔너리 목록
    """
    api_url = f"{gitlab_url}/api/v4"

    # API 작업을 위해 PAT 사용
    api_headers = get_auth_headers_from_env(for_api=True)

    # 그룹 내 모든 프로젝트 조회
    projects_response = requests.get(
        f"{api_url}/groups/{group_id}/projects?include_subgroups=true&per_page=100",
        headers=api_headers
    )

    if projects_response.status_code != 200:
        logger.error("❌ 프로젝트 목록 조회 실패: %s", projects_response.status_code)
        logger.error("응답 내용: %s", projects_response.text)
        return []

    projects = projects_response.json()

    # 현재 프로젝트 및 data-validator 프로젝트 제외
    other_projects = [
        project for project in projects
        if (exclude_project_id is None or str(project['id']) != exclude_project_id) and
           not project['path_with_namespace'].endswith('data-validator')
    ]

    return other_projects

def fetch_project_yaml_files(gitlab_url, headers, project_id, project_path=None):
    """
    GitLab 프로젝트에서 모든 YAML 파일을 가져옵니다.

    매개변수:
        gitlab_url (str): GitLab 인스턴스 URL
        headers (dict): 인증 헤더
        project_id (int): 대상 프로젝트 ID
        project_path (str, 선택): 프로젝트 경로 (에러 메시지용)

    반환값:
        list: 추출된 북마크 딕셔너리 목록
    """
    api_url = f"{gitlab_url}/api/v4"
    project_path = project_path or f"Project ID: {project_id}"
    bookmarks = []

    # API 작업을 위해 PAT 사용
    api_headers = get_auth_headers_from_env(for_api=True)

    # 저장소 내 파일 목록 조회
    tree_response = requests.get(
        f"{api_url}/projects/{project_id}/repository/tree?recursive=true&per_page=100",
        headers=api_headers
    )

    if tree_response.status_code != 200:
        logger.error("❌ 프로젝트 %s의 파일 목록 조회 실패: %s", project_path, tree_response.status_code)
        logger.error("응답 내용: %s", tree_response.text)
        return []

    files = tree_response.json()
    yaml_files = [file for file in files if file['path'].endswith(('.yml', '.yaml'))]

    for yaml_file in yaml_files:
        file_path = yaml_file['path']

        # GitLab CI 설정 관련 YAML 파일은 제외
        if file_path.startswith('.gitlab-ci') or '/gitlab-ci' in file_path:
            continue

        # 파일 내용 조회
        encoded_file_path = quote(file_path, safe='')
        file_response = requests.get(
            f"{api_url}/projects/{project_id}/repository/files/{encoded_file_path}/raw?ref=main",
            headers=api_headers
        )

        if file_response.status_code != 200:
            logger.warning("⚠️  파일 %s 내용 조회 실패: %s", file_path, file_response.status_code)
            continue

        try:
            content = file_response.text
            yaml_content = yaml.safe_load(content)

            if not yaml_content or not isinstance(yaml_content, list):
                continue

            for item in yaml_content:
                if isinstance(item, dict) and 'url' in item:
                    # 에러 메시지에 사용할 원본 정보 추가
                    item['_source_project'] = project_path
                    item['_source_file'] = file_path
                    bookmarks.append(item)
        except yaml.YAMLError as e:
            logger.warning("⚠️  YAML 파싱 오류 - %s/%s: %s", project_path, file_path, str(e))

    return bookmarks

def fetch_all_bookmarks(gitlab_url, headers, group_id, exclude_project_id=None):
    """
    그룹 내 모든 프로젝트에서 북마크 데이터를 수집합니다.

    매개변수:
        gitlab_url (str): GitLab 인스턴스 URL
        headers (dict): 인증 헤더
        group_id (str): 그룹 ID
        exclude_project_id (str, 선택): 제외할 프로젝트 ID

    반환값:
        list: 모든 프로젝트에서 수집한 북마크 리스트
    """
    all_bookmarks = []

    # 그룹 내 프로젝트 목록 조회
    projects = fetch_group_projects(gitlab_url, headers, group_id, exclude_project_id)
    logger.info("📦 그룹 %s 내 프로젝트 수: %s", group_id, len(projects))

    # 각 프로젝트에서 YAML 파일 수집
    for project in projects:
        project_id = project['id']
        project_path = project['path_with_namespace']
        logger.info("📁 프로젝트에서 YAML 수집 중: %s", project_path)

        project_bookmarks = fetch_project_yaml_files(gitlab_url, headers, project_id, project_path)
        logger.info("✅ %s 에서 %s개의 북마크 발견", project_path, len(project_bookmarks))

        all_bookmarks.extend(project_bookmarks)

    return all_bookmarks