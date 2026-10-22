# RAG 파이프라인 설계문서

## 1. 구성

```
[scripts: 배치]  build_items -> items 컬렉션        fetch_docs -> data/boot_docs/ (원문 사본)

[data_prep]  Initializr API -> items.json     GitHub API -> 원문 사본, 매크로 정리, 후보 검색
     |                                              |
[vector_store]  items 컬렉션 (RAG 1)          docs 컬렉션 (RAG 2)   (ChromaDB, 청킹)
     \______________________  ____________________/
                [rag: collect(질문 시점 수집) / LangGraph retrieve -> generate / prompts]
                                        |
                              [services]  특화 기능 / 조건 탐색
                                        |
                       [server.py FastAPI (SSE)]  ←  [web/ HTML·CSS·JS]
```

의존은 위에서 아래로만 흐른다 (`server.py → services → rag → data_prep, vector_store`). 도메인에 묶인 코드(Initializr 파싱, spring-boot 문서 경로)는 `data_prep`에만 두고, `vector_store`는 도메인을 모른다.

## 2. 컬렉션과 메타데이터

### items (RAG 1)
- 청크 1개 = 항목 1건, 청크 ID = 항목 id (예: `kafka`)
- 문서(검색 텍스트): `이름 · id · 그룹 · 설명 · 문서 링크`
- 메타데이터: `item_id`, `name`, `group`, `doc_url`, `source`("initializr"), `collected_at`

### docs (RAG 2)
- 청크 ID = `항목ID:버전:문서ID:순번` (여러 항목이 같은 문서를 수집해도 덮어쓰지 않음)
- 메타데이터: `item_id`, `boot_version`, `doc_title`, `doc_id`(Antora 모듈 기준 상대 경로, 예: `reference/pages/messaging/kafka.adoc`), `source_url`(원문 링크: docs.spring.io 또는 springdoc.org 판별 페이지), `repo_url`(GitHub 파일), `query`(수집에 쓴 검색어), `license`("Apache-2.0"), `source_type`(Boot 문서는 코드값 "boot-reference", 외부 문서는 표시 이름 "springdoc-openapi 3.x 문서" 등), `collected_at`
- 검색 필터: `item_id`와 `boot_version`. 이 필터가 빠지면 다른 항목·버전의 문서가 섞인다.

## 3. 수집·청킹·색인 흐름 (F2003~F2005)

원문 수집(배치)과 색인(질문 시점)을 나눈다.

**데이터 구축 (`scripts/fetch_docs.py`, 1회)**: 버전마다 GitHub Trees API로 reference·how-to·specification 모듈의 `.adoc` 목록을 받고, raw로 본문을 받아 `data/boot_docs/{버전}/`에 원문 그대로 저장한다 (호출 간격 1초 이상, 이미 받은 파일은 건너뜀).

**질문 시점**
1. 프롬프트1: 항목과 질문에서 검색어 JSON 배열 추출. 항목 이름은 항상 포함.
2. 캐시 확인 (`data/collect_log.json`): 같은 (항목, 버전, 질문)이면 저장된 검색어를 쓰고 프롬프트1을 건너뜀. (항목, 버전, 검색어)가 모두 수집됐으면 수집 전체를 건너뜀.
3. 후보 수집: 해당 버전 로컬 사본(122~128개, 외부 문서 출처가 있으면 15~16개 추가)에서 검색어가 경로·본문에 나오는 횟수로 후보 10개(`collect.candidates`)를 추림. 경로 일치는 문서 주제이므로 가중치를 크게 준다(20배).
4. 프롬프트2: 후보의 제목과 경로만 LLM에 보여 색인할 문서를 최대 3개(`collect.max_docs`) 선별. 항목의 `doc_url`이 가리키는 문서는 선별과 무관하게 항상 포함.
5. 본문 정리: 앵커 줄 제거, `javadoc:`은 패키지 전체 이름(`[format=annotation]`이면 `@` 붙임), `configprop:`은 속성 이름, `xref:`는 표시문(없으면 앵커), 따옴표 문법 `"`...`"`은 `"..."`로 바꿈. 코드 블록 보존.
6. 청킹: 헤더 단위로 나눈 뒤 청크 크기·중복 설정으로 분할, 코드 블록은 중간에 자르지 않음.
7. 임베딩(`text-embedding-3-small`) 후 `docs` 컬렉션에 저장.

사전 색인으로 대표 항목을 미리 채워 둘 수 있고, 같은 코드가 질문 시점에도 동작한다.

**외부 문서 출처 (`data_prep/external_docs.py`)**: 항목 id가 `SOURCES`에 있으면 그 문서도 후보 검색에 넣는다. springdoc-openapi, Spring Data JDBC·R2DBC·JPA·Redis·MongoDB·Elasticsearch, Spring Security(security 전체, oauth2-client는 OAuth2 부분). Boot 버전마다 호환되는 판을 쓴다 (springdoc: 4.x → 3.x 문서, 3.4~3.5 → 2.x 문서. Spring Data: Boot 버전의 릴리스 묶음(spring-data-bom)이 정한 모듈 판 브랜치, commons는 묶음의 commons 판 브랜치. 예: Boot 4.0 → MongoDB 5.0 + commons 4.0). include 경로에 문서 속성이 쓰이면(`include::{vector-search-intro-include}[]`) 상위 문서의 정의를 대입한다. GitHub 파일 목록(Trees API, 비로그인 시간당 60회)은 `.tree.json`으로 저장해 다시 쓴다. 판마다 브랜치와 폴더를 지정하고, 사본은 `data/external_docs/{저장소}/{브랜치}/`에 둔다. Antora 문서의 `include::partial$…`, `include::{commons}@data-commons::page$…`(spring-data-commons 같은 판), 같은 폴더 상대 include를 풀고, `ifdef/ifndef/ifeval`과 본문 속성 정의(`:이름: 값`)를 처리한다. doc_id는 `출처:경로`(예: `springdoc-openapi:v2/features.adoc`), 청크 메타데이터 `source_type`은 표시 이름("springdoc-openapi 2.x 문서"), `source_url`은 판별 원문 링크.

## 4. 검색과 병합 (F2006, F2014)

1. 선택 항목의 `items` 청크를 검색 없이 항상 포함.
2. `docs`에서 `item_id`·`boot_version`·`doc_id`(이 질문을 위해 수집 단계가 고른 문서) 필터 후 MMR 검색 (후보 30개 → 7개, 6.1). 검색 질의는 질문 뒤에 수집 단계 프롬프트1의 영어 검색어를 붙인 것이다 (6.1-1). 가이드는 Initializr 의존성 좌표를 검색 밖 근거로 추가한다.
3. 두 결과를 병합하고 청크 ID 기준으로 중복 제거.
4. 근거 번호를 부여하고 출처 유형을 구분해 프롬프트에 전달.

## 5. 프롬프트

| 프롬프트 | 역할 | 출력 형식 |
|---|---|---|
| 1 검색어 추출 | "Spring 기술 문서 전문가"로서 항목·질문에서 문서 검색어 추출 | JSON 배열만 |
| 2 후보 선별 | 후보(제목·경로) 중 색인할 문서 선택 | 선택한 인덱스 JSON 배열 |
| 3 답변 생성 | 근거 문서의 내용만 사용, 없으면 "문서에서 확인되지 않는다", 주장 뒤에 `[근거 N]`, 선택한 버전을 명시, 물음이 여럿이면 나눠 답함, `a.b.Class`에서 패키지 읽기 | 마크다운 |

명세의 프롬프트 3개 외에 특화 기능용으로 다음을 쓴다 (모두 `rag/prompts.py`).

| 프롬프트 | 역할 | 출력 형식 |
|---|---|---|
| `GUIDE_QUESTION` | 가이드(F2010)용 고정 질문. 프롬프트3에 질문으로 넣는다 | (프롬프트3과 같음) |
| `EXPLORE_QUERY` | 조건 탐색(F2011): 한국어 조건 → 영어 검색 문장 (항목 설명이 영어) | 한 줄 |
| `EXPLORE_SELECT` | 조건 탐색: 후보 30개 중 조건에 맞는 항목과 이유 | `[{"id", "reason"}]` JSON |

## 6. 설정 (`config.toml`)

| 항목 | 초기값 | 이유 |
|---|---|---|
| 청크 크기 / 중복 | 1000자 / 200자 | 명세 예시. 검증 단계에서 바꿔 비교 |
| Top-k | 8 (항목 메타 1 + 문서 청크) | 검증 단계에서 조정 |
| 검색 방식 | ~~similarity~~ → **mmr** (fetch_k 30, lambda_mult ~~0.5~~ → 0.6) | 6.1 비교에서 정답 근거를 앞당기고 중복 섹션을 줄임 (2026-10-22 변경) |
| 수집 후보 / 선별 수 | 10 / 3 | 프롬프트2에 보여 줄 후보와 질문 한 번에 새로 색인할 최대 문서 수 |
| 탐색 후보 / 결과 수 | 30 / 8 | 조건 탐색의 items 후보와 카드 수 |
| 답변 모델 | ~~gpt-5.4-nano~~ → **gpt-5.4-mini** | 6.2 비교. 임베딩은 `text-embedding-3-small` (1536차원) |

### 6.1 검색 방식 비교: similarity vs MMR (F2014, 2026-10-22)

`python -m scripts.compare_search`. 같은 질문으로 근거 검색(`retrieve`)만 비교했다. 문서 근거 7개(top_k 8 - 항목 정보 1), MMR은 후보 30개(fetch_k)에서 `lambda_mult` 0.6으로 고른다. 검색 범위는 질문별 수집 문서(`doc_id`)다. "정답 근거 순위"는 답을 판별하는 단어가 처음 나오는 근거 번호.

| 항목·버전 | 방식 | 고유 섹션 / 7 | 정답 근거 순위 |
|---|---|---|---|
| kafka 4.0.x | similarity | 5 | `JacksonJsonDeserializer` 3, `kafka.autoconfigure.KafkaProperties` 2 |
| | mmr | 5 | 3, 2 |
| pulsar 3.5.x | similarity | 7 | `spring-boot-starter-pulsar-reactive` 2 |
| | mmr | 7 | 2 |
| web 4.0.x | similarity | 5 | `tools.jackson` 2 |
| | mmr | **7** | 2 |
| springdoc-openapi 4.1.x | similarity | 7 | `springdoc.swagger-ui.path` **7** |
| | mmr | 7 | **4** |
| springdoc-openapi 3.5.x | similarity | 5 | `springdoc.swagger-ui.path` 3 |
| | mmr | 5 | 3 |

- MMR이 정답 근거를 뺀 경우는 없었다. 순위가 같거나 앞당겨졌다 (springdoc 4.1.x 7위 → 4위). web 4.0.x는 같은 섹션 반복이 줄었다 (고유 섹션 5 → 7).
- `lambda_mult` 0.5(LangChain 기본값)에서는 springdoc 4.1.x 정답 근거가 7개 안에서 빠졌다. 검색 범위가 FAQ 한 문서(104청크)이고 비슷한 Swagger 섹션이 많아, 다양성 쪽이 정답을 밀어냈다. 0.5~0.8 비교 (정답 순위 / 고유 섹션):

| lambda_mult | kafka 4.0.x | pulsar 3.5.x | web 4.0.x | springdoc 4.1.x | springdoc 3.5.x |
|---|---|---|---|---|---|
| 0.5 | 3, 2 | 2 | 2 / 7 | **없음** | 3 |
| **0.6** | 3, 2 | 2 | 2 / 7 | **4** | 3 |
| 0.7 | 3, 2 | 2 | 2 / 6 | 6 | 3 |
| 0.8 | 3, 2 | 2 | 2 / 5 | 6 | 3 |

  0.6이 정답을 빼지 않으면서 다양성을 유지해 0.6으로 정했다. 질문 5개로 정한 값이라 다른 질문에서도 최적인지는 확인하지 않았다.
- 다른 질문으로 수집한 문서가 범위에 섞이면 결과가 달라진다 (9절 마지막 항목). 표는 질문별 범위로 좁힌 뒤 다시 잰 값이다.

### 6.1-1 검색 질의에 영어 검색어 붙이기 (2026-10-22)

문서는 영어인데 질문은 한국어라, 짧은 질문("join sql 작성법")은 엉뚱한 청크(jOOQ 코드 생성 등)가 위로 왔다. 수집 단계 프롬프트1이 이미 만든 영어 검색어를 질문 뒤에 붙여 검색한다 (`collect` 결과 `terms` → `retrieve`). 추가 LLM 호출은 없다. 같은 5개 질문의 정답 근거 순위 (`python -m scripts.compare_search`):

| 항목·버전 | similarity 질문만 → +검색어 | mmr 질문만 → +검색어 |
|---|---|---|
| kafka 4.0.x (`JacksonJsonDeserializer`, `KafkaProperties` 패키지) | 3, 2 → **1**, 3 | 3, 2 → **1**, 3 |
| pulsar 3.5.x | 2 → **1** | 2 → **1** |
| web 4.0.x | 2 → 3 | 2 → 2 |
| springdoc-openapi 4.1.x | 7 → **없음** | 4 → 6 |
| springdoc-openapi 3.5.x | 3 → 6 | 3 → 4 |

- 기본 방식(mmr)에서는 5개 모두 정답 근거가 7개 안에 남았다. kafka·pulsar는 1위로 올랐고 springdoc은 조금 내려갔다. springdoc 질문은 이미 "Swagger UI 경로"라는 영어 단어가 있어 붙인 검색어가 FAQ의 비슷한 섹션들을 더 끌어온 것으로 보인다.
- 이번 변경을 하게 된 질문: Spring Data JDBC 4.1.x "join sql 작성법"은 근거 7개 중 Spring Data JDBC 문서가 2개 → 5개, jOOQ·H2 콘솔 같은 무관한 Boot 청크가 빠졌고 답에 `@Query`로 쿼리를 직접 지정하는 방법이 들어갔다.
- RAG 전후 비교(rag-comparison.md)와 명세 4장 자동 확인(21/21)은 판정이 같다.

### 6.2 답변 모델 비교 (2026-10-21)

대표 질문 1("JSON 값 역직렬화 클래스는? KafkaProperties의 패키지는?", 두 물음 결합)을 4.0.x·3.5.x 각 2회.

| 모델 | 두 물음 모두 정답 | 평균 응답 |
|---|---|---|
| gpt-5.4-nano | 3 / 4 (프롬프트 보완 전 1 / 4) | 5.2초 |
| **gpt-5.4-mini** | **4 / 4** | **4.3초** |
| gpt-5.4 | 4 / 4 | 5.9초 |

nano는 검색된 근거에 `KafkaProperties` 전체 이름이 있어도 뒤 물음을 앞 물음 클래스의 패키지로 답했다. 검색이 아니라 생성 문제였다. 정확도가 같은 gpt-5.4보다 빠른 mini를 쓴다.

### 6.3 청크 크기와 Top-k (2026-10-22, `python -m scripts.verify`)

- 같은 문서(Kafka 4.1.x `messaging/kafka.adoc`)를 1000/200으로 나누면 11개, 500/100이면 27개. 헤더 단위로 먼저 나누므로 크기를 절반으로 줄여도 청크 수가 2배를 넘는다 (짧은 섹션이 그대로 남고 긴 섹션만 더 잘린다).
- Top-k 4 → 8: 근거 4개 → 8개. 늘어난 근거는 같은 문서의 다른 섹션(Testing with Embedded Kafka 등)이라, 질문과 무관한 근거가 늘어날 수 있다. 문서 근거 7개면 대표 질문의 정답 근거가 모두 3위 안에 들어 8을 유지한다 (6.1).

## 7. 근거 표시 (F2008)

답변의 `[근거 N]` 표기를 파싱해 실제 인용된 근거만 화면에 표시한다. 제목, 출처 유형, 원문 링크를 함께 보여주고, 인용이 없으면 그 사실을 안내한다. `web/app.js`의 `citedSources`가 처리한다 (Streamlit 골격의 `cited_sources`를 옮김). 답변 마크다운은 marked로 변환하고 DOMPurify로 정제해 LLM 출력의 스크립트를 막는다.

## 8. 도메인 특화 기능 (F2010): 버전 맞춤 사용 가이드

구현: `services/guide.py`. 고정 질문(`GUIDE_QUESTION`)으로 `collect` → `answer`를 실행하고, Initializr가 지원하는 버전(4.0.x, 4.1.x)은 `/dependencies?bootVersion=` 좌표를 근거로 함께 넣는다. 4.x 문서에는 스타터 좌표(`spring-boot-starter-kafka`)가 없어 문서만으로는 틀린 의존성을 안내하게 되기 때문이다. 3.x는 Initializr가 지원하지 않아(400) 문서 근거만 쓴다.

선택한 항목과 버전에 대해 의존성 선언(Gradle/Maven), 핵심 설정 속성, import 예시를 한 번에 안내한다. 같은 근거 검색을 쓰므로 근거 번호와 링크가 함께 나온다. 이렇게 설계한 이유: 버전마다 달라지는 값을 사용자가 가장 자주 찾는 형태로 묶기 위해서이다.

## 9. 겪은 문제와 해결

- docs.spring.io에는 검색 API가 없어 후보 수집을 GitHub 문서 파일 목록으로 대체했다.
- 버전마다 문서 위치가 다르다 (4.x는 `documentation/...`, 3.2~3.5는 `spring-boot-project/...`). 버전별 경로를 `data_prep` 설정으로 둔다.
- 파일 경로만으로 후보를 찾으면 개념 검색어가 빠진다 (`jackson`, `jpa`, `datasource` 경로 일치 0건, 대표 질문 3의 `features/json.adoc` 누락). 원문을 미리 받아 두고 본문까지 검색하도록 바꿨다.
- `javadoc:` 매크로를 클래스 이름만 남기면 버전별 패키지 이동(대표 질문 1)이 사라진다. 패키지 전체 이름을 남긴다.
- 같은 질문에도 프롬프트1이 매번 다른 검색어를 내서 "같은 질문 재수집 안 함"이 깨졌다. (항목, 버전, 질문) → 검색어도 캐시한다.
- `javadoc:X[format=annotation]`(4개 버전 3567건)의 옵션 값이 답변에 "format=annotation"으로 새어 나왔다. 옵션으로 처리하고 재색인했다.
- 4.x 문서에는 스타터 좌표(`spring-boot-starter-kafka`)가 한 번도 나오지 않아, 가이드가 틀린 의존성을 안내할 수 있었다. Initializr `/dependencies`의 버전별 좌표를 근거로 넣었다. Initializr는 3.x를 지원하지 않아(400) 3.x는 문서만 쓴다.
- springdoc 문서의 `{springdoc-version}`은 `_attributes.adoc`이 아니라 `pom.xml`의 빌드 속성에 있었다. pom의 일반 속성(`version`)까지 쓰면 본문의 `{version}`이 잘못 바뀌어, springdoc 속성만 쓴다.
- 조건 탐색 프롬프트 예시에 테스트 조건("메시징 큐 → Kafka, RabbitMQ")을 넣어 결과를 믿을 수 없었다. 무관한 예시로 바꿔 재확인했다. 무관한 조건에도 항목을 억지로 골라 "목적과 무관하면 고르지 않는다" 규칙을 넣었다.
- RAG 전후 비교의 단어 판정에서 "단정할 수 없습니다"의 "없습니다"가 모름 응답으로 잡혀, 틀린 답이 맞게 판정됐다. 판정 단어를 좁히고 답변 전문을 직접 읽어 확정했다.
- items 204건 중 Spring Boot 문서로 설명되는 항목은 73건뿐이다. SpringDoc처럼 외부 문서 항목은 근거가 Initializr 정보뿐이라, 외부 문서를 두 번째 출처로 추가했다. 외부 문서도 버전이 있어(springdoc 2.x/3.x) Boot 버전에 맞는 판을 고른다.
- Spring Data JDBC 문서를 추가했는데도 예전에 한 질문은 새 문서를 보지 못했다. 검색어별 문서 선택이 캐시돼 있었기 때문이다. `fetch_docs`가 어떤 출처에 새 파일을 받으면 그 항목의 검색어별 선택 기록을 지운다 (`collect.forget`).
- 검색을 (항목, 버전)으로만 거르니, 다른 질문으로 수집한 문서가 정답을 밀어냈다. Kafka 4.0.x에 검증 스크립트의 오류 시험 질문이 실제로 수집한 Testing 문서(105청크)가 쌓여, "JSON 역직렬화" 질문 근거가 `@JsonTest` 섹션으로 채워지고 답이 "확인되지 않는다"가 됐다 (화면 캡처에서 발견). 수집 단계가 이 질문용 `doc_ids`를 돌려주고 검색은 그 문서 안에서만 하도록 바꿨다. 정답 근거가 순위 밖 → 1위. 검증 스크립트의 오류 시험은 수집도 가짜로 바꿨다.
