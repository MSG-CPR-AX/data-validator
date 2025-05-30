#!/usr/bin/env python3
"""
북마크 YAML 검증기 테스트

이 모듈은 app.validators.bookmark_validator 모듈의 기능을 테스트합니다.
"""

import unittest
import tempfile
import os
import yaml
from app.validators.bookmark_validator import BookmarkValidator, SchemaLoader

class TestBookmarkValidator(unittest.TestCase):
    """북마크 YAML 검증기 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        # 테스트에 사용할 BookmarkValidator 인스턴스 생성
        self.validator = BookmarkValidator()

    def test_valid_bookmark(self):
        """유효한 북마크 검증 테스트"""
        valid_bookmark = [{
            "name": "GitLab Docs",
            "url": "https://docs.gitlab.com",
            "domain": "docs.gitlab.com",
            "category": "DevOps/GitLab",
            "packages": [
                {
                    "key": "공통",
                    "children": [
                        {
                            "key": "문서",
                            "children": []
                        }
                    ]
                }
            ],
            "_source_file": "test.yml",
            "_source_project": "current",
            "_index": 1
        }]

        has_errors = self.validator.validate_bookmarks(valid_bookmark)
        self.assertFalse(has_errors, "유효한 북마크가 오류로 표시됨")

    def test_missing_required_field(self):
        """필수 필드 누락 테스트"""
        # name 필드 누락
        invalid_bookmark = [{
            "url": "https://docs.gitlab.com",
            "domain": "docs.gitlab.com",
            "category": "DevOps/GitLab",
            "packages": [],
            "_source_file": "test.yml",
            "_source_project": "current",
            "_index": 1
        }]

        has_errors = self.validator.validate_bookmarks(invalid_bookmark)
        self.assertTrue(has_errors, "필수 필드 누락이 오류로 표시되지 않음")

    def test_malformed_packages(self):
        """잘못된 packages 구조 테스트"""
        # packages가 리스트가 아님
        invalid_bookmark = [{
            "name": "GitLab Docs",
            "url": "https://docs.gitlab.com",
            "domain": "docs.gitlab.com",
            "category": "DevOps/GitLab",
            "packages": "not-a-list",
            "_source_file": "test.yml",
            "_source_project": "current",
            "_index": 1
        }]

        has_errors = self.validator.validate_bookmarks(invalid_bookmark)
        self.assertTrue(has_errors, "잘못된 packages 구조가 오류로 표시되지 않음")

        # packageNode에 key 필드 누락
        invalid_bookmark = [{
            "name": "GitLab Docs",
            "url": "https://docs.gitlab.com",
            "domain": "docs.gitlab.com",
            "category": "DevOps/GitLab",
            "packages": [
                {
                    "children": []
                }
            ],
            "_source_file": "test.yml",
            "_source_project": "current",
            "_index": 1
        }]

        has_errors = self.validator.validate_bookmarks(invalid_bookmark)
        self.assertTrue(has_errors, "key 필드 누락이 오류로 표시되지 않음")

        # packageNode에 children 필드 누락
        invalid_bookmark = [{
            "name": "GitLab Docs",
            "url": "https://docs.gitlab.com",
            "domain": "docs.gitlab.com",
            "category": "DevOps/GitLab",
            "packages": [
                {
                    "key": "공통"
                }
            ],
            "_source_file": "test.yml",
            "_source_project": "current",
            "_index": 1
        }]

        has_errors = self.validator.validate_bookmarks(invalid_bookmark)
        self.assertTrue(has_errors, "children 필드 누락이 오류로 표시되지 않음")

    def test_unknown_top_level_key(self):
        """알 수 없는 최상위 키 테스트"""
        invalid_bookmark = [{
            "name": "GitLab Docs",
            "url": "https://docs.gitlab.com",
            "domain": "docs.gitlab.com",
            "category": "DevOps/GitLab",
            "packages": [],
            "unknown_key": "value",  # 알 수 없는 키
            "_source_file": "test.yml",
            "_source_project": "current",
            "_index": 1
        }]

        has_errors = self.validator.validate_bookmarks(invalid_bookmark)
        self.assertTrue(has_errors, "알 수 없는 최상위 키가 오류로 표시되지 않음")

    def test_duplicate_urls(self):
        """중복 URL 테스트"""
        bookmarks = [
            {
                "name": "GitLab Docs 1",
                "url": "https://docs.gitlab.com",
                "domain": "docs.gitlab.com",
                "category": "DevOps/GitLab",
                "packages": [],
                "_source_file": "test1.yml",
                "_source_project": "current",
                "_index": 1
            },
            {
                "name": "GitLab Docs 2",
                "url": "https://docs.gitlab.com",  # 중복 URL
                "domain": "docs.gitlab.com",
                "category": "DevOps/GitLab",
                "packages": [],
                "_source_file": "test2.yml",
                "_source_project": "current",
                "_index": 1
            }
        ]

        has_errors = self.validator.validate_bookmarks(bookmarks)
        self.assertTrue(has_errors, "중복 URL이 오류로 표시되지 않음")

    def test_empty_packages(self):
        """빈 packages 테스트"""
        valid_bookmark = [{
            "name": "GitLab Docs",
            "url": "https://docs.gitlab.com",
            "domain": "docs.gitlab.com",
            "category": "DevOps/GitLab",
            "packages": [],  # 빈 리스트
            "_source_file": "test.yml",
            "_source_project": "current",
            "_index": 1
        }]

        has_errors = self.validator.validate_bookmarks(valid_bookmark)
        self.assertFalse(has_errors, "빈 packages 리스트가 오류로 표시됨")

    def test_meta_field(self):
        """meta 필드 테스트"""
        valid_bookmark = [{
            "name": "GitLab Docs",
            "url": "https://docs.gitlab.com",
            "domain": "docs.gitlab.com",
            "category": "DevOps/GitLab",
            "packages": [],
            "meta": {
                "owner": "DevOps Team",
                "lastReviewed": "2023-05-20",
                "custom": {
                    "nested": "value"
                }
            },
            "_source_file": "test.yml",
            "_source_project": "current",
            "_index": 1
        }]

        has_errors = self.validator.validate_bookmarks(valid_bookmark)
        self.assertFalse(has_errors, "유효한 meta 필드가 오류로 표시됨")

    def test_schema_loader(self):
        """스키마 로더 테스트"""
        schema_loader = SchemaLoader()
        schema = schema_loader.load_schema()

        # 스키마가 올바른 형식인지 확인
        self.assertIsInstance(schema, dict, "스키마가 딕셔너리가 아님")
        self.assertIn("$schema", schema, "스키마에 $schema 필드가 없음")
        self.assertIn("type", schema, "스키마에 type 필드가 없음")
        self.assertEqual(schema["type"], "array", "스키마의 type이 array가 아님")

if __name__ == "__main__":
    unittest.main()
