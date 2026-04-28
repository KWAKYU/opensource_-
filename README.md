# 서울 코스 추천기 🗺️

멀티에이전트 토론 기반 서울 나들이 코스 추천 시스템

## 🚀 바로 실행하기
**[https://kblxq6vycrhqsjbrnnxf3k.streamlit.app](https://kblxq6vycrhqsjbrnnxf3k.streamlit.app)**  
설치 없이 브라우저에서 바로 사용 가능

## 문제 정의
기존 코스 추천 앱(데이트팝, 카카오맵)은 단순 큐레이션 수준이다.  
이 프로젝트는 **여러 AI 에이전트가 서로 토론하고 반박하며** 예산, 동선, 테마를 동시에 최적화한다.

## 에이전트 구조
```
User Input
    ↓
[Planner - Claude Sonnet 4.6]    전략 수립, 카테고리 스케줄 설계
    ↓
[Scout - Claude Sonnet 4.6]      Kakao API 장소 탐색 + 품질/인기도 검증
[Budget - Perplexity Sonar]      웹 검색 기반 실제 가격 추정 및 예산 검토
[Experience - Gemma 3 27B]       네이버 블로그 후기 기반 분위기/흐름 평가
    ↓ (최소 2 ~ 최대 5라운드 반복)
[Verifier - Claude Haiku]        최종 코스 확정
```

## 기술 스택
| 도구 | 역할 | 선택 근거 |
|------|------|----------|
| OpenRouter | 멀티모델 API | vendor lock-in 없이 Claude/Mixtral/Perplexity 혼용 |
| Kakao Local API | 장소 검색 | 국내 POI 데이터 가장 정확, 무료 |
| Naver Blog Search API | 실제 가격 수집 | 블로그 후기에서 실제 가격 추출 |
| Perplexity (웹 검색) | 실시간 가격 보완 | 웹 검색 내장 모델로 최신 가격 파악 |
| pandas | 데이터 정리 | 장소 필터링, 거리/비용 정렬 |
| Streamlit | 웹 UI | 에이전트 토론 과정 실시간 시각화 |
| FastAPI | REST API | 빠른 개발, 자동 문서화(/docs) |
| Docker | 컨테이너화 | 환경 독립적 실행 보장 |

## 오픈소스 라이선스
| 패키지 | 라이선스 |
|--------|---------|
| openai | MIT |
| requests | Apache 2.0 |
| pandas | BSD 3-Clause |
| fastapi | MIT |
| uvicorn | BSD 3-Clause |
| streamlit | Apache 2.0 |

이 프로젝트를 오픈소스로 공개한다면 **MIT 라이선스**를 선택할 것이다.  
사용 제약이 적고 학술/상업 목적 모두 허용되어 확산에 유리하기 때문이다.

## 실행 방법

### 환경변수 설정
```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

`.env` 파일:
```
OPENROUTER_API_KEY=your_key_here
KAKAO_API_KEY=your_key_here
NAVER_CLIENT_ID=your_key_here       # 네이버 Developers → 검색 API
NAVER_CLIENT_SECRET=your_key_here
```

### API 키 발급
| API | 발급처 | 비용 |
|-----|--------|------|
| OpenRouter | openrouter.ai | 종량제 (~$0.025/회) |
| Kakao Local | developers.kakao.com | 무료 |
| Naver 블로그 검색 | developers.naver.com → 검색 | 무료 |

### Streamlit UI 실행 (권장)
```bash
pip install -r requirements.txt
streamlit run app.py
# → http://localhost:8501
```

### CLI 실행
```bash
python3 -m src.main
```

### Docker 실행
```bash
# Streamlit UI (권장)
docker compose up streamlit --build
# → http://localhost:8501

# API 서버
docker compose up api --build
# → http://localhost:8000/docs

# CLI
docker compose up cli
```

## 보안 점검
```bash
pip install pip-audit
pip-audit
```

## 협업 플로우
- `feature/agents` 브랜치: 에이전트 로직 개발
- `infra/docker` 브랜치: Docker + FastAPI 설정
- PR 리뷰 후 main 머지
