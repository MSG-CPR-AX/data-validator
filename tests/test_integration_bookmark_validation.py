#!/usr/bin/env python3
"""
북마크 정합성 검사 통합 테스트

이 모듈은 북마크 검증 시스템의 전체 워크플로를 테스트합니다.
실제 GitLab API 대신 모킹을 사용하여 안전하게 테스트할 수 있습니다.

사용법:
    python -m pytest tests/test_integration_bookmark_validation.py -v
"""

import pytest
import tempfile
import os
import json
import yaml
from unittest.mock import Mock, patch, MagicMock
from app.orchestrator.validator_runner import DataValidationOrchestrator
from app.gitlab_utils.gitlab_fetcher import GitLabBookmarkFetcher
from app.gitlab_utils.gitlab_auth import GitLabAuthenticator
from app.gitlab_utils.gitlab_client import PatApiClient


class TestBookmarkValidationIntegration:
    """북마크 검증 시스템 통합 테스트"""

    @pytest.fixture
    def mock_pat_env_vars(self):
        """GitLab 환경 변수 모킹"""
        env_vars = {
            'CI': 'true',
            'CI_SERVER_URL': 'https://gitlab.example.com',
            'CI_PROJECT_ID': '123',
            'BOOKMARK_DATA_GROUP_ID': '456',
            'ENCRYPTED_PAT': 'gAAAAABhz1234567890abcdef',  # Fernet으로 암호화된 형태
            'PAT_ENCRYPTION_KEY': 'abcdefghijklmnopqrstuvwxyz123456',  # 32바이트 키
            'CI_PROJECT_DIR': '/tmp/test_project'
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            yield env_vars

    @pytest.fixture
    def mock_deploy_token_env_vars(self):
        """배포 토큰 환경 변수 모킹"""
        env_vars = {
            'CI': 'true',
            'CI_SERVER_URL': 'https://gitlab.example.com',
            'CI_PROJECT_ID': '123',
            'BOOKMARK_DATA_GROUP_ID': '456',
            'ENCRYPTED_DEPLOY_TOKEN': 'gAAAAABhz9876543210fedcba',
            'ENCRYPTION_KEY': 'zyxwvutsrqponmlkjihgfedcba654321',
            'DEPLOY_TOKEN_USERNAME': 'deploy_user',
            'CI_PROJECT_DIR': '/tmp/test_project'
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            yield env_vars

    @pytest.fixture
    def sample_gitlab_projects(self):
        """샘플 GitLab 프로젝트 데이터"""
        return [
            {
                'id': 1,
                'name': 'bookmark-project-1',
                'path_with_namespace': 'group/bookmark-project-1'
            },
            {
                'id': 2, 
                'name': 'bookmark-project-2',
                'path_with_namespace': 'group/bookmark-project-2'
            }
        ]

    @pytest.fixture
    def sample_yaml_files(self):
        """샘플 YAML 파일 데이터"""
        return [
            {
                'path': 'bookmarks.yml',
                'content': yaml.dump([
                    {
                        'url': 'https://www.google.com',
                        'name': '구글',
                        'domain': 'google',
                        'category': 'search',
                        'packages': [
                            {
                                "tag": "frontend",
                                "subtags": [{"tag": "react"}]
                             },
                            {
                                "tag": "ui-library"
                            }
                        ]
                    },
                    {
                        'url': 'https://www.naver.com',
                        'name': '네이버',
                        'domain': 'naver',
                        'category': 'search',
                        'packages': []
                    }
                ]),
                'project_id': 1,
                'project_path_for_log': 'group/bookmark-project-1'
            },
            {
                'path': 'tech-bookmarks.yaml',
                'content': yaml.dump([
                    {
                        'url': 'https://github.com',
                        'name': 'GitHub',
                        'domain': 'github',
                        'category': 'development',
                        'packages': []
                    },
                    {
                        'url': 'https://stackoverflow.com',
                        'name': 'Stack Overflow',
                        'domain': 'stackoverflow',
                        'category': 'development',
                        'packages': []
                    }
                ]),
                'project_id': 2,
                'project_path_for_log': 'group/bookmark-project-2'
            }
        ]

    @pytest.fixture
    def invalid_yaml_files(self):
        """유효하지 않은 YAML 파일 데이터"""
        return [
            {
                'path': 'invalid-bookmarks.yml',
                'content': yaml.dump([
                    {
                        'name': '제목만 있는 북마크',
                        # url이 없음 - 스키마 검증 실패
                        'category': 'invalid'
                    },
                    {
                        'name': 'URL이 잘못된 북마크',
                        'url': 'not-a-valid-url',  # 잘못된 URL 형식
                        'category': 'invalid'
                    }
                ]),
                'project_id': 3,
                'project_path_for_log': 'group/invalid-project'
            }
        ]

    def test_successful_validation_workflow_with_pat(self, mock_pat_env_vars, sample_gitlab_projects,
                                                     sample_yaml_files):
        """PAT를 사용한 성공적인 검증 워크플로 테스트"""
        # TokenCipher의 decrypt 메서드 모킹
        with patch('app.gitlab_utils.gitlab_auth.TokenCipher') as mock_cipher_class:
            mock_cipher = Mock()
            mock_cipher_class.return_value = mock_cipher
            mock_cipher.decrypt.return_value = 'decrypted_pat_token'

            # GitLab API 클라이언트 모킹
            with patch('app.gitlab_utils.gitlab_fetcher.PatApiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client

                # 프로젝트 목록 모킹
                mock_client.fetch_group_projects.return_value = sample_gitlab_projects

                # YAML 파일 목록 모킹
                mock_client.fetch_all_yaml_files_from_group.return_value = sample_yaml_files

                # 오케스트레이터 실행
                orchestrator = DataValidationOrchestrator()
                result = orchestrator.run()

                # 검증
                assert result == 0  # 성공적인 실행
                # mock_client.fetch_group_projects.assert_called_once()
                # mock_client.fetch_all_yaml_files_from_group.assert_called_once()
                #
                # # 모킹된 메서드가 호출되었는지 확인
                # mock_client.fetch_group_projects.assert_called_with('456')

    def test_successful_validation_workflow_with_deploy_token(self, mock_deploy_token_env_vars, 
                                                            sample_gitlab_projects, sample_yaml_files):
        """배포 토큰을 사용한 성공적인 검증 워크플로 테스트"""
        
        # TokenCipher의 decrypt 메서드 모킹 (배포 토큰용)
        with patch('app.gitlab_utils.gitlab_auth.TokenCipher') as mock_cipher_class:
            mock_cipher = Mock()
            mock_cipher_class.return_value = mock_cipher
            mock_cipher.decrypt.return_value = 'decrypted_deploy_token'
            
            # GitLab API 클라이언트 모킹
            with patch('app.gitlab_utils.gitlab_fetcher.PatApiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                # 프로젝트 목록 모킹
                mock_client.fetch_group_projects.return_value = sample_gitlab_projects
                
                # YAML 파일 목록 모킹
                mock_client.fetch_all_yaml_files_from_group.return_value = sample_yaml_files
                
                # 오케스트레이터 실행
                orchestrator = DataValidationOrchestrator()
                result = orchestrator.run()
                
                # 검증
                assert result == 0

    def test_gitlab_fetcher_integration(self, mock_pat_env_vars, sample_gitlab_projects, sample_yaml_files):
        """GitLab 데이터 수집기 통합 테스트"""
        
        with patch('app.gitlab_utils.gitlab_auth.TokenCipher') as mock_cipher_class:
            mock_cipher = Mock()
            mock_cipher_class.return_value = mock_cipher
            mock_cipher.decrypt.return_value = 'decrypted_pat_token'
            
            with patch('app.gitlab_utils.gitlab_fetcher.PatApiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                # 모킹 설정
                mock_client.fetch_group_projects.return_value = sample_gitlab_projects
                mock_client.fetch_all_yaml_files_from_group.return_value = sample_yaml_files
                
                # GitLab 수집기 테스트
                authenticator = GitLabAuthenticator()
                fetcher = GitLabBookmarkFetcher(authenticator)
                
                # 프로젝트 수집 테스트
                projects = fetcher.fetch_group_projects('456')
                assert len(projects) == 2
                assert projects[0]['name'] == 'bookmark-project-1'
                
                # 북마크 수집 테스트
                bookmarks = fetcher.fetch_all_bookmarks('456')
                assert len(bookmarks) == 4  # 2개 파일 * 2개 북마크씩
                assert all('_source_project' in bookmark for bookmark in bookmarks)
                assert all('_source_file' in bookmark for bookmark in bookmarks)

    def test_validation_with_schema_errors(self, mock_pat_env_vars, sample_gitlab_projects,
                                           invalid_yaml_files):
        """스키마 오류가 있는 데이터 검증 테스트"""

        with patch('app.gitlab_utils.gitlab_auth.TokenCipher') as mock_cipher_class:
            mock_cipher = Mock()
            mock_cipher_class.return_value = mock_cipher
            mock_cipher.decrypt.return_value = 'decrypted_pat_token'
            
            with patch('app.gitlab_utils.gitlab_fetcher.PatApiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                # 유효하지 않은 데이터 모킹
                mock_client.fetch_group_projects.return_value = sample_gitlab_projects
                mock_client.fetch_all_yaml_files_from_group.return_value = invalid_yaml_files
                
                # 오케스트레이터 실행
                orchestrator = DataValidationOrchestrator()
                result = orchestrator.run()
                
                # 검증 실패 예상
                assert result == 1  # 검증 실패

    def test_authentication_failure_missing_pat_vars(self):
        """PAT 환경변수 누락 시 인증 실패 테스트"""
        
        # PAT 관련 환경변수 제거
        env_vars = {
            'CI_SERVER_URL': 'https://gitlab.example.com',
            'CI_PROJECT_ID': '123',
            'BOOKMARK_DATA_GROUP_ID': '456',
            'CI_PROJECT_DIR': '/tmp/test_project'
            # ENCRYPTED_PAT, PAT_ENCRYPTION_KEY 누락
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="Missing PAT environment variables"):
                authenticator = GitLabAuthenticator()
                authenticator.get_pat_headers()

    def test_authentication_failure_missing_deploy_token_vars(self):
        """배포 토큰 환경변수 누락 시 인증 실패 테스트"""
        
        # 배포 토큰 관련 환경변수 제거
        env_vars = {
            'CI_SERVER_URL': 'https://gitlab.example.com',
            'CI_PROJECT_ID': '123',
            'BOOKMARK_DATA_GROUP_ID': '456',
            'CI_PROJECT_DIR': '/tmp/test_project'
            # ENCRYPTED_DEPLOY_TOKEN, ENCRYPTION_KEY, DEPLOY_TOKEN_USERNAME 누락
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="Missing Deploy Token environment variables"):
                authenticator = GitLabAuthenticator()
                authenticator.get_deploy_token_headers()

    def test_network_failure_handling(self, mock_pat_env_vars):
        """네트워크 실패 처리 테스트"""
        
        with patch('app.gitlab_utils.gitlab_auth.TokenCipher') as mock_cipher_class:
            mock_cipher = Mock()
            mock_cipher_class.return_value = mock_cipher
            mock_cipher.decrypt.return_value = 'decrypted_pat_token'
            
            with patch('app.gitlab_utils.gitlab_fetcher.PatApiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                # 네트워크 오류 시뮬레이션
                import requests
                mock_client.fetch_group_projects.side_effect = requests.exceptions.RequestException("Network error")
                
                # 오케스트레이터 실행
                orchestrator = DataValidationOrchestrator()
                result = orchestrator.run()
                
                # 네트워크 오류로 인한 실패 예상
                assert result == 1

    def test_yaml_parsing_error_handling(self, mock_pat_env_vars, sample_gitlab_projects):
        """YAML 파싱 오류 처리 테스트"""
        
        # 잘못된 YAML 파일
        malformed_yaml_files = [
            {
                'path': 'malformed.yml',
                'content': 'invalid: yaml: content: [unclosed bracket',
                'project_id': 1,
                'project_path_for_log': 'group/malformed-project'
            }
        ]
        
        with patch('app.gitlab_utils.gitlab_auth.TokenCipher') as mock_cipher_class:
            mock_cipher = Mock()
            mock_cipher_class.return_value = mock_cipher
            mock_cipher.decrypt.return_value = 'decrypted_pat_token'
            
            with patch('app.gitlab_utils.gitlab_fetcher.PatApiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                mock_client.fetch_group_projects.return_value = sample_gitlab_projects
                mock_client.fetch_all_yaml_files_from_group.return_value = malformed_yaml_files
                
                # GitLab 수집기 테스트
                authenticator = GitLabAuthenticator()
                fetcher = GitLabBookmarkFetcher(authenticator)
                
                # YAML 파싱 오류가 있어도 예외 없이 처리되어야 함
                bookmarks = fetcher.fetch_all_bookmarks('456')
                assert len(bookmarks) == 0  # 파싱 실패로 북마크 없음

    def test_authenticator_has_methods(self, mock_pat_env_vars):
        """GitLabAuthenticator의 has_pat, has_deploy_token 메서드 테스트"""
        
        authenticator = GitLabAuthenticator()
        
        # PAT 환경변수가 설정되어 있으므로 True 반환
        assert authenticator.has_pat() is True
        
        # 배포 토큰 환경변수가 설정되지 않았으므로 False 반환
        assert authenticator.has_deploy_token() is False

    def test_authenticator_has_deploy_token_only(self, mock_deploy_token_env_vars):
        """배포 토큰만 있는 경우 테스트"""
        
        authenticator = GitLabAuthenticator()
        
        # PAT 환경변수가 설정되지 않았으므로 False 반환
        assert authenticator.has_pat() is False
        
        # 배포 토큰 환경변수가 설정되어 있으므로 True 반환
        assert authenticator.has_deploy_token() is True

    def test_token_cipher_decrypt_mocking(self, mock_pat_env_vars):
        """TokenCipher decrypt 메서드 모킹 테스트"""
        
        with patch('app.gitlab_utils.gitlab_auth.TokenCipher') as mock_cipher_class:
            mock_cipher = Mock()
            mock_cipher_class.return_value = mock_cipher
            mock_cipher.decrypt.return_value = 'test_decrypted_token'
            
            authenticator = GitLabAuthenticator()
            headers = authenticator.get_pat_headers()
            
            # 헤더가 올바르게 설정되는지 확인
            assert 'Private-Token' in headers
            assert headers['Private-Token'] == 'test_decrypted_token'
            
            # TokenCipher가 올바른 키로 생성되는지 확인
            mock_cipher_class.assert_called_with(key='abcdefghijklmnopqrstuvwxyz123456')
            
            # decrypt 메서드가 올바른 암호화된 토큰으로 호출되는지 확인
            mock_cipher.decrypt.assert_called_with('gAAAAABhz1234567890abcdef')

    @pytest.mark.parametrize("bookmark_count,expected_exit_code", [
        (0, 0),   # 북마크 없음 - 성공
        (10, 0),  # 정상 북마크 - 성공
        (100, 0), # 많은 북마크 - 성공
    ])
    def test_different_bookmark_counts(self, mock_pat_env_vars, bookmark_count, expected_exit_code):
        """다양한 북마크 수량에 대한 테스트"""
        
        # 동적으로 북마크 생성
        bookmarks = []
        for i in range(bookmark_count):
            bookmarks.append({
                'url': f'https://example{i}.com',
                'name': f'북마크 {i}',
                'domain': 'test',
                'category': 'test',
                'packages': [
                    {
                        'tag': 'test'
                    }
                ]
            })
        
        yaml_files = [{
            'path': 'test-bookmarks.yml',
            'content': yaml.dump(bookmarks),
            'project_id': 1,
            'project_path_for_log': 'group/test-project'
        }]
        
        with patch('app.gitlab_utils.gitlab_auth.TokenCipher') as mock_cipher_class:
            mock_cipher = Mock()
            mock_cipher_class.return_value = mock_cipher
            mock_cipher.decrypt.return_value = 'decrypted_pat_token'
            
            with patch('app.gitlab_utils.gitlab_fetcher.PatApiClient') as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value = mock_client
                
                mock_client.fetch_group_projects.return_value = [{'id': 1, 'name': 'test', 'path_with_namespace': 'group/test'}]
                mock_client.fetch_all_yaml_files_from_group.return_value = yaml_files
                
                orchestrator = DataValidationOrchestrator()
                result = orchestrator.run()
                
                assert result == expected_exit_code


def test_end_to_end_mock_scenario():
    """완전한 종단간 모킹 시나리오 테스트"""

    # 전체 환경 모킹
    env_vars = {
        'CI_SERVER_URL': 'https://gitlab.example.com',
        'CI_PROJECT_ID': '123',
        'BOOKMARK_DATA_GROUP_ID': '456',
        'ENCRYPTED_PAT': 'gAAAAABhz1234567890abcdef',
        'PAT_ENCRYPTION_KEY': 'abcdefghijklmnopqrstuvwxyz123456'
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        with patch('app.gitlab_utils.gitlab_auth.TokenCipher') as mock_cipher_class:
            mock_cipher = Mock()
            mock_cipher_class.return_value = mock_cipher
            mock_cipher.decrypt.return_value = 'valid_pat_token'
            
            with patch('requests.get') as mock_get, patch('requests.request') as mock_request:
                # GitLab API 응답 모킹
                mock_request.return_value.json.return_value = [
                    {'id': 1, 'name': 'test-project', 'path_with_namespace': 'group/test-project'}
                ]
                mock_request.return_value.raise_for_status.return_value = None
                
                # 파일 내용 모킹
                mock_get.return_value.text = yaml.dump([
                    {'title': '테스트', 'url': 'https://test.com', 'category': 'test'}
                ])
                mock_get.return_value.raise_for_status.return_value = None
                
                # 메인 스크립트 실행
                from scripts.validate_bookmarks import main
                result = main()
                
                # 성공적인 실행 검증
                assert result == 0