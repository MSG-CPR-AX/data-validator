# sidebar-data
GitLab Project Mirroring

# GitLab CI/CD 파이프라인 설정 가이드

이 문서는 sidebar-data 프로젝트의 GitLab CI/CD 파이프라인 설정에 대한 가이드입니다.

## 프로젝트 구조

- **메인 프로젝트**: sidebar-data
- **하위 프로젝트**: data-validator (검증 스크립트와 Docker 이미지 관리)
- **다른 프로젝트들**: bookmark-data, application, ops 등이 data-validator의 검증 로직을 사용함

## 배포 토큰 설정 가이드

북마크 데이터 검증 시스템은 GitLab API에 접근하기 위해 배포 토큰(Deploy Token)을 사용합니다. 배포 토큰은 보안을 위해 암호화되어 저장되고 실행 시에만 복호화됩니다.

### 1. 토큰 생성

#### 1.1 배포 토큰 생성

1. GitLab 그룹 설정 페이지로 이동합니다.
2. 왼쪽 메뉴에서 "설정 > 저장소 > 배포 토큰"을 선택합니다.
3. 새 배포 토큰을 생성합니다:
   - 이름: `bookmark-validator`
   - 범위: `read_repository` 권한만 선택
4. 생성된 토큰 정보(사용자 이름과 토큰 값)를 안전하게 보관합니다.

#### 1.2 개인 접근 토큰 생성

1. GitLab 개인 설정 페이지로 이동합니다.
2. 왼쪽 메뉴에서 "접근 토큰"을 선택합니다.
3. 새 개인 접근 토큰을 생성합니다:
   - 이름: `bookmark-api-token`
   - 범위: `api`, `read_api`
   - 만료일: 필요에 따라 설정
4. 생성된 토큰 값을 안전하게 보관합니다.

### 2. 토큰 암호화

토큰을 암호화하기 위해 다음 Python 스크립트를 사용합니다:
```python
from cryptography.fernet import Fernet
import base64

# 배포 토큰 암호화 키 생성
deploy_token_key = Fernet.generate_key()
print(f"배포 토큰 암호화 키: {deploy_token_key.decode()}")

# 배포 토큰 암호화
deploy_token = "example"
cipher = Fernet(deploy_token_key)
encrypted_token = cipher.encrypt(deploy_token.encode())
print(f"배포 토큰 암호화된 토큰: {encrypted_token.decode()}")

# PAT 암호화 키 생성
pat_key = Fernet.generate_key()
print(f"PAT 암호화 키: {pat_key.decode()}")

# PAT 암호화
pat = "example"
cipher = Fernet(pat_key)
encrypted_pat = cipher.encrypt(pat.encode())
print(f"암호화된 PAT: {encrypted_pat.decode()}")
```

### 3. CI/CD 변수 설정

1. GitLab 그룹 설정 페이지로 이동합니다.
2. 왼쪽 메뉴에서 "설정 > CI/CD"를 선택합니다.
3. "변수" 섹션에서 다음 변수를 추가합니다:
   - 배포 토큰 관련 변수:
      - `ENCRYPTED_DEPLOY_TOKEN`: 암호화된 배포 토큰
      - `ENCRYPTION_KEY`: 배포 토큰 암호화 키
      - `DEPLOY_TOKEN_USERNAME`: 배포 토큰 사용자 이름
   - 개인 접근 토큰 관련 변수:
      - `ENCRYPTED_PAT`: 암호화된 개인 접근 토큰
      - `PAT_ENCRYPTION_KEY`: PAT 암호화 키
   - 그룹 정보 변수:
      - `BOOKMARK_DATA_GROUP_ID`: 북마크 데이터 그룹 ID

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
      - scripts/*.py
      - Dockerfile
  - if: '$CI_COMMIT_TAG'
    when: always
```


### validation-ci.yml

이 파일은 북마크 검증 작업을 포함합니다. 다음 규칙을 적용하여 data-validator 프로젝트에서는 실행되지 않고 다른 프로젝트에서만 실행되도록 합니다:

```yaml
variables:
  # bookmark-data 그룹 ID 지정
  # BOOKMARK_DATA_GROUP_ID: (CI/CD 설정에서 설정/실제 그룹 ID로 변경해야 함)

  # 배포 토큰 관련 변수는 CI/CD 설정에서 추가해야 함
  # ENCRYPTED_DEPLOY_TOKEN: (CI/CD 설정에서 설정)
  # ENCRYPTION_KEY: (CI/CD 설정에서 설정)
  # DEPLOY_TOKEN_USERNAME: (CI/CD 설정에서 설정)
```

### 다른 프로젝트의 .gitlab-ci.yml
다른 프로젝트(bookmark-data, application, ops 등)의 .gitlab-ci.yml 파일은 data-validator 프로젝트의 .gitlab-ci.yml 파일을 포함합니다
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

## 검증 규칙
북마크 데이터는 다음 규칙에 따라 검증됩니다:
1. 필수 필드: `url`, `name`, `domain`, `category`, `packages`
2. URL 중복 없음 (모든 프로젝트에 걸쳐서 검사)
3. `domain` 필드는 URL의 호스트와 일치해야 함
4. `packages`는 `key`와 `children`을 가진 객체의 리스트여야 함 (빈 리스트 허용)
5. `meta` 필드는 선택적이며 추가 속성을 허용함

## JSON Schema 검증
북마크 데이터는 `bookmark-schema/bookmark.schema.json` 파일에 정의된 JSON Schema를 사용하여 검증됩니다. 이 스키마는 다음과 같은 구조를 가집니다:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["name", "url", "domain", "category", "packages"],
    "properties": {
      "name": { "type": "string" },
      "url": { "type": "string", "format": "uri" },
      "domain": { "type": "string" },
      "category": { "type": "string" },
      "packages": {
        "type": "array",
        "items": { "$ref": "#/definitions/packageNode" },
        "default": []
      },
      "meta": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "additionalProperties": false
  },
  "definitions": {
    "packageNode": {
      "type": "object",
      "required": ["key", "children"],
      "properties": {
        "key": { "type": "string" },
        "children": {
          "type": "array",
          "items": { "$ref": "#/definitions/packageNode" }
        }
      },
      "additionalProperties": false
    }
  }
}
```

## 예제 YAML 형식

유효한 북마크 예제:

```yaml
- name: "GitLab Docs"
  url: "https://docs.gitlab.com"
  domain: "docs.gitlab.com"
  category: "DevOps/GitLab"
  packages:
    - key: "공통"
      children:
        - key: "문서"
          children: []
  meta:
    owner: "DevOps Team"
    lastReviewed: "2023-05-20"

# 최소 필수 필드만 포함한 예제
- name: "Google"
  url: "https://www.google.com"
  domain: "www.google.com"
  category: "Search/Engine"
  packages: []
```
