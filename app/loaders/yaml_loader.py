import os
import logging
import yaml

logger = logging.getLogger(__name__)

def find_yaml_files(self, base_dir):
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

def load_yaml_file(self, yaml_file):
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

def load_current_project_yaml_files(self, current_dir):
    """
    현재 프로젝트 디렉토리의 모든 북마크 YAML 파일을 로드합니다.

    매개변수:
        current_dir (str): 현재 프로젝트 디렉토리

    반환값:
        tuple: (북마크 리스트, 오류 여부)
    """
    yaml_files = self.find_yaml_files(current_dir)
    if not yaml_files:
        logger.warning("⚠️  %s 에서 YAML 파일을 찾을 수 없습니다.", current_dir)
        return [], False

    logger.info("🔍 현재 프로젝트에서 %s개의 YAML 파일을 찾았습니다.", len(yaml_files))

    all_bookmarks = []
    has_errors = False

    for yaml_file in yaml_files:
        bookmarks, file_has_errors = self.load_yaml_file(yaml_file)
        all_bookmarks.extend(bookmarks)
        has_errors = has_errors or file_has_errors

    return all_bookmarks, has_errors