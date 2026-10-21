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
                                  [app.py Streamlit]
```

의존은 위에서 아래로만 흐른다 (`app.py → services → rag → data_prep, vector_store`). 도메인에 묶인 코드(Initializr 파싱, spring-boot 문서 경로)는 `data_prep`에만 두고, `vector_store`는 도메인을 모른다.

## 2. 컬렉션과 메타데이터

### items (RAG 1)
- 청크 1개 = 항목 1건, 청크 ID = 항목 id (예: `kafka`)
- 문서(검색 텍스트): `이름 · id · 그룹 · 설명 · 문서 링크`
- 메타데이터: `item_id`, `name`, `group`, `doc_url`, `source`("initializr"), `collected_at`

### docs (RAG 2)
- 청크 ID = `항목ID:버전:문서ID:순번` (여러 항목이 같은 문서를 수집해도 덮어쓰지 않음)
- 메타데이터: `item_id`, `boot_version`, `doc_title`, `doc_id`(Antora 모듈 기준 상대 경로, 예: `reference/pages/messaging/kafka.adoc`), `source_url`(docs.spring.io 원문), `repo_url`(GitHub 파일), `query`(수집에 쓴 검색어), `license`("Apache-2.0"), `source_type`("boot-reference"), `collected_at`
- 검색 필터: `item_id`와 `boot_version`. 이 필터가 빠지면 다른 항목·버전의 문서가 섞인다.

## 3. 수집·청킹·색인 흐름 (F2003~F2005)

원문 수집(배치)과 색인(질문 시점)을 나눈다.

**데이터 구축 (`scripts/fetch_docs.py`, 1회)**: 버전마다 GitHub Trees API로 reference·how-to·specification 모듈의 `.adoc` 목록을 받고, raw로 본문을 받아 `data/boot_docs/{버전}/`에 원문 그대로 저장한다 (호출 간격 1초 이상, 이미 받은 파일은 건너뜀).

**질문 시점**
1. 프롬프트1: 항목과 질문에서 검색어 JSON 배열 추출. 항목 이름은 항상 포함.
2. 캐시 확인 (`data/collect_log.json`): 같은 (항목, 버전, 질문)이면 저장된 검색어를 쓰고 프롬프트1을 건너뜀. (항목, 버전, 검색어)가 모두 수집됐으면 수집 전체를 건너뜀.
3. 후보 수집: 해당 버전 로컬 사본(약 127개)에서 검색어가 경로·본문에 나오는 횟수로 후보를 추림. 경로 일치는 문서 주제이므로 가중치를 크게 준다.
4. 프롬프트2: 후보의 제목과 경로만 LLM에 보여 색인할 문서를 선별. 항목의 `doc_url`이 가리키는 문서는 선별과 무관하게 항상 포함.
5. 본문 정리: 앵커 줄 제거, `javadoc:`은 패키지 전체 이름, `configprop:`은 속성 이름, `xref:`는 표시문(없으면 앵커)으로 바꿈. 코드 블록 보존.
6. 청킹: 헤더 단위로 나눈 뒤 청크 크기·중복 설정으로 분할, 코드 블록은 중간에 자르지 않음.
7. 임베딩(`text-embedding-3-small`) 후 `docs` 컬렉션에 저장.

사전 색인으로 대표 항목을 미리 채워 둘 수 있고, 같은 코드가 질문 시점에도 동작한다.

**외부 문서 출처 (`data_prep/external_docs.py`)**: 항목 id가 `SOURCES`에 있으면 그 문서도 후보 검색에 넣는다. 지금은 springdoc-openapi. Boot 버전마다 호환되는 판을 쓴다 (4.x → springdoc 3.x 문서, 3.4~3.5 → 2.x 문서). doc_id는 `출처:경로`(예: `springdoc-openapi:v2/features.adoc`), 청크 메타데이터 `source_type`은 표시 이름("springdoc-openapi 2.x 문서"), `source_url`은 판별 원문 링크.

## 4. 검색과 병합 (F2006, F2014)

1. 선택 항목의 `items` 청크를 검색 없이 항상 포함.
2. `docs`에서 `item_id`·`boot_version` 필터 후 질문과의 유사도 검색 (심화: MMR).
3. 두 결과를 병합하고 청크 ID 기준으로 중복 제거.
4. 근거 번호를 부여하고 출처 유형을 구분해 프롬프트에 전달.

## 5. 프롬프트

| 프롬프트 | 역할 | 출력 형식 |
|---|---|---|
| 1 검색어 추출 | "Spring 기술 문서 전문가"로서 항목·질문에서 문서 검색어 추출 | JSON 배열만 |
| 2 후보 선별 | 후보(제목·경로) 중 색인할 문서 선택 | 선택한 인덱스 JSON 배열 |
| 3 답변 생성 | 근거 문서의 내용만 사용, 없으면 "문서에서 확인되지 않는다", 주장 뒤에 `[근거 N]`, 선택한 버전을 명시 | 마크다운 |

## 6. 설정 (`config.toml`, 초기값)

| 항목 | 초기값 | 이유 |
|---|---|---|
| 청크 크기 / 중복 | 1000자 / 200자 | 명세 예시. 검증 단계에서 바꿔 비교 |
| Top-k | 8 (항목 메타 1 + 문서 청크) | 검증 단계에서 조정 |
| 검색 방식 | similarity (심화: mmr, fetch_k 30) | |

## 7. 근거 표시 (F2008)

답변의 `[근거 N]` 표기를 파싱해 실제 인용된 근거만 화면에 표시한다. 제목, 출처 유형, 원문 링크를 함께 보여주고, 인용이 없으면 그 사실을 안내한다. 기존 `app.py`의 `cited_sources`를 그대로 사용한다.

## 8. 도메인 특화 기능 (F2010): 버전 맞춤 사용 가이드

구현: `services/guide.py`. 고정 질문(`GUIDE_QUESTION`)으로 `collect` → `answer`를 실행하고, Initializr가 지원하는 버전(4.0.x, 4.1.x)은 `/dependencies?bootVersion=` 좌표를 근거로 함께 넣는다. 4.x 문서에는 스타터 좌표(`spring-boot-starter-kafka`)가 없어 문서만으로는 틀린 의존성을 안내하게 되기 때문이다. 3.x는 Initializr가 지원하지 않아(400) 문서 근거만 쓴다.

선택한 항목과 버전에 대해 의존성 선언(Gradle/Maven), 핵심 설정 속성, import 예시를 한 번에 안내한다. 같은 근거 검색을 쓰므로 근거 번호와 링크가 함께 나온다. 이렇게 설계한 이유: 버전마다 달라지는 값을 사용자가 가장 자주 찾는 형태로 묶기 위해서이다.

## 9. 겪은 문제와 해결 (작성 중)

- docs.spring.io에는 검색 API가 없어 후보 수집을 GitHub 문서 파일 목록으로 대체했다.
- 버전마다 문서 위치가 다르다 (4.x는 `documentation/...`, 3.2~3.5는 `spring-boot-project/...`). 버전별 경로를 `data_prep` 설정으로 둔다.
- 파일 경로만으로 후보를 찾으면 개념 검색어가 빠진다 (`jackson`, `jpa`, `datasource` 경로 일치 0건, 대표 질문 3의 `features/json.adoc` 누락). 원문을 미리 받아 두고 본문까지 검색하도록 바꿨다.
- `javadoc:` 매크로를 클래스 이름만 남기면 버전별 패키지 이동(대표 질문 1)이 사라진다. 패키지 전체 이름을 남긴다.
- items 204건 중 Spring Boot 문서로 설명되는 항목은 73건뿐이다. SpringDoc처럼 외부 문서 항목은 근거가 Initializr 정보뿐이라, 외부 문서를 두 번째 출처로 추가했다. 외부 문서도 버전이 있어(springdoc 2.x/3.x) Boot 버전에 맞는 판을 고른다.
