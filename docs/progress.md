# 진행 상황 (에이전트 인수인계용)

마지막 갱신: 2026-10-21 (1일차)

## 1. 요구사항별 상태

| 번호 | 내용 | 상태 | 위치 / 메모 |
|---|---|---|---|
| F2001 | 항목 메타데이터 적재 | 완료 | `data_prep/initializr.py` → `data/items.json` (204건) |
| F2002 | 메타데이터 색인 | 완료 | `build_items.py`, 두 번 실행해도 204건 유지 확인 |
| F2003 | 검색어 추출(프롬프트1) | 미착수 | 다음 작업 |
| F2004 | 외부 문서 수집(프롬프트2) | 미착수 | 다음 작업 |
| F2005 | 외부 문서 색인 | 미착수 | 다음 작업 |
| F2006 | 근거 검색·병합 | 미착수 | |
| F2007 | LangGraph 답변 생성 | 미착수 | |
| F2008 | 근거 표시 | 일부 | `app.py`의 `cited_sources`/`render_sources` 재사용 예정 |
| F2009 | 항목·버전 선택, 대화 분리 | 미착수 | 대화 기록 키 = (항목, 버전) |
| F2010 | 특화 기능: 버전 맞춤 사용 가이드 | 미착수 | |
| F2011 | 조건 기반 항목 탐색 | 미착수 | 아래 4.1 문제 반영 필요 |
| F2012 | 진행 상태·안내 | 미착수 | 색인 0건, GMS_KEY 누락, 검색 결과 없음 |
| F2014 | 심화: MMR | 미착수 | 선택함 |
| F2015 | 심화: RAG 전후 비교 | 미착수 | 선택함 |
| F2013, F2016 | 심화 | 보류 | |

1일차 마감(도메인 확정, 16시)용 요구사항 정의서는 작성 완료. RAG 설계문서는 초안이며 구현하면서 채운다 (값 변경 비교, 겪은 문제).

## 2. 확정된 결정과 이유

| 결정 | 이유 |
|---|---|
| 도메인: Spring Initializr 의존성(항목) × Spring Boot 버전 | 사용자 선택. 버전별 문서 차이로 근거가 필요한 질문이 성립 |
| 지원 버전: 4.1.x, 4.0.x, 3.5.x, 3.4.x | 문서 경로 패턴이 두 가지뿐(아래 3). 3.2~3.3은 설정 추가로 확장 가능, 3.1 이하·2.x는 구형 AsciiDoc이라 제외 |
| 외부 문서: spring-boot 저장소 AsciiDoc을 GitHub API로 수집 | docs.spring.io에는 검색 API가 없음. 명세가 허용하는 "도메인별 공개 API"이고, HTML 노이즈가 없고 Apache-2.0 |
| 후보 검색: Trees API 파일 목록에서 경로·제목이 검색어와 맞는 문서 → 프롬프트2 선별 | F2004의 "출처에서 검색해 후보를 모은다"를 충족 |
| 수집 방식: 질문 시점 수집 + 캐시, 대표 항목은 사전 색인으로 워밍업 | F2004, NF2002와 검증 4.2("같은 질문 재수집 안 함")가 질문 시점 수집을 전제 |
| UI: Streamlit (`app.py` 이어 쓰기) | 명세 기본. HTML 프론트(F2013)는 심화라 보류 |
| Vector DB: ChromaDB, 컬렉션 `items`/`docs` | 명세 필수 라이브러리 |
| 임베딩: `text-embedding-3-small` (GMS), 답변: `gpt-5.4-nano` | GMS에서 임베딩 동작 확인 (1536차원) |
| 설정 파일: `config.toml` (tomllib) | 의존성 추가 없이 읽음 |
| 위험 도메인 아님, 면책 문구 없음 | |

## 3. 직접 확인한 사실 (2026-10-21)

- Initializr `https://start.spring.io/metadata/client` (헤더 `Accept: application/json`): 의존성 204건, 23개 그룹, 188건에 `_links` 있음. `reference` 링크 중 73건이 `https://docs.spring.io/spring-boot/{bootVersion}/...` 템플릿.
  - 예: kafka → `.../{bootVersion}/reference/messaging/kafka.html`, web → `.../reference/web/servlet.html`, batch → `.../how-to/batch.html`
- spring-boot 저장소 문서 경로 (Antora, `pages` 아래 `.adoc`):
  - 4.0.x, 4.1.x: `documentation/spring-boot-docs/src/docs/antora/modules/reference/pages`
  - 3.2.x~3.5.x: `spring-boot-project/spring-boot-docs/src/docs/antora/modules/reference/pages`
  - 3.1.x 이하: `spring-boot-project/spring-boot-docs/src/docs/asciidoc` (미지원)
  - reference 모듈 파일 수: 4.1.x 89개, 4.0.x 85개, 3.5.x 83개, 3.4.x 83개 (각 약 0.8~0.9MB)
  - **미확인**: `how-to` 등 reference 외 모듈(`modules/how-to/pages`)의 경로와 포함 여부. batch처럼 how-to를 가리키는 항목이 있으므로 확인 필요.
- 목록: `GET https://api.github.com/repos/spring-projects/spring-boot/git/trees/{branch}?recursive=1` (truncated 아님). 본문: `https://raw.githubusercontent.com/spring-projects/spring-boot/{branch}/{path}`.
- GitHub API 인증 없이 시간당 60회 (IP 공유). Trees는 버전당 1회면 충분, 본문은 raw로 받는다.
- 원문 링크: `https://docs.spring.io/spring-boot/{major.minor}/reference/<page>.html` — 4.0, 3.5는 200, 4.1은 302(최신으로 리다이렉트). `x.y.z`는 301. docs.spring.io robots.txt: crawl-delay 1.
- 라이선스: spring-boot, start.spring.io 저장소 모두 Apache-2.0. start.spring.io에 별도 API 약관·robots.txt 없음(404).
- AsciiDoc에 `[[anchor]]`, `:attr:` 줄, `include::`, `javadoc:...[]` 매크로, `----` 코드 블록이 있다. 코드 블록 안의 `=` 줄은 헤더가 아니다.
- 3.5 vs 4.0 문서 차이 예 (대표 질문 근거): kafka(`JsonDeserializer`→`JacksonJsonDeserializer`, `KafkaProperties` 패키지 이동), pulsar(리액티브 스타터 섹션 삭제), features/json(`com.fasterxml`→`tools.jackson`).

## 4. 알려진 문제

### 4.1 한국어 조건 검색이 약함 (F2011)
항목 설명이 영어라 "메시징 큐에 쓸 수 있는 의존성"은 상위 30위 안에 Kafka/RabbitMQ가 없다. "message queue"는 RabbitMQ 1위. "데이터베이스에 접근하는 JPA", "보안 로그인 인증"은 정상.
대응 계획(미검증): 조건을 LLM으로 영어 검색어로 바꿔 검색 → 후보 30개 → LLM이 조건에 맞는 항목만 선별.

### 4.2 공유 문서 중복
여러 항목이 같은 Boot 문서를 수집하면 청크 ID(`항목ID:버전:문서ID:순번`) 때문에 항목별로 중복 저장된다. 명세 요구(덮어쓰지 않기)대로이며 용량만 늘어난다.

## 5. 다음 작업 (순서대로)

1. F2003~F2005 외부 문서 파이프라인 (`data_prep/boot_docs.py`, `vector_store/`, 색인 스크립트)
   - 버전별 경로 표를 `data_prep`에 두고, how-to 모듈 포함 여부부터 확인
   - 프롬프트1: 항목·질문 → 검색어 JSON 배열 (항목 이름 항상 포함)
   - 캐시: (item_id, boot_version, query) 수집 이력 저장 → 재수집 방지
   - 후보: Trees 목록에서 검색어 매칭 → 프롬프트2(제목·경로만 보여주고 선택) → 항목 `doc_url` 문서는 항상 포함
   - 청킹: 헤더 단위 후 `config.toml`의 size/overlap, 코드 블록 보존 (`langchain-text-splitters` 사용 검토)
   - 메타데이터: docs/rag-design.md 2절
2. F2006~F2008 `rag/`: LangGraph retrieve/generate, 근거 병합·중복 제거, 출처 유형 구분
3. F2009~F2012 `app.py`: 항목+버전 선택, 대화 분리, 진행 상태, 안내 문구
4. F2010, F2011 `services/`
5. 심화 F2014, F2015 → 검증(명세 4장) → 설계문서·README 보완

## 6. 커밋 이력 요약
- 기획 문서 → 라이브러리 버전·설정 → items 색인 (F2001, F2002)
