# gitlab_utils/schema.py
import json
import os
import logging
import jsonschema # jsonschema 라이브러리 필요
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class BookmarkJsonSchema:
    def __init__(self, schema_file_paths=None):
        if schema_file_paths is None:
            # 기본 스키마 경로들 (yaml_validator.py의 load_schema 참조)
            self.schema_file_paths = [
                "bookmark-schema/bookmark.schema.json",
                "../../../bookmark-schema/bookmark.schema.json",
                os.environ.get('CI_PROJECT_DIR', '') + "/bookmark-schema/bookmark.schema.json" if 'CI_PROJECT_DIR' in os.environ else None
            ]
            self.schema_file_paths = [p for p in self.schema_file_paths if p] # None 제거
        else:
            self.schema_file_paths = schema_file_paths

        self.schema = self._load_schema()

    def _load_schema(self):
        for schema_path in self.schema_file_paths:
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

    def validate_bookmarks(self, bookmarks):
        """
        북마크 딕셔너리 리스트가 형식 및 제약 조건을 만족하는지 검사합니다.

        매개변수:
            bookmarks (list): 유효성 검사를 수행할 북마크 딕셔너리 리스트

        반환값:
            bool: 오류가 발견되면 True, 그렇지 않으면 False
        """
        has_errors = False
        all_urls = set()

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
                jsonschema.validate(instance=[bookmark], schema=self.schema)
            except jsonschema.exceptions.ValidationError as e:
                # 검증 오류 메시지 출력
                error_path = '.'.join(str(p) for p in e.path)
                if error_path:
                    logger.error("❌ %s - JSON Schema 검증 오류: %s (%s)", location, e.message, error_path)
                else:
                    logger.error("❌ %s - JSON Schema 검증 오류: %s", location, e.message)
                has_errors = True

        return has_errors