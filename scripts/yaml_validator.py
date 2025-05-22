#!/usr/bin/env python3
"""
YAML 북마크 유효성 검사기

이 모듈은 북마크 YAML 데이터가 요구되는 형식과 제약 조건을 만족하는지 검사하는 기능을 제공합니다.

검사 규칙:
1. 필수 필드: url, name, category, domain
2. 모든 파일(다른 프로젝트 포함)에서 URL 중복 금지
3. domain 필드는 URL의 호스트와 일치해야 함
4. categories, tags, packages 필드는 존재할 경우 리스트여야 함
5. category 값은 A/B 또는 A/B/C 형식을 따라야 함

사용 예:
    from yaml_validator import validate_bookmarks

    # 북마크 리스트 유효성 검사
    has_errors = validate_bookmarks(bookmarks)
"""

import re
import sys
from urllib.parse import urlparse

def validate_bookmarks(bookmarks):
    """
    북마크 딕셔너리 리스트가 형식 및 제약 조건을 만족하는지 검사합니다.

    매개변수:
        bookmarks (list): 유효성 검사를 수행할 북마크 딕셔너리 리스트

    반환값:
        bool: 오류가 발견되면 True, 그렇지 않으면 False
    """
    has_errors = False
    all_urls = set()

    # category는 A/B 또는 A/B/C 형식만 허용
    category_pattern = re.compile(r'^[^/]+/[^/]+(/[^/]+)?$')

    for bookmark in bookmarks:
        source_file = bookmark.get('_source_file', 'unknown')
        source_project = bookmark.get('_source_project', 'unknown')
        index = bookmark.get('_index', 0)

        # 오류 메시지 출력용 위치 문자열 생성
        if source_project == 'current':
            location = f"{source_file}, 항목 {index}"
        else:
            location = f"{source_project}/{source_file}"

        # 메타데이터 제거
        bookmark_copy = bookmark.copy()
        for meta_field in ['_source_file', '_source_project', '_index']:
            if meta_field in bookmark_copy:
                del bookmark_copy[meta_field]

        # 필수 필드 존재 여부 검사
        required_fields = ['url', 'name', 'category', 'domain']
        for field in required_fields:
            if field not in bookmark_copy:
                print(f"❌ {location} - 필수 필드 '{field}' 누락", file=sys.stderr)
                has_errors = True

        # 필수 필드 중 하나라도 없으면 추가 검사 생략
        if not all(field in bookmark_copy for field in required_fields):
            continue

        # URL 중복 검사
        url = bookmark_copy['url']
        if url in all_urls:
            print(f"❌ {location} - 중복된 URL '{url}'", file=sys.stderr)
            has_errors = True
        else:
            all_urls.add(url)

        # domain 필드가 URL 호스트와 일치하는지 검사
        try:
            parsed_url = urlparse(url)
            if parsed_url.netloc != bookmark_copy['domain']:
                print(f"❌ {location} - 도메인 '{bookmark_copy['domain']}'가 URL 호스트 '{parsed_url.netloc}'와 일치하지 않음", file=sys.stderr)
                has_errors = True
        except Exception as e:
            print(f"❌ {location} - 잘못된 URL '{url}': {str(e)}", file=sys.stderr)
            has_errors = True

        # category 형식 검사
        if not category_pattern.match(bookmark_copy['category']):
            print(f"❌ {location} - category '{bookmark_copy['category']}'는 'A/B' 또는 'A/B/C' 형식을 따라야 합니다.", file=sys.stderr)
            has_errors = True

        # 리스트 필드 검사
        list_fields = ['tags', 'packages']
        for field in list_fields:
            if field in bookmark_copy and not isinstance(bookmark_copy[field], list):
                print(f"❌ {location} - 필드 '{field}'는 리스트여야 합니다.", file=sys.stderr)
                has_errors = True

    return has_errors

def find_yaml_files(base_dir):
    """
    지정한 디렉토리 아래의 모든 YAML 북마크 파일을 찾습니다.

    매개변수:
        base_dir (str): 탐색할 루트 디렉토리

    반환값:
        list: YAML 파일 경로 리스트
    """
    import os
    yaml_files = []

    if not os.path.exists(base_dir):
        print(f"⚠️  경고: 디렉토리 {base_dir} 가 존재하지 않습니다.", file=sys.stderr)
        return yaml_files

    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(('.yml', '.yaml')):
                if '.git' in root:
                    continue
                yaml_files.append(os.path.join(root, file))

    return yaml_files

def load_yaml_file(yaml_file):
    """
    단일 YAML 파일을 읽고 파싱합니다.

    매개변수:
        yaml_file (str): YAML 파일 경로

    반환값:
        tuple: (북마크 리스트, 오류 여부)
    """
    import yaml
    bookmarks = []
    has_errors = False

    try:
        with open(yaml_file, 'r') as f:
            try:
                yaml_content = yaml.safe_load(f)
                if not yaml_content:
                    print(f"ℹ️  정보: 빈 파일 또는 북마크가 없는 YAML 파일 생략: {yaml_file}", file=sys.stderr)
                    return bookmarks, has_errors

                if not isinstance(yaml_content, list):
                    print(f"❌ {yaml_file} - 루트 요소는 리스트여야 합니다.", file=sys.stderr)
                    has_errors = True
                    return bookmarks, has_errors

                for i, bookmark in enumerate(yaml_content):
                    if not isinstance(bookmark, dict):
                        print(f"❌ {yaml_file}, 항목 {i+1} - 북마크는 딕셔너리여야 합니다.", file=sys.stderr)
                        has_errors = True
                        continue

                    # 오류 메시지를 위한 메타 정보 추가
                    bookmark['_source_project'] = 'current'
                    bookmark['_source_file'] = yaml_file
                    bookmark['_index'] = i + 1

                    bookmarks.append(bookmark)

            except yaml.YAMLError as e:
                print(f"❌ {yaml_file} 파싱 오류: {str(e)}", file=sys.stderr)
                has_errors = True
    except Exception as e:
        print(f"❌ {yaml_file} 읽기 오류: {str(e)}", file=sys.stderr)
        has_errors = True

    return bookmarks, has_errors

def load_current_project_bookmarks(current_dir):
    """
    현재 프로젝트 디렉토리의 모든 북마크 YAML 파일을 로드합니다.

    매개변수:
        current_dir (str): 현재 프로젝트 디렉토리

    반환값:
        tuple: (북마크 리스트, 오류 여부)
    """
    yaml_files = find_yaml_files(current_dir)
    if not yaml_files:
        print(f"⚠️  {current_dir} 에서 YAML 파일을 찾을 수 없습니다.", file=sys.stderr)
        return [], False

    print(f"🔍 현재 프로젝트에서 {len(yaml_files)}개의 YAML 파일을 찾았습니다.", file=sys.stderr)

    all_bookmarks = []
    has_errors = False

    for yaml_file in yaml_files:
        bookmarks, file_has_errors = load_yaml_file(yaml_file)
        all_bookmarks.extend(bookmarks)
        has_errors = has_errors or file_has_errors

    return all_bookmarks, has_errors
