# 버전핏 — 내 Spring Boot 버전에 맞는 공식 문서 Q&A

Spring Initializr 의존성과 Spring Boot 버전을 고르면, **그 버전의 공식 문서를 근거로** 답하고 근거 문서를 함께 보여주는 RAG 서비스.

같은 질문이라도 버전에 따라 답이 달라진다. 예를 들어 Kafka의 JSON 역직렬화 클래스는 3.5에서 `JsonDeserializer`, 4.0에서 `JacksonJsonDeserializer`다. 근거 없이 답하는 LLM은 4.0 질문에도 3.x 지식으로 답한다 ([RAG 전후 비교](docs/rag-comparison.md)).

## 기능

| 구분 | 기능 | 설명 |
|---|---|---|
| 필수 | 버전별 질의응답 (F2001~F2009) | 의존성 204개 × Boot 4.1.x / 4.0.x / 3.5.x / 3.4.x. 질문 시점에 필요한 문서만 수집·색인하고, 답변에 `[근거 N]`을 붙여 인용한 근거만 원문 링크와 함께 표시 |
| 필수 | 버전 맞춤 사용 가이드 (F2010, 도메인 특화) | 의존성 선언(Gradle·Maven), 핵심 설정 속성, import를 근거와 함께 정리. 4.x는 Initializr의 버전별 좌표 사용 |
| 필수 | 조건 기반 탐색 (F2011) | "메시징 큐에 쓸 수 있는 의존성"처럼 자연어 조건으로 의존성을 찾아 이유와 함께 카드로 제시, 카드에서 바로 대화로 이동 |
| 필수 | 진행 상태·안내 (F2012) | 수집·색인·생성 단계를 실시간 표시 (SSE). 키 없음, 색인 없음, 문서 근거 없음 안내 |
| 심화 | 프론트엔드 직접 구현 (F2013) | FastAPI + HTML·CSS·JS, 진행 상태 SSE, (항목, 버전)별 대화 저장 |
| 심화 | MMR 검색 (F2014) | 비슷한 섹션 반복을 줄이는 MMR을 기본 검색으로, 유사도 검색과 비교 |
| 심화 | RAG 전후 비교 (F2015) | 대표 질문을 LLM만 / RAG로 답해 사실 정확성·근거 제시·모름 응답 비교 |
| 심화 | 프로젝트 문서 결합 (F2016) | 자주 쓰는 13개 의존성은 Spring Boot 문서에 더해 그 프로젝트의 공식 문서(Spring Data, Security, Kafka 등)를 Boot 버전에 맞는 판으로 함께 근거로 쓴다 ([효과 비교](docs/rag-comparison.md)) |
| 추가 | 일반 지식 답변 | 문서에 답이 없을 때 버튼을 누르면 LLM 일반 지식으로 답하고, "문서 근거 없음"으로 구분해 표시. 문서 기반 답변은 그대로 둔다 |

출처와 라이선스는 [아래 절](#출처와-라이선스), 수집 시 확인한 이용 조건은 [requirements.md 1.1](docs/requirements.md).

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

## 데이터 준비와 색인

1. **항목 색인** (`scripts.build_items`): Initializr 메타데이터 API에서 의존성 204건을 받아 `data/items.json`에 저장하고, 항목마다 "이름·id·분류·설명·문서 링크" 텍스트 1청크로 `items` 컬렉션에 색인한다 (청크 ID = 항목 id라 다시 실행해도 늘지 않는다).
2. **문서 원문 수집** (`scripts.fetch_docs`): GitHub에서 Boot 버전별 Spring Boot 레퍼런스 문서(`data/boot_docs/`)와 13개 항목의 프로젝트 문서(`data/external_docs/`)를 받는다. 1초 간격, 이미 받은 파일은 건너뛴다.
3. **질문 시점 수집·색인**: 질문이 오면 검색어 추출(프롬프트1) → 원문 사본에서 후보 10개 → 후보 선별(프롬프트2, 최대 3개 + 항목 자체 문서) → 헤더 단위 청킹 → `docs` 컬렉션 색인. 같은 질문과 검색어는 `data/collect_log.json` 캐시로 다시 수집하지 않는다.
4. **답변**: LangGraph `retrieve`(항목 정보 + 질문별 문서 근거) → `generate`(근거 기반 답변, `[근거 N]`).

자세한 흐름은 [RAG 파이프라인 설계문서](docs/rag-design.md) 3~4절.

## 심화 기능 적용 요약

| 번호 | 기능 | 적용 내용 | 결과 |
|---|---|---|---|
| F2013 | 프론트엔드 직접 구현 | FastAPI(`server.py`) + HTML·CSS·JS(`web/`), 진행 상태는 SSE | 화면 캡처 ([검증 결과](docs/verification.md)) |
| F2014 | MMR 검색 | 기본 검색 방식 MMR (fetch_k 30, lambda_mult 0.6) | 유사도 검색과 비교 ([설계문서 6.1](docs/rag-design.md)) |
| F2015 | RAG 전후 비교 | 대표 질문 6개를 LLM만 / RAG로 답해 3개 기준 비교 | 사실 정확성 2/5 → 5/5, 근거 0/5 → 5/5, 모름 0/2 → 2/2 ([비교](docs/rag-comparison.md)) |
| F2016 | 여러 문서 출처 결합 | Spring Boot 문서 + 13개 항목의 프로젝트 문서, 근거에 출처 종류·판 표시 | 13개 질문 중 10개 개선 ([비교 4절](docs/rag-comparison.md)) |

## 구조

의존은 `server.py → services → rag → data_prep, vector_store` 한 방향이다.

| 경로 | 책임 |
|---|---|
| `server.py` | FastAPI. `/api/status`, `/api/items`, `/api/docs-count`, `/api/ask`·`/api/guide`(SSE), `/api/explore`, `/api/general`(일반 지식 답변), 화면 제공 |
| `web/` | HTML·CSS·JS 화면 |
| `services/` | 버전 맞춤 사용 가이드, 조건 기반 탐색 |
| `rag/` | 프롬프트, 질문 시점 수집(검색어 추출 → 후보 → 선별 → 색인), LangGraph retrieve → generate |
| `vector_store/` | ChromaDB 컬렉션(`items`, `docs`), 청킹 |
| `data_prep/` | 외부 출처: Initializr, spring-boot 문서, 프로젝트 문서(springdoc, Spring Data, Security, Kafka, AMQP, Batch, Session) |
| `scripts/` | 배치(`build_items`, `fetch_docs`)와 비교·검증(`compare_search`, `compare_rag`, `compare_sources`, `verify`) |

## 출처와 라이선스

답변 근거는 아래 공개 저장소의 문서를 Boot 버전에 맞는 브랜치에서 받아 쓴다. 모두 [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)이며, 저작권은 각 저장소의 원저작자에게 있다.

| 출처 | 저장소 | 쓰는 곳 |
|---|---|---|
| Spring Boot 레퍼런스 문서 | [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 모든 의존성의 기본 근거 |
| Spring Data JDBC·R2DBC | [spring-projects/spring-data-relational](https://github.com/spring-projects/spring-data-relational) | data-jdbc, data-r2dbc |
| Spring Data 공통 문서 | [spring-projects/spring-data-commons](https://github.com/spring-projects/spring-data-commons) | Spring Data 문서가 include하는 페이지 |
| Spring Data JPA | [spring-projects/spring-data-jpa](https://github.com/spring-projects/spring-data-jpa) | data-jpa |
| Spring Data Redis | [spring-projects/spring-data-redis](https://github.com/spring-projects/spring-data-redis) | data-redis |
| Spring Data MongoDB | [spring-projects/spring-data-mongodb](https://github.com/spring-projects/spring-data-mongodb) | data-mongodb |
| Spring Data Elasticsearch | [spring-projects/spring-data-elasticsearch](https://github.com/spring-projects/spring-data-elasticsearch) | data-elasticsearch |
| Spring Security | [spring-projects/spring-security](https://github.com/spring-projects/spring-security) | security, oauth2-client |
| Spring for Apache Kafka | [spring-projects/spring-kafka](https://github.com/spring-projects/spring-kafka) | kafka |
| Spring AMQP | [spring-projects/spring-amqp](https://github.com/spring-projects/spring-amqp) | rabbitmq |
| Spring Batch | [spring-projects/spring-batch](https://github.com/spring-projects/spring-batch) | batch |
| Spring Session | [spring-projects/spring-session](https://github.com/spring-projects/spring-session) | session-data-redis |
| springdoc-openapi 문서 | [springdoc/springdoc.github.io](https://github.com/springdoc/springdoc.github.io) | springdoc-openapi |
| Initializr 메타데이터 | [start.spring.io](https://start.spring.io) ([spring-io/start.spring.io](https://github.com/spring-io/start.spring.io)) | 의존성 목록, 버전별 좌표 |

- **수정 고지**: 원문 AsciiDoc을 그대로 보여 주지 않는다. 매크로(`javadoc:`, `xref:` 등)를 글로 바꾸고, include와 조건 블록을 풀고, 헤더 단위로 잘라(청크) 답변 근거로 일부만 보여 준다. 근거마다 원문 링크를 붙인다.
- 원문 사본(`data/boot_docs/`, `data/external_docs/`)은 저장소에 포함하지 않는다. `python -m scripts.fetch_docs`로 각자 받는다.
- 확인한 저장소에는 NOTICE 파일이 없다 (2026-10-22).

## 문서

| 문서 | 내용 |
|---|---|
| [docs/requirements.md](docs/requirements.md) | 요구사항 정의서 |
| [docs/rag-design.md](docs/rag-design.md) | RAG 파이프라인 설계, 설정값 비교, 겪은 문제 |
| [docs/rag-comparison.md](docs/rag-comparison.md) | RAG 전후 비교 (F2015), 외부 문서 추가 효과 |
| [docs/verification.md](docs/verification.md) | 명세 4장 검증 결과 (`python -m scripts.verify`, 출력 전문 [verify-output.md](docs/verify-output.md)) |
