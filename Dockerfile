FROM python:3.11-alpine

# PyYAML 설치
RUN pip install pyyaml

# 작업 디렉토리 설정
WORKDIR /app

# 스크립트 복사
COPY scripts/validate_bookmarks.py /app/validate_bookmarks.py

# 실행 권한 부여
RUN chmod +x /app/validate_bookmarks.py

# 환경 변수 설정 (선택 사항)
ENV PYTHONUNBUFFERED=1

# 진입점 설정 (선택 사항)
ENTRYPOINT ["python3", "/app/validate_bookmarks.py"]