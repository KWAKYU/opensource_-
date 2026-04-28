# AI 데이트 플래너 — 프로젝트 목표 선언

## 목표
사용자가 지역, 인원, 예산, 분위기를 입력하면  
여러 AI 에이전트가 서로 토론하여 최적의 데이트 코스를 추천한다.

## 에이전트 역할 분담

| 에이전트 | 모델 | 역할 |
|---------|------|------|
| Planner | Claude Sonnet 4.6 | 요청 분석, 전략 수립 |
| Scout | GPT-4o mini | Kakao API로 장소 탐색 및 인기도 기반 품질 검증 |
| Budget | Perplexity Sonar | 웹 검색 기반 실제 가격 추정 및 예산 검토 |
| Experience | Claude Sonnet 4.5 | 네이버 블로그 후기 기반 분위기/코스 흐름 평가 및 반박 |
| Verifier | Gemini 2.0 Flash | 토론 결과 최종 검증 및 코스 확정 |

## 토론 프로토콜
1. Planner가 요청 분석 → 구조화된 플랜 생성
2. Scout → Budget → Experience 순으로 각자 평가
3. 예산 미통과 or Experience 점수 8점 미만 시 재토론 (최소 2라운드, 최대 5라운드)
4. Experience 반박 장소만 교체, 승인된 장소는 유지 (approved_candidates)
5. Verifier가 최종 코스 확정

## 성공 기준
- 예산 초과 없이 코스 구성
- Experience 점수 8점 이상
- 최대 5라운드 이내 합의
