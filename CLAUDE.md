# 프로젝트
버전 인지형 Spring Boot 문서 Q&A (RAG). SSAFY AI 코어 프로젝트 2회차 제출물.
- 명세: `AI코어프로젝트_2회차_요구사항정의서.pdf` (루트, gitignore, 對外秘라 커밋 금지). 필수 F2001~F2012는 수정 불가.
- 기획: `docs/requirements.md`(요구사항 정의서), `docs/rag-design.md`(RAG 파이프라인 설계문서)
- **진행 상황과 다음 작업: `docs/progress.md`를 먼저 읽는다.**

# 규칙
- 코드 작성 전에 계획을 먼저 보여주고 확인받는다.
- 추측하지 않고 실제 저장소·API를 직접 호출해 확인한다. 확인한 사실은 날짜와 함께 docs/progress.md에 남긴다.
- 커밋 메시지, 코드 주석, 문서 어디에도 AI 작성 표기나 서명(Co-Authored-By 포함)을 넣지 않는다.
- `.env`는 읽지 않는다 (키가 들어 있다). 코드에서 `load_dotenv()`로만 쓴다.
- 커밋은 논리 단위로 나눈다. push는 사용자가 요청할 때만 한다 (origin = 제출용 lab.ssafy.com 저장소).
- 외부 호출은 1초 이상 간격, 식별용 User-Agent를 붙인다 (NF2006).
- 설정값(청크, Top-k, 검색 방식, 모델)은 `config.toml`에만 둔다. 코드에 하드코딩하지 않는다.
- 임베딩 모델을 바꾸면 `chroma_db/`를 지우고 전체 재색인한다.

# 구조 (NF2005 모듈 분리)
의존 방향: `server.py → services → rag → data_prep, vector_store`. 반대 방향 import 금지. 파일은 필요해질 때 만든다.

| 경로 | 책임 |
|---|---|
| `server.py` | FastAPI 진입점. `/api/*`(상태, 항목, 질문·가이드 SSE, 조건 탐색, 일반 지식 답변)와 `web/` 정적 화면 제공. 오류 추적은 서버 콘솔에만 |
| `web/` | HTML·CSS·JS 화면. 조건 탐색 카드, 항목·버전 선택, (항목, 버전)별 대화(localStorage), 진행 상태, 인용 근거 표시. marked·DOMPurify(cdnjs) |
| `config.toml` / `config.py` | 설정 / `CONFIG`, `ROOT` 로드 (루트 기준 경로 계산 때문에 루트에 둔다) |
| `scripts/` | 배치 스크립트. 루트에서 `python -m scripts.<이름>`으로 실행. `build_items`(items 색인), `fetch_docs`(문서 원문 수집), `compare_search`·`compare_rag`(F2014·F2015 비교), `verify`(명세 4장 자동 확인) |
| `data_prep/` | 외부 출처와 도메인 지식. LLM·Chroma 없음. `initializr.py`(항목), `boot_docs.py`(버전별 경로, 원문 수집, 매크로 정리, 후보 검색), `external_docs.py`(외부 문서 출처: springdoc, Spring Data JDBC·R2DBC·JPA·Redis·MongoDB·Elasticsearch, Spring Security. 판별 브랜치, Antora include 풀기) |
| `vector_store/` | Chroma와 청킹. 도메인 모름. `store.py`(컬렉션), `chunking.py`(헤더 단위 청킹) |
| `rag/` | LLM 흐름. `prompts.py`(프롬프트 3개 + 가이드·탐색용), `collect.py`(질문 시점 수집 F2003~F2005), `graph.py`(LangGraph retrieve/generate) |
| `services/` | `guide.py`(버전 맞춤 사용 가이드 F2010), `explore.py`(조건 기반 항목 탐색 F2011) |
| `data/` | `items.json`(커밋). gitignore: `boot_docs/`(원문 사본), `coordinates/`(버전별 좌표), `external_docs/`(외부 문서 사본, `{저장소}/{브랜치}/`), `collect_log.json`(수집 캐시) |

# 실행 (Windows, Git Bash 기준)
```
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m scripts.build_items   # 기대 출력: 로드한 항목 204건, 색인된 청크 204건
.venv/Scripts/python -m scripts.fetch_docs    # 첫 실행 약 10분. 기대 출력: 보관 문서 4.1.x 128, 4.0.x 124, 3.5.x/3.4.x 122건
.venv/Scripts/uvicorn server:app          # http://127.0.0.1:8000 (로컬에서만 열림)
```

# 환경 주의점
- 시스템 python이 아니라 `.venv/Scripts/python`을 쓴다 (명세 버전 고정 패키지가 venv에만 있음).
- 콘솔 한글이 깨지면 `PYTHONUTF8=1`을 붙인다.
- 한글 문자열을 `python -c "..."`로 넘기지 않는다 (특히 `-I`와 함께 쓰면 argv가 깨져 잘못된 검색어로 테스트된다). 임시 스크립트 파일로 실행한다.
- 임시 파일은 프로젝트 밖(스크래치 디렉터리)에 둔다.
