#!/usr/bin/env python3
import logging
import yaml
from app.gitlab_utils.gitlab_auth import GitLabAuthenticator
from app.gitlab_utils.gitlab_client import PatApiClient

# 로깅 설정
logger = logging.getLogger(__name__)


class GitLabBookmarkFetcher:
    """
    GitLab 프로젝트 및 그룹에서 북마크 데이터(YAML 파일 기반)를 수집, 처리 및 반환하는 클래스.

    이 클래스는 GitLab API를 통해 그룹 내 프로젝트들을 조회하고 각 프로젝트의 데이터를 파싱하여 북마크 데이터를 추출합니다.
    GitLab 인증 객체를 사용하여 API 요청을 처리하며, 다양한 형식의 에러를 관리하고 로그를 통해 문제를 보고합니다.
    """
    def __init__(self, authenticator=None):
        """
        GitLabBookmarkFetcher 초기화

        매개변수:
            authenticator (GitLabAuthenticator, 선택): GitLab 인증 객체
        """
        if authenticator is None:
            authenticator = GitLabAuthenticator()
        self.client = PatApiClient(authenticator)

    def fetch_group_projects(self, group_id):
        """
        GitLab API를 사용하여 그룹 내 모든 프로젝트를 조회합니다.

        매개변수:
            group_id (str): 조회 대상 그룹 ID
            exclude_project_id (str, 선택): 제외할 프로젝트 ID

        반환값:
            list: 프로젝트 정보 딕셔너리 목록
        """
        return self.client.fetch_group_projects(group_id)

    def fetch_project_bookmarks(self, project_id, project_path=None):
        """
        GitLab 프로젝트에서 모든 YAML 파일을 가져옵니다.

        매개변수:
            project_id (int): 대상 프로젝트 ID
            project_path (str, 선택): 프로젝트 경로 (에러 메시지용)

        반환값:
            list: 추출된 북마크 딕셔너리 목록
        """
        yaml_files = self.client.fetch_project_yaml_files_content(project_id, project_path)
        bookmarks = []

        for yaml_file in yaml_files:
            try:
                content = yaml_file['content']
                file_path = yaml_file['path']
                project_path = yaml_file['project_path_for_log']

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
                logger.warning("⚠️  YAML 파싱 오류 - %s/%s: %s", 
                               yaml_file.get('project_path_for_log', 'unknown'), 
                               yaml_file.get('path', 'unknown'), 
                               str(e))
            except Exception as e:
                logger.warning("⚠️  파일 처리 중 오류 발생: %s", str(e))

        return bookmarks

    def fetch_all_bookmarks(self, group_id):
        """
        그룹 내 모든 프로젝트에서 북마크 데이터를 수집합니다.

        매개변수:
            group_id (str): 그룹 ID
            exclude_project_id (str, 선택): 제외할 프로젝트 ID

        반환값:
            list: 모든 프로젝트에서 수집한 북마크 리스트
        """
        # PatApiClient의 fetch_all_bookmarks_from_group 메서드 사용
        all_yaml_files = self.client.fetch_all_yaml_files_from_group(group_id)
        all_bookmarks = []

        # YAML 파일 내용 파싱
        for file_data in all_yaml_files:
            try:
                content = file_data['content']
                file_path = file_data['path']
                project_path = file_data['project_path_for_log']

                yaml_content = yaml.safe_load(content)

                if not yaml_content or not isinstance(yaml_content, list):
                    continue

                for item in yaml_content:
                    if isinstance(item, dict) and 'url' in item:
                        # 에러 메시지에 사용할 원본 정보 추가
                        item['_source_project'] = project_path
                        item['_source_file'] = file_path
                        all_bookmarks.append(item)
            except yaml.YAMLError as e:
                logger.warning("⚠️  YAML 파싱 오류 - %s/%s: %s", 
                               file_data.get('project_path_for_log', 'unknown'), 
                               file_data.get('path', 'unknown'), 
                               str(e))
            except Exception as e:
                logger.warning("⚠️  파일 처리 중 오류 발생: %s", str(e))

        logger.info("📦 그룹 %s 내 총 %s개의 북마크 발견", group_id, len(all_bookmarks))
        return all_bookmarks
