# AI 사용 기록

## Claude Code 사용 내역

### 프로젝트 초기 설계
- **프롬프트**: "DeepAgent + OpenRouter 구조로 데이트 플래너 멀티에이전트 시스템 설계해줘"
- **생성된 것**: 전체 폴더 구조, 에이전트 역할 분담, debate.py 루프 구조
- **수정한 것**: response_format json_object 강제 추가 (파싱 오류 방지)

### Kakao API 연동
- **프롬프트**: "Kakao Local API로 장소 검색하고 pandas DataFrame으로 정리하는 모듈 만들어줘"
- **생성된 것**: kakao_api.py 초안
- **수정한 것**: distance 필드가 string으로 오는 문제 → `pd.to_numeric` 추가

### Docker 설정
- **프롬프트**: "CLI + FastAPI 두 서비스를 docker-compose로 구성해줘"
- **생성된 것**: Dockerfile, docker-compose.yml
- **수정한 것**: stdin_open, tty 옵션 추가 (CLI 인터랙션 지원)

## AI가 만든 코드 중 수정이 필요했던 부분
1. `scout.py` — 응답이 배열인지 객체인지 불확실 → `result.get("candidates", result)` 방어 처리
2. `verifier.py` — 한글 JSON 파싱 시 ensure_ascii=False 누락 → 추가
3. `docker-compose.yml` — 서비스 이름 충돌 → cli / api 로 분리
