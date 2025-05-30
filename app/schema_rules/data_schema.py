import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import jsonschema

logger = logging.getLogger(__name__)

class BaseJsonSchema(ABC):
    """
    JSON 스키마 기반 데이터 검증을 위한 기본 클래스
    
    이 클래스는 JSON 스키마 파일 로드, 기본 검증 등의 공통 기능을 제공합니다.
    구체적인 스키마 클래스는 이 클래스를 상속받아 특화된 검증 로직을 구현해야 합니다.
    """
    
    def __init__(self, schema_file_paths: Optional[List[str]] = None):
        """
        BaseJsonSchema 초기화
        
        매개변수:
            schema_file_paths (List[str], 선택): 스키마 파일 경로 목록
        """
        self.schema_file_paths = schema_file_paths or self._get_default_schema_paths()
        self.schema = self._load_schema()
    
    @abstractmethod
    def _get_default_schema_paths(self) -> List[str]:
        """
        기본 스키마 파일 경로들을 반환합니다.
        
        각 구체적인 스키마 클래스에서 구현해야 합니다.
        
        반환값:
            List[str]: 스키마 파일 경로 목록
        """
        pass
    
    @abstractmethod
    def _get_fallback_schema(self) -> Dict[str, Any]:
        """
        스키마 파일을 찾을 수 없을 때 사용할 기본 스키마를 반환합니다.
        
        각 구체적인 스키마 클래스에서 구현해야 합니다.
        
        반환값:
            Dict[str, Any]: JSON 스키마 딕셔너리
        """
        pass
    
    def _load_schema(self) -> Dict[str, Any]:
        """
        스키마 파일을 로드합니다.
        
        반환값:
            Dict[str, Any]: JSON 스키마 딕셔너리
        """
        # 경로에서 None 값 제거
        valid_paths = [path for path in self.schema_file_paths if path is not None]
        
        for schema_path in valid_paths:
            if os.path.exists(schema_path):
                try:
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema = json.load(f)
                        logger.info("✅ 스키마 파일 로드 성공: %s", schema_path)
                        return schema
                except json.JSONDecodeError as e:
                    logger.error("❌ 스키마 파일 JSON 파싱 오류 '%s': %s", schema_path, str(e))
                except Exception as e:
                    logger.error("❌ 스키마 파일 로드 오류 '%s': %s", schema_path, str(e))
        
        # 스키마 파일을 찾지 못한 경우 기본 스키마 반환
        logger.warning("⚠️ 스키마 파일을 찾을 수 없어 기본 스키마를 사용합니다. 시도한 경로: %s", valid_paths)
        return self._get_fallback_schema()
    
    def validate_json_schema(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], 
                           location: str = "unknown") -> List[str]:
        """
        JSON Schema 검증을 수행합니다.
        
        매개변수:
            data: 검증할 데이터 (단일 객체 또는 객체 리스트)
            location: 오류 메시지에 표시할 위치 정보
            
        반환값:
            List[str]: 검증 오류 메시지 목록 (빈 리스트면 오류 없음)
        """
        errors = []
        
        try:
            # 단일 객체인 경우 리스트로 감싸서 검증
            validation_data = data if isinstance(data, list) else [data]
            jsonschema.validate(instance=validation_data, schema=self.schema)
            
        except jsonschema.exceptions.ValidationError as e:
            error_path = '.'.join(str(p) for p in e.path) if e.path else "root"
            error_msg = f"❌ {location} - JSON Schema 검증 오류: {e.message} (경로: {error_path})"
            errors.append(error_msg)
            logger.error(error_msg)
            
        except jsonschema.exceptions.SchemaError as e:
            error_msg = f"❌ {location} - 스키마 자체에 오류가 있습니다: {e.message}"
            errors.append(error_msg)
            logger.error(error_msg)
            
        except Exception as e:
            error_msg = f"❌ {location} - 검증 중 예상치 못한 오류: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        return errors
    
    def reload_schema(self) -> bool:
        """
        스키마를 다시 로드합니다.
        
        반환값:
            bool: 로드 성공 여부
        """
        try:
            self.schema = self._load_schema()
            return True
        except Exception as e:
            logger.error("❌ 스키마 재로드 실패: %s", str(e))
            return False
    
    def get_schema_info(self) -> Dict[str, Any]:
        """
        현재 로드된 스키마 정보를 반환합니다.
        
        반환값:
            Dict[str, Any]: 스키마 정보
        """
        return {
            "schema_type": self.schema.get("$schema", "unknown"),
            "title": self.schema.get("title", "untitled"),
            "description": self.schema.get("description", ""),
            "version": self.schema.get("version", "unknown"),
            "loaded_paths": self.schema_file_paths
        }
    
    @abstractmethod
    def validate(self, data: Any, **kwargs) -> bool:
        """
        데이터 검증을 수행합니다.
        
        각 구체적인 스키마 클래스에서 구현해야 합니다.
        JSON Schema 검증 외에 추가적인 비즈니스 로직 검증을 포함할 수 있습니다.
        
        매개변수:
            data: 검증할 데이터
            **kwargs: 추가 검증 옵션
            
        반환값:
            bool: 검증 실패 시 True (오류 있음), 성공 시 False
        """
        pass


class BookmarkJsonSchema(BaseJsonSchema, ABC):
    """
    북마크 데이터를 위한 JSON 스키마 검증 클래스
    """
    
    def _get_default_schema_paths(self) -> List[str]:
        """북마크 스키마 기본 경로들을 반환합니다."""
        paths = [
            "src/schemas/bookmark.schema.json",
            "../schemas/bookmark.schema.json"
        ]

        return paths
    
    def _get_fallback_schema(self) -> Dict[str, Any]:
        """북마크 스키마의 기본 스키마를 반환합니다."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Bookmark Schema",
            "description": "Schema for bookmark validation",
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
                        "items": {"$ref": "#/definitions/packageTag"},
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
                "packageTag": {
                    "type": "object",
                    "required": ["tag"],
                    "properties": {
                        "tag": {
                            "type": "string",
                            "description": "패키지 태그명"
                        },
                        "subtags": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/packageTag"},
                            "default": [],
                            "description": "하위 태그들"
                        }
                    },
                    "additionalProperties": False
                }
            }
        }

    def validate(self, bookmarks: List[Dict[str, Any]], **kwargs) -> bool:
            """
            북마크 딕셔너리 리스트가 형식 및 제약 조건을 만족하는지 검사합니다.

            매개변수:
                bookmarks (List[Dict]): 유효성 검사를 수행할 북마크 딕셔너리 리스트
                **kwargs: 추가 검증 옵션

            반환값:
                bool: 오류가 발견되면 True, 그렇지 않으면 False
            """
            from urllib.parse import urlparse

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
                # if 'url' in bookmark_copy and 'domain' in bookmark_copy:
                #     try:
                #         parsed_url = urlparse(bookmark_copy['url'])
                #         if parsed_url.netloc != bookmark_copy['domain']:
                #             logger.error("❌ %s - 도메인 '%s'가 URL 호스트 '%s'와 일치하지 않음",
                #                        location, bookmark_copy['domain'], parsed_url.netloc)
                #             has_errors = True
                #     except Exception as e:
                #         logger.error("❌ %s - 잘못된 URL '%s': %s", location, bookmark_copy.get('url', ''), str(e))
                #         has_errors = True

                # 북마크 객체에 위치 정보 추가 (오류 메시지용)
                bookmark_copy['_location'] = location
                clean_bookmarks.append(bookmark_copy)

            # JSON Schema 검증
            for bookmark in clean_bookmarks:
                location = bookmark.pop('_location', 'unknown')
                schema_errors = self.validate_json_schema([bookmark], location)
                if schema_errors:
                    has_errors = True

            return has_errors

# # 다른 스키마 예시
# class UserJsonSchema(BaseJsonSchema):
#     """
#     사용자 데이터를 위한 JSON 스키마 검증 클래스 (예시)
#     """
#
#     def _get_default_schema_paths(self) -> List[str]:
#         """사용자 스키마 기본 경로들을 반환합니다."""
#         return [
#             "user-schema/user.schema.json",
#             "../../../user-schema/user.schema.json"
#         ]
#
#     def _get_fallback_schema(self) -> Dict[str, Any]:
#         """사용자 스키마의 기본 스키마를 반환합니다."""
#         return {
#             "$schema": "http://json-schema.org/draft-07/schema#",
#             "title": "User Schema",
#             "description": "Schema for user validation",
#             "type": "object",
#             "required": ["username", "email"],
#             "properties": {
#                 "username": {"type": "string", "minLength": 3},
#                 "email": {"type": "string", "format": "email"},
#                 "age": {"type": "integer", "minimum": 0}
#             },
#             "additionalProperties": False
#         }
#
#     def validate(self, user_data: Dict[str, Any], **kwargs) -> bool:
#         """사용자 데이터 검증을 수행합니다."""
#         has_errors = False
#
#         # JSON Schema 검증
#         schema_errors = self.validate_json_schema(user_data, "user")
#         if schema_errors:
#             has_errors = True
#
#         # 추가적인 비즈니스 로직 검증
#         if 'username' in user_data:
#             username = user_data['username']
#             if username.lower() in ['admin', 'root', 'system']:
#                 logger.error("❌ 예약된 사용자명입니다: %s", username)
#                 has_errors = True
#
#         return has_errors