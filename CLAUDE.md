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
| 경로 | 책임 |
|---|---|
| `data_prep/` | 도메인에 묶인 코드 전부 (Initializr 파싱, spring-boot 문서 경로, 문서 수집) |
| `vector_store/` | Chroma 컬렉션(`items`, `docs`), 청킹, 색인 |
| `rag/` (예정) | LangGraph `retrieve`/`generate` 두 노드, 프롬프트 3개 |
| `services/` (예정) | 특화 기능(버전 맞춤 사용 가이드), 조건 기반 항목 탐색 |
| `app.py` | Streamlit UI. 기존 골격을 이어 쓴다 (`get_model`, `cited_sources`, `render_sources` 재사용). 아직 영화 예시 상태 |
| `build_items.py` | items 색인 스크립트 |
| `config.toml` / `config.py` | 설정 / `CONFIG`, `ROOT` 로드 |

# 실행 (Windows, Git Bash 기준)
```
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python build_items.py      # 기대 출력: 로드한 항목 204건, 색인된 청크 204건
.venv/Scripts/streamlit run app.py
```

# 환경 주의점
- 시스템 python이 아니라 `.venv/Scripts/python`을 쓴다 (명세 버전 고정 패키지가 venv에만 있음).
- 콘솔 한글이 깨지면 `PYTHONUTF8=1`을 붙인다.
- 한글 문자열을 `python -c "..."`로 넘기지 않는다 (특히 `-I`와 함께 쓰면 argv가 깨져 잘못된 검색어로 테스트된다). 임시 스크립트 파일로 실행한다.
- 임시 파일은 프로젝트 밖(스크래치 디렉터리)에 둔다.
