# sidebar-data
GitLab Project Mirroring

# GitLab CI/CD 파이프라인 설정 가이드

이 문서는 sidebar-data 프로젝트의 GitLab CI/CD 파이프라인 설정에 대한 가이드입니다.

## 프로젝트 구조

- **메인 프로젝트**: sidebar-data
- **하위 프로젝트**: data-validator (검증 스크립트와 Docker 이미지 관리)
- **다른 프로젝트들**: bookmark-data, application, ops 등이 data-validator의 검증 로직을 사용함

## CI/CD 파일 구조

### data-validator/.gitlab-ci.yml

이 파일은 data-validator 프로젝트의 메인 CI/CD 설정 파일입니다. 다음 두 파일을 조건부로 포함합니다:


```yaml
include:
  # Docker 빌드 작업 - data-validator 프로젝트에서만 실행
  - local: '/docker-build-ci.yml'
    rules:
      - if: '$CI_PROJECT_NAME == "data-validator"'
        when: always
  
  # 북마크 검증 작업 - 다른 프로젝트에서만 실행
  - local: '/validation-ci.yml'
    rules:
      - if: '$CI_PROJECT_NAME != "data-validator"'
        when: always
```

### docker-build-ci.yml

이 파일은 Docker 이미지 빌드 및 배포 작업을 포함합니다. 다음 규칙을 적용하여 data-validator 프로젝트에서만 실행되도록 합니다:

```yaml
rules:
  # data-validator 프로젝트에서만 실행
  - if: '$CI_PROJECT_NAME != "data-validator"'
    when: never
  - if: '$CI_COMMIT_BRANCH == "main"'
    changes:
      - scripts/validate_bookmarks.py
      - Dockerfile
  - if: '$CI_COMMIT_TAG'
    when: always
```

### validation-ci.yml

이 파일은 북마크 검증 작업을 포함합니다. 다음 규칙을 적용하여 data-validator 프로젝트에서는 실행되지 않고 다른 프로젝트에서만 실행되도록 합니다:

```yaml
rules:
  # data-validator 프로젝트에서는 실행하지 않음
  - if: '$CI_PROJECT_NAME == "data-validator"'
    when: never
  # 머지 리퀘스트에서만 실행
  - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    when: always
```

### 다른 프로젝트의 .gitlab-ci.yml

다른 프로젝트(bookmark-data, application, ops 등)의 .gitlab-ci.yml 파일은 data-validator 프로젝트의 .gitlab-ci.yml 파일을 포함합니다:

```yaml
include:
  - project: 'sidebar-data/data-validator'
    file: '/.gitlab-ci.yml'
```

## 작업 분리 설명

1. **validate_bookmarks 작업**:
   - data-validator 프로젝트에서는 실행되지 않음
   - 다른 프로젝트에서 머지 리퀘스트가 생성될 때 실행됨
   - 북마크 데이터의 유효성을 검증함

2. **build_docker_image, publish_tagged_version 작업**:
   - data-validator 프로젝트에서만 실행됨
   - 메인 브랜치에 변경사항이 있거나 태그가 생성될 때 실행됨
   - Docker 이미지를 빌드하고 레지스트리에 배포함