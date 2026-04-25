# AI 데이트 플래너 🗺️

멀티에이전트 토론 기반 데이트 코스 추천 시스템

## 문제 정의
기존 데이트 추천 앱(데이트팝, 카카오맵)은 단순 큐레이션 수준이다.  
이 프로젝트는 **여러 AI 에이전트가 서로 토론하고 반박하며** 예산, 분위기, 동선을 동시에 최적화한다.

## 에이전트 구조
```
User Input
    ↓
[Planner - Claude]     전략 수립
    ↓
[Scout - Mixtral]      Kakao API 장소 탐색
[Budget - DeepSeek]    예산 검토 및 반박
[Vibe - Mixtral]       분위기 평가 및 반박
    ↓ (최대 3라운드 반복)
[Verifier - Claude]    최종 확정
```

## 기술 스택
| 도구 | 역할 | 선택 근거 |
|------|------|----------|
| OpenRouter | 멀티모델 API | vendor lock-in 없이 Claude/GPT/Mixtral 혼용 |
| Kakao Local API | 장소 검색 | 국내 POI 데이터 가장 정확 |
| pandas | 데이터 정리 | 장소 필터링, 거리/비용 정렬 |
| FastAPI | API 서버 | 빠른 개발, 자동 문서화(/docs) |
| Docker | 컨테이너화 | 환경 독립적 실행 보장 |

## 오픈소스 라이선스
| 패키지 | 라이선스 |
|--------|---------|
| openai | MIT |
| requests | Apache 2.0 |
| pandas | BSD 3-Clause |
| fastapi | MIT |
| uvicorn | BSD 3-Clause |

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
```

### CLI 실행
```bash
pip install -r requirements.txt
python -m src.main
```

### Docker 실행
```bash
# CLI
docker build -t date-planner .
docker run -it --env-file .env date-planner

# API 서버
docker-compose up api
# → http://localhost:8000/docs
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
