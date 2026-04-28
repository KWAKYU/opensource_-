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

## 반복 4
- **변경사항**: Streamlit UI 구축, 네이버 블로그 API 연동으로 실제 가격 수집
- **문제점**: Kakao API `sort=accuracy` + 좌표 동시 사용 시 400 에러
- **수정**: 좌표 있을 때 `sort=distance`, 키워드만 검색 시 `sort=accuracy`로 분리
- **결과**: 장소 탐색 정상화, Streamlit UI 토론 과정 실시간 표시

## 반복 5
- **변경사항**: 네이버 블로그 언급수(blog_count) 기반 인기도 지표 도입
- **문제점**: 지하철역 내 분식집·저가 음식점이 거리 기준으로 상위 노출
- **수정**: blog_count 1000+ 우선, 100 미만 제외 / 지하철 주소 필터 추가
- **결과**: 검증된 핫플레이스 위주로 추천 품질 향상

## 반복 6
- **변경사항**: 음식점 오분류 자동 필터링 (FOOD_NAME_KEYWORDS) 추가
- **문제점**: 스시집·육회집이 포토스팟으로 분류되는 LLM 오분류 발생
- **수정**: kakao_api.py에서 비음식 카테고리 검색 시 음식 키워드 이름 장소 제거
- **결과**: 포토스팟·쇼핑 카테고리에서 음식점 혼입 차단

## 반복 7
- **변경사항**: `_sanitize_course()` 후처리 함수 추가, MAX_CATEGORY_COUNT 도입
- **문제점**: Verifier LLM이 반나절 코스에 맛집 2개를 포함하는 오류 반복
- **수정**: Python 레벨에서 카테고리 중복 초과 시 강제 제거 + 맛집 재분류
- **결과**: LLM 신뢰 + Python 후처리 이중 안전망으로 오류 최소화

## 반복 8
- **변경사항**: Gemini rate limit 재시도 로직 추가 (5s → 10s → 15s 백오프)
- **문제점**: `openai.RateLimitError: 429` — Gemini 무료 티어 rate limit 초과
- **수정**: Experience·Verifier 에이전트에 최대 3회 재시도 루프 추가
- **결과**: rate limit 상황에서도 자동 복구, 앱 중단 없이 정상 완료

## 반복 9
- **변경사항**: `previous_feedback` + `approved_candidates` 도입으로 토론 메커니즘 강화
- **문제점**: 매 라운드 Scout가 완전 재탐색 → 좋은 장소도 버려지는 낭비
- **수정**: Experience 반박 텍스트에서 문제 장소명 추출 → 해당 슬롯만 재탐색, 나머지 유지
- **결과**: 실질적인 반복 개선 토론 구현, 코스 품질 안정적 향상
