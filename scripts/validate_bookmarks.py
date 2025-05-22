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
import yaml

# 사용자 정의 모듈 임포트
from token_manager import get_token_from_env
from fetch_projects import fetch_all_bookmarks
from yaml_validator import validate_bookmarks, load_current_project_bookmarks

# 이 함수는 현재 yaml_validator.py에서 임포트됩니다
# def find_yaml_files(base_dir):
#     """지정한 디렉토리 내의 모든 북마크 YAML 파일을 찾습니다."""
#     ...

# 이 함수는 현재 fetch_projects.py의 fetch_all_bookmarks로 대체되었습니다
# def fetch_other_projects_yaml(gitlab_url, token, group_id, exclude_project_id=None):
#     """GitLab API를 사용하여 bookmark-data 그룹 내 다른 프로젝트에서 YAML 파일을 가져옵니다."""
#     ...

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

        # 배포 토큰 관련 환경 변수가 설정되어 있는지 확인
        if all([
            os.environ.get('ENCRYPTED_DEPLOY_TOKEN'),
            os.environ.get('ENCRYPTION_KEY'),
            os.environ.get('DEPLOY_TOKEN_USERNAME'),
            gitlab_url,
            group_id
        ]):
            try:
                # 배포 토큰을 사용하여 인증 헤더 생성
                _, _, headers = get_token_from_env()

                print(f"그룹 {group_id} 내 다른 프로젝트에서 북마크를 가져오는 중...", file=sys.stderr)
                other_bookmarks = fetch_all_bookmarks(gitlab_url, headers, group_id, current_project_id)
                print(f"다른 프로젝트에서 {len(other_bookmarks)}개의 북마크를 찾았습니다.", file=sys.stderr)

                all_bookmarks.extend(other_bookmarks)
            except Exception as e:
                print(f"다른 프로젝트에서 북마크를 가져오는 중 오류 발생: {str(e)}", file=sys.stderr)
                has_errors = True
        else:
            print("경고: 다른 프로젝트의 북마크를 가져올 수 없습니다. 필요한 환경 변수가 누락되었습니다.", file=sys.stderr)
            print("필요한 변수: ENCRYPTED_DEPLOY_TOKEN, ENCRYPTION_KEY, DEPLOY_TOKEN_USERNAME, CI_SERVER_URL, BOOKMARK_DATA_GROUP_ID", file=sys.stderr)

    # 수집된 모든 북마크 검증
    validation_errors = validate_bookmarks(all_bookmarks)
    has_errors = has_errors or validation_errors

    if has_errors:
        print("검증 실패. 위 오류를 확인하세요.", file=sys.stderr)
        return 1

    print(f"검증 성공. 총 {len(all_bookmarks)}개의 북마크를 찾았습니다.")
    return 0

def main():
    # CI 환경에서 실행 중인지 확인
    in_ci = 'CI' in os.environ

    # 다른 프로젝트의 데이터를 가져올지 여부 결정
    # CI 환경에서 실행 중이고 필요한 환경 변수가 설정된 경우에만 실행
    fetch_others = in_ci and all([
        os.environ.get('CI_SERVER_URL'),
        os.environ.get('BOOKMARK_DATA_GROUP_ID'),
        os.environ.get('ENCRYPTED_DEPLOY_TOKEN'),
        os.environ.get('ENCRYPTION_KEY'),
        os.environ.get('DEPLOY_TOKEN_USERNAME')
    ])

    if fetch_others:
        print("CI 환경에서 GitLab API 접근 가능. 모든 프로젝트의 북마크를 검증합니다.", file=sys.stderr)
    else:
        print("단독 모드로 실행됩니다. 로컬 YAML 파일만 검증합니다.", file=sys.stderr)
        if in_ci:
            print("프로젝트 간 검증을 활성화하려면 다음 환경 변수를 설정하세요: CI_SERVER_URL, BOOKMARK_DATA_GROUP_ID, ENCRYPTED_DEPLOY_TOKEN, ENCRYPTION_KEY, DEPLOY_TOKEN_USERNAME", file=sys.stderr)

    # YAML 파일을 검색할 현재 디렉토리 가져오기
    current_dir = os.environ.get('CI_PROJECT_DIR', '.')

    # 검증 수행
    return validate_bookmarks_data(current_dir, fetch_others)

if __name__ == "__main__":
    sys.exit(main())
