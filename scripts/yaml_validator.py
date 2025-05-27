#!/usr/bin/env python3
"""
YAML 북마크 유효성 검사기

이 모듈은 북마크 YAML 데이터가 요구되는 형식과 제약 조건을 만족하는지 검사하는 기능을 제공합니다.

검사 규칙:
1. 필수 필드: url, name, domain, category, packages
2. 모든 파일(다른 프로젝트 포함)에서 URL 중복 금지
3. domain 필드는 URL의 호스트와 일치해야 함
4. packages는 key와 children을 가진 객체의 리스트여야 함 (빈 리스트 허용)
5. meta 필드는 선택적이며 추가 속성을 허용함

사용 예:
    from yaml_validator import validate_bookmarks

    # 북마크 리스트 유효성 검사
    has_errors = validate_bookmarks(bookmarks)
"""

import re
import os
import logging
import yaml
import json
import jsonschema
from urllib.parse import urlparse
from pathlib import Path

# 로깅 설정
logger = logging.getLogger(__name__)

def load_schema():
    """
    JSON Schema를 로드합니다.

    반환값:
        dict: 로드된 JSON Schema
    """
    # 먼저 현재 디렉토리에서 스키마 파일 찾기
    schema_paths = [
        # 현재 디렉토리 기준 상대 경로
        "bookmark-schema/bookmark.schema.json",
        # 프로젝트 루트 기준 상대 경로
        "../../../bookmark-schema/bookmark.schema.json",
        # CI 환경에서의 경로
        os.environ.get('CI_PROJECT_DIR', '') + "/bookmark-schema/bookmark.schema.json" if 'CI_PROJECT_DIR' in os.environ else None
    ]

    # None 값 제거
    schema_paths = [p for p in schema_paths if p]

    for schema_path in schema_paths:
        if os.path.exists(schema_path):
            try:
                with open(schema_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error("❌ 스키마 파일 '%s' 로드 오류: %s", schema_path, str(e))
                break

    # 스키마 파일을 찾지 못한 경우 기본 스키마 반환
    logger.warning("⚠️ 스키마 파일을 찾을 수 없어 기본 스키마를 사용합니다.")
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "array",
        "items": {
            "type": "object",
            "required": ["name", "url", "domain", "category", "packages"],
            "properties": {
                "name": {"type": "string"},
                "url": {"type": "string", "format": "uri"},
                "domain": {"type": "string"},
                "category": {"type": "string"},
                "packages": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/packageNode"},
                    "default": []
                },
                "meta": {
                    "type": "object",
                    "additionalProperties": True
                }
            },
            "additionalProperties": False
        },
        "definitions": {
            "packageNode": {
                "type": "object",
                "required": ["key", "children"],
                "properties": {
                    "key": {"type": "string"},
                    "children": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/packageNode"}
                    }
                },
                "additionalProperties": False
            }
        }
    }

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

    # JSON Schema 로드
    schema = load_schema()

    # 북마크 메타데이터 제거 및 URL 중복 검사
    clean_bookmarks = []
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

        # URL 중복 검사
        if 'url' in bookmark_copy:
            url = bookmark_copy['url']
            if url in all_urls:
                logger.error("❌ %s - 중복된 URL '%s'", location, url)
                has_errors = True
            else:
                all_urls.add(url)

        # domain 필드가 URL 호스트와 일치하는지 검사
        if 'url' in bookmark_copy and 'domain' in bookmark_copy:
            try:
                parsed_url = urlparse(bookmark_copy['url'])
                if parsed_url.netloc != bookmark_copy['domain']:
                    logger.error("❌ %s - 도메인 '%s'가 URL 호스트 '%s'와 일치하지 않음", 
                                location, bookmark_copy['domain'], parsed_url.netloc)
                    has_errors = True
            except Exception as e:
                logger.error("❌ %s - 잘못된 URL '%s': %s", location, bookmark_copy.get('url', ''), str(e))
                has_errors = True

        # 북마크 객체에 위치 정보 추가 (오류 메시지용)
        bookmark_copy['_location'] = location
        clean_bookmarks.append(bookmark_copy)

    # JSON Schema 검증
    for bookmark in clean_bookmarks:
        location = bookmark.pop('_location', 'unknown')
        try:
            jsonschema.validate(instance=[bookmark], schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            # 검증 오류 메시지 출력
            error_path = '.'.join(str(p) for p in e.path)
            if error_path:
                logger.error("❌ %s - JSON Schema 검증 오류: %s (%s)", location, e.message, error_path)
            else:
                logger.error("❌ %s - JSON Schema 검증 오류: %s", location, e.message)
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
    yaml_files = []

    if not os.path.exists(base_dir):
        logger.warning("⚠️  경고: 디렉토리 %s 가 존재하지 않습니다.", base_dir)
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
    bookmarks = []
    has_errors = False

    try:
        with open(yaml_file, 'r') as f:
            try:
                yaml_content = yaml.safe_load(f)
                if not yaml_content:
                    logger.info("ℹ️  정보: 빈 파일 또는 북마크가 없는 YAML 파일 생략: %s", yaml_file)
                    return bookmarks, has_errors

                if not isinstance(yaml_content, list):
                    logger.error("❌ %s - 루트 요소는 리스트여야 합니다.", yaml_file)
                    has_errors = True
                    return bookmarks, has_errors

                for i, bookmark in enumerate(yaml_content):
                    if not isinstance(bookmark, dict):
                        logger.error("❌ %s, 항목 %s - 북마크는 딕셔너리여야 합니다.", yaml_file, i+1)
                        has_errors = True
                        continue

                    # 오류 메시지를 위한 메타 정보 추가
                    bookmark['_source_project'] = 'current'
                    bookmark['_source_file'] = yaml_file
                    bookmark['_index'] = i + 1

                    bookmarks.append(bookmark)

            except yaml.YAMLError as e:
                logger.error("❌ %s 파싱 오류: %s", yaml_file, str(e))
                has_errors = True
    except Exception as e:
        logger.error("❌ %s 읽기 오류: %s", yaml_file, str(e))
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
        logger.warning("⚠️  %s 에서 YAML 파일을 찾을 수 없습니다.", current_dir)
        return [], False

    logger.info("🔍 현재 프로젝트에서 %s개의 YAML 파일을 찾았습니다.", len(yaml_files))

    all_bookmarks = []
    has_errors = False

    for yaml_file in yaml_files:
        bookmarks, file_has_errors = load_yaml_file(yaml_file)
        all_bookmarks.extend(bookmarks)
        has_errors = has_errors or file_has_errors

    return all_bookmarks, has_errors
