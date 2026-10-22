# 버전 인지형 Spring Boot 문서 Q&A

Spring Initializr 의존성과 Spring Boot 버전을 고르면, **그 버전의 공식 문서를 근거로** 답하고 근거 문서를 함께 보여주는 RAG 서비스.

같은 질문이라도 버전에 따라 답이 달라진다. 예를 들어 Kafka의 JSON 역직렬화 클래스는 3.5에서 `JsonDeserializer`, 4.0에서 `JacksonJsonDeserializer`다. 근거 없이 답하는 LLM은 4.0 질문에도 3.x 지식으로 답한다 ([RAG 전후 비교](docs/rag-comparison.md)).

## 기능

| 기능 | 설명 |
|---|---|
| 버전별 질의응답 | 의존성 204개 × Boot 4.1.x / 4.0.x / 3.5.x / 3.4.x. 질문 시점에 필요한 문서만 수집·색인하고, 답변에 `[근거 N]`을 붙여 인용한 근거만 원문 링크와 함께 표시 |
| 버전 맞춤 사용 가이드 | 의존성 선언(Gradle·Maven), 핵심 설정 속성, import를 근거와 함께 정리. 4.x는 Initializr의 버전별 좌표 사용 |
| 조건 기반 탐색 | "메시징 큐에 쓸 수 있는 의존성"처럼 자연어 조건으로 의존성을 찾아 이유와 함께 카드로 제시, 카드에서 바로 대화로 이동 |
| 일반 지식 답변 (선택) | 문서에 답이 없을 때 버튼을 누르면 LLM 일반 지식으로 답하고, "문서 근거 없음"으로 구분해 표시. 문서 기반 답변은 그대로 둔다 |
| 진행 상태·안내 | 수집·색인·생성 단계를 실시간 표시 (SSE). 키 없음, 색인 없음, 문서 근거 없음 안내 |

출처: Spring Boot 레퍼런스 문서(spring-boot 저장소), springdoc-openapi 문서(3.x·2.x 판), Spring Data JDBC·R2DBC 문서(spring-data-relational·commons, Boot 버전별 판), Initializr 메타데이터. 이용 조건은 [requirements.md 1.1](docs/requirements.md).

## 실행 (Windows)

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env                          # GMS_KEY 입력
.venv\Scripts\python -m scripts.build_items     # 항목 204건 색인
.venv\Scripts\python -m scripts.fetch_docs      # 문서 원문 수집 (첫 실행 약 10분)
.venv\Scripts\uvicorn server:app                # http://127.0.0.1:8000
```

- 시스템 Python이 아니라 `.venv`의 Python·uvicorn을 쓴다 (명세 버전으로 고정한 패키지가 venv에만 있다).
- 서버는 기본으로 이 PC(127.0.0.1)에서만 열린다. 다른 사람이 접속하면 그 질문이 GMS 키로 호출된다.
- 설정(청크, Top-k, 검색 방식, 모델)은 `config.toml`에서 바꾼다.

## 구조

의존은 `server.py → services → rag → data_prep, vector_store` 한 방향이다.

| 경로 | 책임 |
|---|---|
| `server.py` | FastAPI. `/api/status`, `/api/items`, `/api/docs-count`, `/api/ask`·`/api/guide`(SSE), `/api/explore`, 화면 제공 |
| `web/` | HTML·CSS·JS 화면 |
| `services/` | 버전 맞춤 사용 가이드, 조건 기반 탐색 |
| `rag/` | 프롬프트, 질문 시점 수집(검색어 추출 → 후보 → 선별 → 색인), LangGraph retrieve → generate |
| `vector_store/` | ChromaDB 컬렉션(`items`, `docs`), 청킹 |
| `data_prep/` | 외부 출처: Initializr, spring-boot 문서, 외부 문서(springdoc, Spring Data) |
| `scripts/` | 배치(`build_items`, `fetch_docs`)와 비교·검증(`compare_search`, `compare_rag`, `verify`) |

## 문서

| 문서 | 내용 |
|---|---|
| [docs/requirements.md](docs/requirements.md) | 요구사항 정의서 |
| [docs/rag-design.md](docs/rag-design.md) | RAG 파이프라인 설계, 설정값 비교, 겪은 문제 |
| [docs/rag-comparison.md](docs/rag-comparison.md) | RAG 전후 비교 (F2015) |
| [docs/verification.md](docs/verification.md) | 명세 4장 검증 결과 (`python -m scripts.verify`) |
