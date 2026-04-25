# AI 데이트 플래너 — 프로젝트 목표 선언

## 목표
사용자가 지역, 인원, 예산, 분위기를 입력하면  
여러 AI 에이전트가 서로 토론하여 최적의 데이트 코스를 추천한다.

## 에이전트 역할 분담

| 에이전트 | 모델 | 역할 |
|---------|------|------|
| Planner | Claude Sonnet 4.6 | 요청 분석, 전략 수립 |
| Scout | Claude Sonnet 4.6 | Kakao API로 장소 탐색 및 품질 검증 |
| Budget | Perplexity Sonar | 웹 검색 기반 실제 가격 추정 및 예산 검토 |
| Experience | Gemma 3 27B | 네이버 블로그 후기 기반 분위기/코스 흐름 평가 |
| Verifier | Claude Haiku | 토론 결과 최종 검증 및 코스 확정 |

## 토론 프로토콜
1. Planner가 요청 분석 → 구조화된 플랜 생성
2. Scout → Budget → Vibe 순으로 각자 평가
3. 예산 미통과 or 분위기 점수 7 미만 시 재토론 (최소 2라운드, 최대 5라운드)
4. Verifier(Claude)가 최종 코스 확정

## 팀 역할 분담

- **팀원 A**: 에이전트 로직 (`src/agents/`, `src/debate.py`)
- **팀원 B**: 인프라 (`Dockerfile`, `docker-compose.yml`, `api/`, `docs/`)

## 성공 기준
- 예산 초과 없이 코스 구성
- Experience 점수 7점 이상
- 최대 5라운드 이내 합의
