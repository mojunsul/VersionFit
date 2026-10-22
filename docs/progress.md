# 진행 상황 (에이전트 인수인계용)

마지막 갱신: 2026-10-21 (1일차)

## 1. 요구사항별 상태

| 번호 | 내용 | 상태 | 위치 / 메모 |
|---|---|---|---|
| F2001 | 항목 메타데이터 적재 | 완료 | `data_prep/initializr.py` → `data/items.json` (204건) |
| F2002 | 메타데이터 색인 | 완료 | `scripts/build_items.py`, 두 번 실행해도 204건 유지 확인 |
| F2003 | 검색어 추출(프롬프트1) | 완료 | `rag/prompts.py` `SEARCH_TERMS`, `rag/collect.py` `extract_terms` |
| F2004 | 외부 문서 수집(프롬프트2) | 완료 | 원문 `data_prep/boot_docs.py`, `scripts/fetch_docs.py` / 선별·캐시 `rag/collect.py` |
| F2005 | 외부 문서 색인 | 완료 | `vector_store/chunking.py`, `rag/collect.py` `collect()` |
| F2006 | 근거 검색·병합 | 완료 | `rag/graph.py` `retrieve` (items 항목 청크 항상 + docs 항목·버전 필터 검색, 중복 제거) |
| F2007 | LangGraph 답변 생성 | 완료 | `rag/graph.py` `generate`, `answer()`. 아래 4.3 답변 품질 한계 |
| F2008 | 근거 표시 | 완료 | `web/app.js` `citedSources`/`renderSources` |
| F2009 | 항목·버전 선택, 대화 분리 | 완료 | `web/` 사이드바, localStorage `chat:{항목}|{버전}` |
| F2010 | 특화 기능: 버전 맞춤 사용 가이드 | 완료 | `services/guide.py`, `data_prep/initializr.py` `fetch_coordinates`, 사이드바 버튼. 4.x는 Initializr 좌표 근거 추가, 3.x는 문서만 |
| F2011 | 조건 기반 항목 탐색 | 완료 | `services/explore.py`, `POST /api/explore`, `web/` 카드 → 해당 항목 대화 이동 |
| F2012 | 진행 상태·안내 | 완료 | `collect(on_step=)` → `server.py` SSE `step` → 화면 진행 박스. 키 누락·items 0건·원문 없음·문서 근거 없음(`no_docs_notice`)·오류 안내 |
| F2014 | 심화: MMR | 완료 | 기본 검색 방식 mmr, lambda_mult 0.6 (`config.toml`), 비교 `scripts/compare_search.py` → rag-design.md 6.1 |
| F2015 | 심화: RAG 전후 비교 | 완료 | `docs/rag-comparison.md`, `scripts/compare_rag.py` (mini, 6문항) |
| F2016 | 심화: 여러 문서 출처 결합 | 일부 | springdoc-openapi 문서 추가 (`data_prep/external_docs.py`). 다른 외부 문서는 미착수 |
| F2013 | 심화: HTML 프론트 | 완료 | `server.py` + `web/` (Streamlit `app.py` 삭제) |

1일차 마감(도메인 확정, 16시)용 요구사항 정의서는 작성 완료. RAG 설계문서는 초안이며 구현하면서 채운다 (값 변경 비교, 겪은 문제).

## 2. 확정된 결정과 이유

| 결정 | 이유 |
|---|---|
| 도메인: Spring Initializr 의존성(항목) × Spring Boot 버전 | 사용자 선택. 버전별 문서 차이로 근거가 필요한 질문이 성립 |
| 지원 버전: 4.1.x, 4.0.x, 3.5.x, 3.4.x | 문서 경로 패턴이 두 가지뿐(아래 3). 3.2~3.3은 설정 추가로 확장 가능, 3.1 이하·2.x는 구형 AsciiDoc이라 제외 |
| 외부 문서: spring-boot 저장소 AsciiDoc을 GitHub API로 수집 | docs.spring.io에는 검색 API가 없음. 명세가 허용하는 "도메인별 공개 API"이고, HTML 노이즈가 없고 Apache-2.0 |
| 후보 검색: 로컬 원문 사본에서 검색어의 경로·본문 출현 횟수(경로 가중 20배)로 후보 → 프롬프트2 선별 | 경로만으로는 개념 검색어(`jackson`, `jpa`)가 0건 (4.2). F2004의 "출처에서 검색해 후보를 모은다"를 충족 |
| 수집 방식: 원문은 배치(`scripts/fetch_docs.py`)로 1회 수집해 `data/boot_docs/`에 보관, 청킹·색인은 질문 시점 + 캐시, 대표 항목은 사전 색인으로 워밍업 | F2004, NF2002와 검증 4.2("같은 질문 재수집 안 함")가 질문 시점 수집을 전제. 서비스는 외부 호출 없이 로컬 사본만 읽음 (사용자 확인 2026-10-21) |
| 수집 캐시: `data/collect_log.json`에 `(항목, 버전, 검색어)` → 선택 문서, `(항목, 버전, 질문)` → 검색어. 문서 중복은 Chroma 메타데이터로 확인 | 새 문서를 못 만든 검색어도 기록해야 함. 프롬프트1은 같은 질문에도 다른 검색어를 내서 질문별 검색어도 캐시 (3절) |
| 청킹 직접 구현 (헤더 경로 접두, 문단·구분자 블록 단위) | langchain-text-splitters에 AsciiDoc 헤더 분할기가 없고, 글자 수 분할기는 코드 블록을 자른다 |
| 디렉터리: 배치는 `scripts/`, 의존 방향 `app → services → rag → data_prep, vector_store` | 사용자 요청으로 루트 정리 (CLAUDE.md 구조 표) |
| UI: FastAPI(`server.py`) + HTML·CSS·JS(`web/`). Streamlit `app.py` 삭제, `requirements.txt`의 streamlit 줄은 명세 필수 목록이라 남김 (사용자 결정 2026-10-21) | 로직(`rag/`, `services/`)은 UI와 분리돼 있어 화면만 교체. fastapi==0.156.8 추가(명세 목록 밖), uvicorn==0.54.0. 기본 127.0.0.1이라 네트워크에 노출 안 됨 |
| Vector DB: ChromaDB, 컬렉션 `items`/`docs` | 명세 필수 라이브러리 |
| 임베딩: `text-embedding-3-small` (GMS), 답변: `gpt-5.4-mini` (개발 중 nano로 임시 사용 후 2026-10-22 mini로 원복) | GMS에서 임베딩 동작 확인 (1536차원). 답변 모델은 nano에서 변경 (3절 모델 비교, 4.3-1) |
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
- 질문 시점 수집 (`rag/collect.py`, kafka, 대표 질문 1, 2026-10-21): 4.0.x 첫 수집 약 6초, `messaging/kafka.adoc` 청크 11개 색인. 같은 질문 재실행 0.0초, LLM·임베딩 호출 없음. 3.5.x는 별도 11개, 버전 섞임 0. `item_id`+`boot_version` 필터 유사도 검색 1위가 `JacksonJsonDeserializer` 청크(Additional Kafka Properties).
  - 질문별 검색어 캐시 전에는 같은 질문 재실행에서 프롬프트1이 다른 검색어를 내 후보 검색·프롬프트2가 다시 호출됐다.
  - kafka는 프롬프트1 검색어가 여러 단어 구라 후보가 1~2개였지만, 답 문서가 하나라 문제없었다.
  - 대표 질문 2·3 (3.5.x/4.0.x): 후보 10개씩. pulsar 3.5.x 선택 `messaging/pulsar`+`web/reactive`, `spring-boot-starter-pulsar-reactive` 청크 1개 / 4.0.x 0개(삭제된 내용, 기대대로). web 두 버전 모두 `features/json`, `how-to/spring-mvc`, `web/servlet` 선택, 3.5.x `com.fasterxml.jackson` 10청크·`tools.jackson` 0, 4.0.x `tools.jackson` 9청크. → 단어 단위 매칭 불필요.
  - 후보 순위는 출현 횟수라 긴 문서·흔한 단어에 치우친다 (pulsar 3.5.x 1위가 `reactor`가 많은 `how-to/webserver`). 프롬프트2가 걸러 결과에는 영향 없음.
  - 질문 1회 색인 청크: kafka 11, pulsar 17~52, web 106~110.
- 답변 생성 (`rag/graph.py`, gpt-5.4-nano, 2026-10-21):
  - 근거 8건 = Initializr 1 + docs 7. 근거 번호는 모두 범위 안. pulsar 4.0.x 리액티브 스타터는 "문서에서 확인되지 않는다"(지어내지 않음), kafka에 GraphQL 질문도 "확인되지 않는다".
  - 대표 질문 1(두 물음 결합)의 `KafkaProperties` 패키지: 근거 3·6에 전체 이름이 있는데도 4번 중 1번만 답함. 나머지는 앞 물음 클래스(`JsonDeserializer`)의 패키지로 답함. 프롬프트에 "물음별로 답", "`a.b.Class`의 패키지는 `a.b`" 규칙 추가 후에도 동일.
  - 같은 물음을 따로 ("KafkaProperties 클래스의 패키지는?"): 4번 중 3번 정답 (3.5.x 1번 "확인되지 않는다").
- GMS 모델 (2026-10-21): `/models` 목록 조회는 500 에러로 미지원. 직접 호출 성공: gpt-5.4-nano, gpt-5.4-mini, gpt-5.4, gpt-5-mini, gpt-5, gpt-4.1-mini, gpt-4o-mini. 명세 PDF 영문 텍스트에 답변 모델 지정 없음 (한글은 pdftotext로 추출 안 돼 미확인).
- 모델 비교 (대표 질문 1, 버전별 2회 = 4회, 프롬프트 규칙 추가 후): nano 3/4 평균 5.2초, **mini 4/4 평균 4.3초**, gpt-5.4 4/4 평균 5.9초. mini로 바꾼 뒤 pulsar 4.0.x·GraphQL "확인되지 않는다" 확인도 통과. 표본이 작아 F2015에서 더 넓게 비교.
- 화면 (`app.py`, Streamlit AppTest, 2026-10-21): kafka·4.0.x 선택 → 사이드바 "항목 204건 · 문서 청크 11건", 질문 → 상태 "이미 색인된 문서로 답합니다", 답변에 `JacksonJsonDeserializer`·`kafka.autoconfigure`, 근거 2건 표시. 3.5.x로 바꾸면 대화 0건, 4.0.x로 돌아오면 2건 유지.
- Initializr 버전 지원 (2026-10-21): `metadata/client`의 bootVersion은 4.2.0-SNAPSHOT/M2, 4.1.2-SNAPSHOT, **4.1.1.RELEASE**, 4.0.9-SNAPSHOT, **4.0.8.RELEASE**뿐. `/dependencies?bootVersion=3.5.0|3.5.7|3.4.0|3.4.5`는 400 "Invalid Spring Boot version". `metadata/client`에 `compatibilityRange` 필드 없음.
  - `/dependencies?bootVersion=4.0.8.RELEASE` 195건, 4.1.1 183건 (items 204건 중 일부는 버전에 따라 제공 안 됨). kafka → `org.springframework.boot:spring-boot-starter-kafka`, web → `spring-boot-starter-webmvc`.
  - 4.0.x 문서 원문에는 `spring-boot-starter-kafka`가 0건 (프로젝트 이름 `spring-kafka`만). 문서만으로는 4.x 스타터 좌표를 답할 수 없어 Initializr 좌표를 근거로 추가.
- 정리 규칙 보완: `javadoc:X[format=annotation]`이 4개 버전 3567건, `[format=full]` 1건 → 표시문이 아니라 옵션이므로 `` `@X` `` / `` `X` ``로. AsciiDoc 따옴표 `"`...`"` 639건 → `"..."` (줄바꿈·중첩 25건 남음). 보완 후 `docs` 컬렉션과 수집 캐시를 지우고 재색인.
- 가이드 (`services/guide.py`): kafka 4.0.x `spring-boot-starter-kafka` [Initializr 좌표 근거], kafka 3.5.x 좌표 "문서에서 확인되지 않는다"(지어내지 않음), web 4.0.x `spring-boot-starter-webmvc`. AppTest 버튼 → 대화에 가이드·근거 7건.
- 탐색 화면 (AppTest, 2026-10-21): "메시징 큐에 쓸 수 있는 의존성" → 카드 8개(rabbitmq, kafka, ...), kafka 카드 버튼 → 사이드바 선택 kafka, 제목 Kafka로 이동, 카드 유지. 무관 조건 → 안내 문구. 폼 key와 결과 session key가 같으면(`explore`) Streamlit 예외 → 결과 key를 `explore_result`로 분리.
- springdoc-openapi 문서 (2026-10-21): 원본 `springdoc/springdoc.github.io` (Apache-2.0, 브랜치 master만), springdoc.org robots.txt `Allow: /`.
  - `src/docs/asciidoc/*.adoc` = springdoc 3.x (springdoc.org/), `src/docs/asciidoc/v2/*.adoc` = 2.x (springdoc.org/v2/, 제목 "for Spring Boot 3"), `v1/` = Boot 2용. `index.adoc`이 본문 파일을 include로 묶는다.
  - 호환표(v2 문서 FAQ 13.80): Boot 4.x ↔ 3.x, 3.5.x ↔ 2.8.x, 3.4.x ↔ 2.7.x~2.8.x. 그래서 Boot 4.0/4.1은 3.x판, 3.4/3.5는 2.x판을 쓴다.
  - `{springdoc-version}`(3.1.1), `{springdoc-version2}`(2.9.1)은 `_attributes.adoc`이 아니라 `pom.xml`의 asciidoctor 속성. v2 문서는 `{springdoc-version2}`를 쓴다. pom의 일반 속성(version 0.0.5 등)은 쓰면 안 됨.
  - 수집 결과: 3.x판 16개, 2.x판 15개 (`_` 조각·index 제외). nano로 "Swagger UI 경로" 질문: 4.1.x → `springdoc.swagger-ui.path` [3.x 문서, springdoc.org/], 3.5.x → 같은 속성 [2.x 문서, /v2/], 판 섞임 없음. 4.1.x 가이드에 설정 속성이 근거와 함께 나옴 (이전엔 "확인되지 않는다"). kafka 4.0.x 회귀 정상.
  - 4.1.x 가이드에 Initializr 좌표(3.1.0)와 문서 예시(3.1.1)가 함께 나옴. nano라 형식이 어수선함.
- 웹 서버 (FastAPI TestClient + uvicorn, 2026-10-21): status·items(204)·docs-count 정상, 잘못된 항목 404·버전 400·빈 질문 422. `/api/ask` 이벤트 step×4 → result, kafka 4.0.x `JacksonJsonDeserializer`. springdoc 4.1.x 가이드 출처에 3.x 문서 포함, htmx 가이드는 외부 문서 안내. uvicorn 실측: step이 0.5→1.8→2.9초에 하나씩 도착, result 6.0초 (버퍼링 없음). 브라우저 클릭 동작은 사용자 확인 필요.
- similarity vs MMR (2026-10-22, 5개 질문, 표는 rag-design.md 6.1): MMR이 정답 근거를 뺀 경우 0. springdoc 4.1.x 정답 순위 7→3, web 4.0.x 고유 섹션 5→7, 나머지 동일. 색인 청크가 적은 (항목, 버전)(kafka 11, pulsar 24)은 차이 없음.
- 근거 오염 (2026-10-22, 캡처 ⑤에서 발견): kafka 4.0.x 가이드가 "확인되지 않는다". 원인은 verify의 오류 시험 질문이 실제 수집을 해서 Testing 문서 105청크와 GraphQL 문서가 같은 (항목, 버전)에 쌓였고, 검색이 `@JsonTest` 섹션을 가져와 MMR이 정답 청크를 뺌. 수정: `collect`가 `doc_ids` 반환, `retrieve`는 `doc_id $in`으로 범위 제한, verify 오류 시험은 collect도 mock, 캐시 경로에서 질문별 검색어 저장 누락 수정. 결과: 정답 청크 1위, 답 `JacksonJsonDeserializer`, 가이드에 spring.kafka.* 설정. 오염 청크는 색인에 남아 있지만 다른 질문 범위에는 안 들어감.
  - 범위 제한 후 재측정: lambda_mult 0.5에서 springdoc 4.1.x 정답이 빠짐 (FAQ 한 문서 104청크, 비슷한 섹션 다수) → 0.5~0.8 비교 후 0.6 (정답 4위, similarity 7위). verify 20/20. 조건 탐색 검사는 cloud-gcp-pubsub(Google Cloud 분류) 때문에 한 번 실패 → "대부분 Messaging + 나머지도 설명이 메시징"으로 판정 변경.
- RAG 전후 비교 (2026-10-22, gpt-5.4-mini, 6문항, docs/rag-comparison.md): 사실 정확성 LLM만 2/5 → RAG 5/5, 근거 제시 0/5 → 5/5, 모름 응답 0/2 → 2/2. LLM만은 4.0 질문에 3.x 값으로 답하고(Kafka, Jackson), 사라진 리액티브 스타터를 "사용할 수 있다", 문서에 없는 브로커 힙을 "6GB"로 지어냄.
  - 단어 판정 보정: "없습니다"가 "단정할 수 없습니다"에 걸려 오판 → 모름 단어에서 제외, 틀린 주장 단어 추가. "Kafka 항목에서 GraphQL 질문"은 RAG가 Boot GraphQL 문서로 정확히 답해 모름 문항에서 제외.
- 명세 4장 검증 (2026-10-22, docs/verification.md): `python -m scripts.verify` 자동 확인 20/20 통과. 화면 증명 캡처 ①~⑦ 완료 (③은 3장, ⑤는 2장, 근거 오염 수정 후 재촬영). verification.md 미확인 항목 없음.
- 일반 지식 답변 (2026-10-22, 사용자 결정: 버튼을 눌렀을 때만 생성): Spring Data JDBC 4.0.x "join sql 작성법"이 Boot 문서만으로는 "확인되지 않는다". 답이 "확인되지 않"을 포함하거나 인용 근거가 없을 때 버튼 → `/api/general`(`rag.graph.general`, 프롬프트 `GENERAL`). F2007(문서에 없으면 확인되지 않는다)을 지키려고 문서 기반 답변과 분리해 표시. verify 21/21. 모델이 규칙과 달리 끝에 추가 도움 제안을 붙이는 경우가 있음. 명세 PDF는 한글 텍스트 추출이 안 돼 PyMuPDF(스크래치에 임시 설치)로 18~19쪽을 이미지로 읽음.
  - 검사 보정: 조건 탐색 판정을 분류 정확 일치 → 'Messaging' 포함으로 (cloud-stream 분류가 'Spring Cloud Messaging'). '항목 자체 문서 포함'은 캐시 때문에 두 번째 실행부터 selected가 비어 Chroma 색인 여부로 판정.
- 3.5 vs 4.0 문서 차이 예 (대표 질문 근거): kafka(`JsonDeserializer`→`JacksonJsonDeserializer`, `KafkaProperties` 패키지 이동), pulsar(리액티브 스타터 섹션 삭제), features/json(`com.fasterxml`→`tools.jackson`).
- Spring Data JDBC·R2DBC 외부 문서 (2026-10-22): 저장소 spring-projects/spring-data-relational(Apache-2.0), 본문 일부는 spring-data-commons(Apache-2.0) 같은 판 페이지를 include. 네 브랜치(4.1.x/4.0.x/3.5.x/3.4.x) 모두 `src/main/antora/modules/ROOT/` 같은 구조.
  - Boot ↔ Spring Data: Boot 브랜치 spring-boot-dependencies의 Spring Data Bom이 4.1.x 2026.0.2-SNAPSHOT, 4.0.x 2025.1.8-SNAPSHOT, 3.5.x 2025.0.13, 3.4.x 2024.1.13. Maven Central BOM의 spring-data-jdbc는 2026.0.1 → 4.1.1, 2025.1.7 → 4.0.7, 2025.0.13 → 3.5.13, 2024.1.13 → 3.4.13.
  - 원문 링크: docs.spring.io/spring-data/relational/reference/{4.0,3.5}/… 200, 4.1은 현재판(302 → /reference/…), 3.4는 404라 GitHub 원문으로 링크.
  - 수집 결과: data-jdbc 판별 문서 35/34/33/32, data-r2dbc 32/31/31/30 (4.1→3.4). 남은 include 0. `example$` include(빌드 때 테스트 소스에서 복사되는 예제 코드)는 저장소 문서 폴더에 없어 지움.
  - springdoc도 같은 방식으로 옮김. 본문은 그대로이고 조건 지시어 62쌍과 머리말 속성 줄만 빠짐 (전후 비교).
  - "join sql 작성법"(Spring Data JDBC): 4.1.x는 예전 질문의 검색어별 선택 캐시 때문에 새 문서를 못 봄 → `fetch_docs`가 새 파일이 생긴 출처의 선택 캐시를 지우도록 수정. 이후 근거에 "Spring Data JDBC 4.1 문서"(Query Methods, Using @Query)가 붙지만 답은 여전히 "join 작성 예시는 확인되지 않는다". 원문에도 join 예시는 없고 "쿼리 메서드 이름 파생은 join 없이 WHERE에 쓸 수 있는 속성까지만" 한 줄뿐인데, 이 문장이 든 청크가 한국어 질문 검색 15위 안에 없음. verify 21/21.
- 검색 질의에 영어 검색어 붙이기 (2026-10-22, rag-design.md 6.1-1): "join sql 작성법" 근거가 핵심 문장 청크 30위 → 9위, 근거 7개 중 Spring Data JDBC 2 → 5개, 답에 `@Query` 방법 포함. 5개 비교 질문(mmr): kafka 3,2 → 1,3, pulsar 2 → 1, web 2 → 2, springdoc 4.1.x 4 → 6, 3.5.x 3 → 4 (모두 7개 안). similarity로는 springdoc 4.1.x가 빠짐. compare_rag 판정 같음, verify 21/21.

- Spring Data 1차 4개 모듈 (2026-10-22): spring-data-jpa·redis·mongodb·elasticsearch 모두 Apache-2.0, NOTICE 없음, `src/main/antora/modules/ROOT` 구조. spring-data-bom 2026.0.1 / 2025.1.7 / 2025.0.13 / 2024.1.13 → JPA·Redis·commons 4.1/4.0/3.5/3.4, MongoDB 5.1/5.0/4.5/4.4, Elasticsearch 6.1/6.0/5.5/5.4. 문서 주소 규칙은 relational과 같음 (4.1 짝 현재판 302, 4.0·3.5 짝 200, 3.4 짝 404).
  - 판별 문서: JPA 33/33/31/31, Redis 44/41/41/41, MongoDB 55/54/52/51, Elasticsearch 30×4 (4.1→3.4). 남은 include 0.
  - 다운로드 중 GitHub API 비로그인 한도(시간당 60회) 초과 → Trees API 결과를 `.tree.json`으로 캐시 (boot_docs.github_tree).
  - 대표 질문: JPA 4.0.x @EntityGraph(근거 JPA 4.0 문서 4개), Redis 3.5.x 직렬화(Redis 3.5 문서 5개), MongoDB 4.0.x 집계(MongoDB 5.0 문서 5개), Elasticsearch 4.1.x 검색 쿼리(Elasticsearch 6.1 문서 7개). 모두 구체적인 클래스·예시로 답함. verify 21/21.
- Spring Security (2026-10-22): Boot 의존성 설정의 Spring Security 4.1.x 7.1.2-SNAPSHOT, 4.0.x 7.0.8-SNAPSHOT, 3.5.x 6.5.11, 3.4.x 6.4.13 → spring-security-bom 최신 릴리스 7.1.1/7.0.7/6.5.11/6.4.13, 브랜치 7.1.x/7.0.x/6.5.x/6.4.x. 저장소 Apache-2.0, 문서 `docs/modules/ROOT`(폴더가 깊고 하위 폴더 index.adoc에 본문). 주소 규칙은 Spring Data와 같음 (7.1 302, 7.0·6.5 200, 6.4 404).
  - 판별 문서: security 190/190/187/174, oauth2-client(OAuth2 부분만) 37/37/31/30. 남은 include 0. `{registrationId}`, `{baseUrl}`은 Spring Security의 URL 자리표시자라 그대로 둠.
  - 대표 질문: security 4.0.x "특정 경로만 인증 없이 허용"(Security 7.0 문서 6개, `requestMatchers(...).permitAll()` 예시), oauth2-client 3.5.x "구글 로그인"(Security 6.5 문서 5개, `spring.security.oauth2.client.registration.google` 설정). verify 21/21.
- 출처 표기 (2026-10-22): README "출처와 라이선스" 절(저장소 9곳, Apache-2.0, 수정 고지)과 사이드바 하단 고지 추가.

## 4. 알려진 문제

### 4.1 한국어 조건 검색이 약함 (F2011)
항목 설명이 영어라 "메시징 큐에 쓸 수 있는 의존성"은 상위 30위 안에 Kafka/RabbitMQ가 없다. "message queue"는 RabbitMQ 1위. "데이터베이스에 접근하는 JPA", "보안 로그인 인증"은 정상.
해결 (`services/explore.py`, 2026-10-21): 조건 → LLM 영어 검색 문장 → items 후보 30개 → LLM이 맞는 항목만 이유와 함께 선별.
- 한국어 직접 검색 순위 → 탐색 결과: 메시징 큐 kafka·rabbitmq 30위 밖 → 1·2위, 보안 로그인 security 3·oauth2-client 8 → 1·2위, 실시간 양방향 websocket 4 → 1위, JPA data-jpa 1 → 1위.
- 프롬프트 예시에 테스트 조건(메시징 큐→Kafka, RabbitMQ)을 넣었다가 무관한 예시(캐시→Redis)로 교체 후 재확인.
- 무관한 조건(냉장고 온도, 점심 메뉴)에서 처음엔 cache·quartz 등을 억지로 골라 "목적과 무관하면 고르지 않는다" 규칙 추가 → 6회 모두 빈 결과.

### 4.2 경로 매칭만으로는 후보가 부족함 (F2004)
해결: 원문 사본의 본문 검색으로 변경 (2절). 대표 질문 3의 `jackson`이 `features/json.adoc`을 2위로 찾는다.

### 4.3 남은 한계
- `include-code::` 예제 코드는 adoc에 없어 색인되지 않는다. F2010(import 예시)에서 필요하면 검토.
- 크기를 넘는 코드·표 청크(최대 4412자)는 통째로 임베딩된다. 검색 품질은 F2006에서 확인.

### 4.3-1 답변 모델이 복합 질문·전체 이름 해석에 약함 (F2007)
3절 답변 생성 결과. 검색은 정상이고 생성 단계 문제. 해결: 답변 모델을 `gpt-5.4-mini`로 변경 (사용자 확인, 3절 모델 비교). 대표 질문은 그대로 둔다.

### 4.3-2 3.x 의존성 좌표
Initializr가 3.x를 지원하지 않아 3.5.x/3.4.x 가이드의 좌표는 문서에 적힌 만큼만 나온다 (kafka는 "확인되지 않는다"). 3.x 좌표 공개 API 미확인.

### 4.3-3 Spring Boot 문서 밖 항목 (2026-10-21 확인)
items 204건 중 `doc_url`이 Spring Boot 문서인 항목 73, 외부 링크 113(그중 docs.spring.io의 다른 Spring 프로젝트 79, techdocs.broadcom.com 8 등), 링크 없음 18. 4.1.x 문서에 id·이름 문자열이 안 나오는 항목 최대 106 (단순 문자열 비교라 과대 추정). 예: springdoc-openapi(springdoc.org)는 가이드에서 좌표만 나오고 설정·import는 "확인되지 않는다".
대응: 문서 근거가 없으면 화면에서 외부 문서 링크로 안내 (`app.py` `no_docs_notice`). springdoc-openapi는 외부 문서 수집 추가 (3절). 나머지(docs.spring.io 79건 등)는 `external_docs.SOURCES`에 출처를 추가하는 방식으로 확장 가능 — 결정 필요.

### 4.4 공유 문서 중복
여러 항목이 같은 Boot 문서를 수집하면 청크 ID(`항목ID:버전:문서ID:순번`) 때문에 항목별로 중복 저장된다. 명세 요구(덮어쓰지 않기)대로이며 용량만 늘어난다.

## 5. 다음 작업 (순서대로)

1. 상호 점검(옆 교육생)
2. push (사용자 요청 시)

## 6. 커밋 이력 요약
- 기획 문서 → 라이브러리 버전·설정 → items 색인 (F2001, F2002)
- 디렉터리 정리(scripts/) → 문서 원문 수집·후보 검색 (F2004) → 청킹 (F2005) → javadoc 매크로 보완
