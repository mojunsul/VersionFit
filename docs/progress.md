# 진행 상황 (에이전트 인수인계용)

마지막 갱신: 2026-10-21 (1일차)

## 1. 요구사항별 상태

| 번호 | 내용 | 상태 | 위치 / 메모 |
|---|---|---|---|
| F2001 | 항목 메타데이터 적재 | 완료 | `data_prep/initializr.py` → `data/items.json` (204건) |
| F2002 | 메타데이터 색인 | 완료 | `scripts/build_items.py`, 두 번 실행해도 204건 유지 확인 |
| F2003 | 검색어 추출(프롬프트1) | 미착수 | 다음 작업 |
| F2004 | 외부 문서 수집(프롬프트2) | 일부 | 원문 수집·정리·후보 검색 완료 (`data_prep/boot_docs.py`, `scripts/fetch_docs.py`). 프롬프트2 미착수 |
| F2005 | 외부 문서 색인 | 일부 | 청킹 완료 (`vector_store/chunking.py`). `docs` 컬렉션 저장 미착수 |
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
| 후보 검색: 로컬 원문 사본에서 검색어의 경로·본문 출현 횟수(경로 가중 20배)로 후보 → 프롬프트2 선별 | 경로만으로는 개념 검색어(`jackson`, `jpa`)가 0건 (4.2). F2004의 "출처에서 검색해 후보를 모은다"를 충족 |
| 수집 방식: 원문은 배치(`scripts/fetch_docs.py`)로 1회 수집해 `data/boot_docs/`에 보관, 청킹·색인은 질문 시점 + 캐시, 대표 항목은 사전 색인으로 워밍업 | F2004, NF2002와 검증 4.2("같은 질문 재수집 안 함")가 질문 시점 수집을 전제. 서비스는 외부 호출 없이 로컬 사본만 읽음 (사용자 확인 2026-10-21) |
| 수집 캐시: 별도 파일 없이 `docs` 청크 메타데이터 `(item_id, boot_version, query)`로 조회 | 메타데이터에 이미 있는 값 |
| 청킹 직접 구현 (헤더 경로 접두, 문단·구분자 블록 단위) | langchain-text-splitters에 AsciiDoc 헤더 분할기가 없고, 글자 수 분할기는 코드 블록을 자른다 |
| 디렉터리: 배치는 `scripts/`, 의존 방향 `app → services → rag → data_prep, vector_store` | 사용자 요청으로 루트 정리 (CLAUDE.md 구조 표) |
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
  - 모듈은 위 경로의 `.../antora/modules/{모듈}/pages`로, 4개 버전 모두 같은 기본 경로 아래에 있다. how-to 28개, specification 11개, appendix 8개, ROOT 7개 (버전 공통). actuator API 문서(`api`)와 빌드 플러그인 문서는 다른 경로에 있다.
  - Initializr 링크 73건(고유 31개)의 모듈 분포: reference 66, how-to 6(`batch`, `data-access`, `data-initialization`), specification 1(`configuration-metadata/annotation-processor`). 31개 모두 4개 버전에서 `{모듈}/pages/{경로}.adoc`로 존재 → 수집 대상 모듈: reference, how-to, specification.
- 목록: `GET https://api.github.com/repos/spring-projects/spring-boot/git/trees/{branch}?recursive=1` (truncated 아님). 본문: `https://raw.githubusercontent.com/spring-projects/spring-boot/{branch}/{path}`.
- GitHub API 인증 없이 시간당 60회 (IP 공유). Trees는 버전당 1회면 충분, 본문은 raw로 받는다.
- 원문 링크: `https://docs.spring.io/spring-boot/{major.minor}/{모듈}/<page>.html` — 4.0, 3.5, 3.4는 200, 4.1은 302(최신으로 리다이렉트). how-to(3.4/3.5/4.0), specification(4.0)도 같은 규칙으로 200 확인. `x.y.z`는 301. docs.spring.io robots.txt: crawl-delay 1.
- 라이선스: spring-boot, start.spring.io 저장소 모두 Apache-2.0. start.spring.io에 별도 API 약관·robots.txt 없음(404).
- AsciiDoc에 `[[anchor]]`, `:attr:` 줄, `include::`, `javadoc:...[]` 매크로, `----` 코드 블록이 있다. 코드 블록 안의 `=` 줄은 헤더가 아니다.
  - 실제 본문 확인 (kafka 3.5/4.0, how-to/batch 4.0, features/json 3.5): `:attr:` 줄과 `include::`는 0건. 많은 순서: `javadoc:패키지.클래스[]`(23~33건), `[[anchor]]`(6건), `xref:[모듈:]경로.adoc#앵커[표시문]`(표시문이 빈 경우 있음), `configprop:spring.kafka...[]`, `[configprops,yaml]` 코드 블록 표시, `include-code::MyBean[]`.
  - **`javadoc:`는 패키지 전체 이름을 남겨야 한다.** 대표 질문 1의 답(`KafkaProperties` 패키지)이 `javadoc:org.springframework.boot.kafka.autoconfigure.KafkaProperties[]` 안에만 있다.
  - `include-code::`는 Java 예제를 별도 소스 파일에서 끼워 넣는다. adoc만 받으면 예제 코드가 빠진다 (kafka 5건, json 2건).
- Trees 경로 매칭 (4.0.x, 3개 모듈 127개 문서): `kafka`, `json`, `pulsar`, `security`, `messaging`은 경로에 걸린다. `jackson`, `deserializer`, `serialization`, `jpa`, `datasource`, `login`은 0건 → 경로만으로는 개념 검색어 후보가 안 나온다.
- 원문 수집 결과 (`scripts/fetch_docs.py`, 3개 모듈): 4.1.x 128건, 4.0.x 124건, 3.5.x 122건, 3.4.x 122건, 버전당 약 1MB. API 호출은 버전당 Trees 1회.
  - 정리 후 남은 매크로는 `https:` 링크(`url[표시문]` 형식, 그대로 둠), `reference:partial$...[]` 3건뿐. `javadoc:`에는 `{url-...-javadoc}/` 접두사와 `Class#method(...)` 형식도 있어 처리함.
  - 본문 검색 후보 (4개 버전 동일): `jackson` → `how-to/spring-mvc`, `features/json` 등, `jpa`+`datasource` → `how-to/data-access`, `data/sql` 등, `kafka`+`json deserializer` → `messaging/kafka` 1위.
- 청킹 (4.0.x 124건, size 1000/overlap 200): 청크 1583개, 평균 694자, 중앙 736자, 최대 4412자. 1000자 초과 22건은 모두 코드·표 블록(자르지 않음).
- 3.5 vs 4.0 문서 차이 예 (대표 질문 근거): kafka(`JsonDeserializer`→`JacksonJsonDeserializer`, `KafkaProperties` 패키지 이동), pulsar(리액티브 스타터 섹션 삭제), features/json(`com.fasterxml`→`tools.jackson`).

## 4. 알려진 문제

### 4.1 한국어 조건 검색이 약함 (F2011)
항목 설명이 영어라 "메시징 큐에 쓸 수 있는 의존성"은 상위 30위 안에 Kafka/RabbitMQ가 없다. "message queue"는 RabbitMQ 1위. "데이터베이스에 접근하는 JPA", "보안 로그인 인증"은 정상.
대응 계획(미검증): 조건을 LLM으로 영어 검색어로 바꿔 검색 → 후보 30개 → LLM이 조건에 맞는 항목만 선별.

### 4.2 경로 매칭만으로는 후보가 부족함 (F2004)
해결: 원문 사본의 본문 검색으로 변경 (2절). 대표 질문 3의 `jackson`이 `features/json.adoc`을 2위로 찾는다.

### 4.3 남은 한계
- `include-code::` 예제 코드는 adoc에 없어 색인되지 않는다. F2010(import 예시)에서 필요하면 검토.
- 크기를 넘는 코드·표 청크(최대 4412자)는 통째로 임베딩된다. 검색 품질은 F2006에서 확인.

### 4.4 공유 문서 중복
여러 항목이 같은 Boot 문서를 수집하면 청크 ID(`항목ID:버전:문서ID:순번`) 때문에 항목별로 중복 저장된다. 명세 요구(덮어쓰지 않기)대로이며 용량만 늘어난다.

## 5. 다음 작업 (순서대로)

1. F2003~F2005 나머지: `rag/prompts.py`, `rag/collect.py`
   - 완료: 원문 수집·정리·후보 검색(`data_prep/boot_docs.py`), 청킹(`vector_store/chunking.py`)
   - 프롬프트1: 항목·질문 → 검색어 JSON 배열 (항목 이름 항상 포함). 한국어 질문도 영어 검색어로 (원문이 영어)
   - 캐시: `docs` 메타데이터 `(item_id, boot_version, query)` 조회 → 있으면 건너뜀
   - 후보: `boot_docs.search(load_docs(v), terms, N)` → 프롬프트2(제목·경로만 보여주고 선택) → `doc_id_for_item(doc_url)` 문서는 항상 포함. 후보 수 N은 `config.toml`에 추가
   - 색인: `chunk()` 결과에 docs/rag-design.md 2절 메타데이터를 붙여 `docs` 컬렉션에 저장
2. F2006~F2008 `rag/`: LangGraph retrieve/generate, 근거 병합·중복 제거, 출처 유형 구분
3. F2009~F2012 `app.py`: 항목+버전 선택, 대화 분리, 진행 상태, 안내 문구
4. F2010, F2011 `services/`
5. 심화 F2014, F2015 → 검증(명세 4장) → 설계문서·README 보완

## 6. 커밋 이력 요약
- 기획 문서 → 라이브러리 버전·설정 → items 색인 (F2001, F2002)
- 디렉터리 정리(scripts/) → 문서 원문 수집·후보 검색 (F2004) → 청킹 (F2005) → javadoc 매크로 보완
