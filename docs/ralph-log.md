# Ralph Mode — 반복 개선 로그

## 반복 1
- **변경사항**: 기본 에이전트 구조 생성 (planner, scout, budget, vibe, verifier)
- **문제점**: 에이전트 간 데이터 포맷 불일치
- **결과**: debate.py 기본 루프 동작 확인

## 반복 2
- **변경사항**: Kakao API 연동, pandas DataFrame으로 결과 정리
- **문제점**: API 응답 필드 누락 시 KeyError 발생
- **수정**: `errors="coerce"` 처리 추가, fillna로 방어
- **결과**: 실제 장소 데이터 수신 성공

## 반복 3
- **변경사항**: FastAPI 엔드포인트 추가, docker-compose 다중 서비스 구성
- **문제점**: 컨테이너 간 환경변수 전달 누락
- **수정**: `env_file: .env` 설정 추가
- **결과**: `docker-compose up api` 로 API 서버 정상 동작
