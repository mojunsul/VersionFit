# 요구사항 정의서

서비스명: 버전핏 — 내 Spring Boot 버전에 맞는 공식 문서 Q&A

## 1. 도메인과 조건 충족 근거

일반 LLM은 오래된 버전 기준의 설정과 API를 알려주는 경우가 많다. 이 서비스는 사용자가 고른 **항목(Spring Initializr 의존성)과 Spring Boot 버전**에 맞는 공식 문서를 근거로 답하고, 근거 문서를 함께 보여준다.

| 조건 | 내용 | 상태 |
|---|---|---|
| 항목 메타데이터 약 100건 이상 | Spring Initializr 메타데이터 API(`https://start.spring.io/metadata/client`)의 의존성 204건. 이 중 188건에 문서 링크가 있다 | 건수 확인 완료 (2026-10-21) |
| 항목마다 연결되는 설명 문서 | 항목의 `reference` 링크가 가리키는 페이지를 "항목 자체를 다룬 문서"로 쓴다. 본문은 spring-boot 저장소의 AsciiDoc을 GitHub API로 받는다 | 문서 경로 확인 완료 |
| 근거 필요한 질문 | 아래 3.3 참고 | 작성 완료 |
| 위험 도메인 여부 | 아니다. 면책 안내 없음 | - |

### 1.1 출처와 이용 조건

| 출처 | 용도 | 이용 조건 | 비고 |
|---|---|---|---|
| start.spring.io 메타데이터 API | 항목 메타데이터 | 서비스 소스가 Apache-2.0 공개 저장소(spring-io/start.spring.io). 별도 API 이용 약관과 robots.txt는 없음(404), 2026-10-21 확인 | 호출 1회, 결과를 로컬에 저장 |
| github.com/spring-projects/spring-boot | 외부 문서 (Boot 레퍼런스 AsciiDoc) | Apache-2.0 (GitHub API로 확인) | 브랜치 4.1.x, 4.0.x, 3.5.x, 3.4.x |
| GitHub REST API | 문서 파일 목록(후보) 조회 | GitHub API 약관, 인증 없이 시간당 60회 | 식별용 User-Agent 포함, 호출 간격 1초 이상 |
| docs.spring.io | 원문 링크 표시용 (본문 수집은 하지 않음) | robots.txt: crawl-delay 1 | |
| start.spring.io `/dependencies?bootVersion=` | 버전별 의존성 좌표 (F2010 가이드) | 위 메타데이터 API와 같음. 4.0.x·4.1.x만 지원(3.x는 400), 2026-10-21 확인 | 버전당 1회, `data/coordinates/`에 저장 |
| github.com/springdoc/springdoc.github.io | 외부 문서 (springdoc-openapi 3.x·2.x AsciiDoc) | Apache-2.0 (GitHub API로 확인), springdoc.org robots.txt `Allow: /`, 2026-10-21 확인 | Boot 4.x → 3.x판, 3.4~3.5 → 2.x판 |
| github.com/spring-projects/spring-data-jpa, -redis, -mongodb, -elasticsearch | 외부 문서 (Spring Data 모듈 Antora AsciiDoc) | Apache-2.0 (GitHub API로 확인), NOTICE 없음, 2026-10-22 확인 | 모듈 판은 spring-data-bom 값 (아래 progress.md 3절) |
| github.com/spring-projects/spring-kafka, spring-amqp, spring-batch, spring-session | 외부 문서 (Antora AsciiDoc) | Apache-2.0 (GitHub API로 확인), NOTICE 없음, 2026-10-22 확인 | Boot 의존성 설정의 판 (progress.md 3절) |
| github.com/spring-projects/spring-security | 외부 문서 (Spring Security Antora AsciiDoc) | Apache-2.0 (GitHub API로 확인), NOTICE 없음, 2026-10-22 확인 | Boot 4.1/4.0/3.5/3.4 → 브랜치 7.1.x/7.0.x/6.5.x/6.4.x |
| github.com/spring-projects/spring-data-relational, spring-data-commons | 외부 문서 (Spring Data JDBC·R2DBC Antora AsciiDoc, commons 페이지는 include로 포함) | Apache-2.0 (GitHub API로 확인), 2026-10-22 확인 | Boot 4.1/4.0/3.5/3.4 → 브랜치 4.1.x/4.0.x/3.5.x/3.4.x |
| github.com/projectlombok/lombok | 외부 문서 (Lombok 기능 문서, FreeMarker HTML 템플릿과 예제 코드) | MIT (LICENSE 파일, GitHub API는 NOASSERTION), 2026-10-22 확인 | Boot 4.1/4.0 → 태그 v1.18.48, 3.5 → v1.18.46, 3.4 → v1.18.42 |

### 1.2 지원 버전

4.1.x, 4.0.x, 3.5.x, 3.4.x. 3.2.x~3.3.x는 설정 추가로 확장 가능. 3.1.x 이하와 2.x는 문서 형식이 달라 제외.

### 1.3 근거가 필요한 질문 (예시)

항목과 버전을 고른 상태에서 물을 수 있고, 3.5.x와 4.0.x 문서의 실제 차이(2026-10-21 문서 비교)로 답이 갈리는 질문이다.

| # | 항목 | 질문 | 문서에서 확인한 차이 |
|---|---|---|---|
| 1 | Spring for Apache Kafka | "JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나? KafkaProperties의 패키지는?" | 3.5: `JsonDeserializer`, `org.springframework.boot.autoconfigure.kafka` / 4.0: `JacksonJsonDeserializer`, `org.springframework.boot.kafka.autoconfigure` |
| 2 | Spring for Apache Pulsar | "리액티브 Pulsar 스타터를 쓸 수 있나?" | 3.5: `spring-boot-starter-pulsar-reactive` 문서 있음 / 4.0: 리액티브 섹션과 스타터 설명이 문서에서 사라짐 |
| 3 | Spring Web | "JSON 직렬화(Jackson)를 설정할 때 쓰는 패키지는?" | 3.5: `com.fasterxml` / 4.0: `tools.jackson` (`features/json`) |

위 차이는 문서 원문을 비교해 확인했지만, 답변이 실제로 이 차이를 정확히 짚는지는 구현 후 검증한다.

## 2. 기능 요구사항

필수 기능은 명세 그대로 따른다. 도메인에 맞게 표현만 바꾼다.

| 번호 | 분류 | 요구사항명 | 이 프로젝트에서의 구현 | 우선순위 |
|---|---|---|---|---|
| F2001 | 데이터 | 항목 메타데이터 적재 | Initializr 의존성 204건을 로드, 항목 1건을 이름·id·그룹·설명·문서 링크를 이은 텍스트로 구성 | 필수 |
| F2002 | 색인 | 메타데이터 색인(RAG 1) | `items` 컬렉션에 항목당 1청크, 청크 ID = 항목 id (재색인 시 덮어쓰기), 색인 건수 화면 표시 | 필수 |
| F2003 | 프롬프트 | 검색어 추출(프롬프트1) | 항목·질문에서 문서 검색어를 JSON 배열로 추출, 항목 자체 문서는 항상 대상 | 필수 |
| F2004 | 수집 | 외부 문서 수집(프롬프트2) | 선택한 버전 브랜치의 문서 원문 사본(Boot 문서 + 항목의 프로젝트 문서)에서 검색어가 경로·본문에 나오는 횟수로 후보 10개를 모아 선별 프롬프트로 고르고, 본문과 원문 URL 수집. 항목 자체 문서는 항상 포함. 이미 수집한 검색어는 재수집하지 않음 | 필수 |
| F2005 | 색인 | 외부 문서 색인(RAG 2) | 청크 크기·중복은 `config.toml`. `docs` 컬렉션에 저장, 청크 ID = `항목ID:버전:문서ID:순번` | 필수 |
| F2006 | 검색 | 근거 검색 및 병합 | 선택 항목의 메타데이터 청크는 항상 포함, 문서 청크는 항목·버전·질문별 수집 문서로 필터링해 검색(질문 + 영어 검색어, MMR, 항목 자체 Boot 문서 근거 우선), 병합 후 중복 제거, Top-k는 설정 | 필수 |
| F2007 | 생성 | 근거 기반 답변(프롬프트3) | LangGraph retrieve/generate 두 노드, 근거에 출처 유형(항목 메타데이터/Boot 문서/프로젝트 문서) 구분, 근거 없으면 "확인되지 않는다" | 필수 |
| F2008 | 생성 | 근거 표시 | 본문의 `[근거 N]` 중 실제 인용된 것만 제목·원문 링크와 함께 표시, 인용 없으면 안내 | 필수 |
| F2009 | UI | 항목 선택 및 질의응답 | 사이드바에서 항목과 Boot 버전 선택, 항목·버전별 대화 기록 분리 | 필수 |
| F2010 | 서비스 | 도메인 특화 기능 | **버전 맞춤 사용 가이드**: 선택 항목과 버전의 의존성 선언·핵심 설정·import를 근거 문서와 함께 생성 | 필수 |
| F2011 | 서비스 | 조건 기반 항목 탐색 | 자연어 조건("메시징에 쓸 수 있는 의존성")으로 `items`를 검색하고 LLM이 맞는 항목만 카드로 제시, 선택 시 해당 항목 대화로 이동 | 필수 |
| F2012 | UI | 진행 상태 및 안내 | 수집·생성 중 진행 상태, 색인 없음·키 누락·검색 결과 없음 안내 (위험 도메인 아님) | 필수 |
| F2013 | UI | 프론트엔드 직접 구현 | FastAPI(`server.py`) + HTML·CSS·JS(`web/`), SSE 진행 상태 | 심화 (선택) |
| F2014 | 검색 | MMR 검색 | 후보 넉넉히 조회 후 MMR로 선별, 유사도 검색과 비교 | 심화 (선택) |
| F2015 | 품질 | RAG 전후 비교 | 대표 질문 5개 이상, 3개 기준(사실 정확성·근거 제시·모름 응답)으로 비교 문서 작성 → `docs/rag-comparison.md` | 심화 (선택) |
| F2016 | 수집 | 여러 문서 출처 결합 | Spring Boot 문서에 더해 26개 항목(springdoc-openapi, data-jdbc·r2dbc·jpa·redis·redis-reactive·mongodb·mongodb-reactive·elasticsearch, security·oauth2-client·oauth2-resource-server·security-saml2·spring-security-webauthn, kafka·kafka-streams, rabbitmq·rabbitmq-streams, batch·batch-jdbc·batch-data-mongodb, session-data-redis·session-jdbc·session-hazelcast·session-data-mongodb, lombok)의 프로젝트 문서를 Boot 버전에 맞는 판으로 결합, 근거에 출처 종류 표시 | 심화 (선택) |
| (추가) | 생성 | 일반 지식 답변 | 문서 기반 답변이 확인되지 않거나 인용이 없을 때 사용자가 버튼을 누르면 근거 없이 LLM 일반 지식으로 답하고, "문서 근거 없음"으로 구분 표시 (F2007은 그대로) | 추가 |

## 3. 비기능 요구사항

| 번호 | 요구사항명 | 구현 방침 |
|---|---|---|
| NF2001 | 응답 시간 | 사전 색인된 범위는 즉시 응답, 미색인 시 수집 단계 진행 상태 표시 |
| NF2002 | 수집 캐시 | (항목, 버전, 검색어) 수집 이력을 저장해 재수집 방지 |
| NF2003 | API 키 관리 | `.env` 환경변수, `.gitignore` 등록 |
| NF2004 | 내부 정보 비노출 | 화면에 키, 프롬프트 전문, 오류 추적 미표시 |
| NF2005 | 모듈 분리 | `data_prep`(도메인 의존) / `vector_store` / `rag` / `services` / `server.py`(API) / `web/`(화면) |
| NF2006 | 외부 API 예절 | 호출 간격 1초 이상, 재시도, 식별용 User-Agent, GitHub 호출 제한 처리 |
| NF2007 | 출처와 이용 조건 | 1.1 표와 README에 기록 |

## 4. 검증

명세 4장의 체크리스트로 점검한 결과는 [verification.md](verification.md)에 있다 (2026-10-22 셀프 점검, 화면 캡처는 최종 UI로 다시 찍을 예정).
