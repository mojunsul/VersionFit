# RAG 전후 비교 (F2015)

2026-10-22 측정, 같은 날 질문별 문서 범위 검색·MMR lambda_mult 0.6으로 바꾼 뒤 재측정 (판정 같음, 답변 전문은 재측정 결과). 검색 질의에 영어 검색어를 붙인 뒤(rag-design.md 6.1-1), 외부 문서(Spring Kafka 등)를 추가하고 항목 자체 Boot 문서 근거를 먼저 확보하게 한 뒤(6.1-2), 답변 규칙에 "근거의 기능으로 해결 방법이 분명하면 먼저 설명"을 넣은 뒤에도 판정은 같다. 재현: `python -m scripts.compare_rag`

같은 날 답변 모델을 `gpt-5.4-mini`에서 `gpt-6.1-sol`로 바꾸고 같은 질문으로 다시 쟀다 (2.1절, 4절 끝). 2절 표와 3절 답변 전문은 mini 측정, 5절은 sol 답변 전문이다.

## 1. 방법

- 같은 모델(처음 `gpt-5.4-mini`, 바꾼 뒤 `gpt-6.1-sol`)로 같은 질문에 두 번 답한다.
  - **LLM만**: 근거 없이 항목·버전·질문만 준다. 공정하게 비교하려고 "확실하지 않거나 모르면 모른다고 답한다"는 지시를 똑같이 넣었다.
  - **RAG**: 서비스와 같은 경로(`collect` → `answer`, 검색 MMR, 근거 8개).
- 질문 6개: 답이 문서에 있는 질문 4개(버전에 따라 답이 달라지는 질문 포함), 문서에 답이 없는 질문 2개.
- 기준 3개
  - **사실 정확성**: 맞는 값이 들어 있고, 틀린 값(다른 버전의 값, 없는 기능을 있다고 한 주장)이 없는가
  - **근거 제시**: 주장에 `[근거 N]`을 붙였는가
  - **모름 응답**: 답이 문서에 없을 때 지어내지 않고 모른다고 하는가
- 1차 판정은 스크립트의 단어 기준이고, 아래 표는 답변 전문(3절)을 읽고 확정했다.

## 2. 결과

| # | 항목·버전 | 질문 요지 | LLM만 | RAG |
|---|---|---|---|---|
| 1 | Kafka 4.0.x | 역직렬화 클래스, `KafkaProperties` 패키지 | ✗ 3.x 값(`JsonDeserializer`, `boot.autoconfigure.kafka`)으로 답함 | ✓ `JacksonJsonDeserializer`, `boot.kafka.autoconfigure` [근거] |
| 2 | Kafka 3.5.x | 같은 질문 | ✓ | ✓ [근거] |
| 3 | Web 4.0.x | Jackson 패키지 | ✗ `tools.jackson` 누락 (3.x의 `com.fasterxml`로 답함) | ✓ `tools.jackson` [근거] |
| 4 | SpringDoc 3.5.x | Swagger UI 경로 속성 | ✓ | ✓ [근거, springdoc 2.x 문서] |
| 5 | Pulsar 4.0.x | 리액티브 스타터 사용 가능 여부 (4.0 문서에서 사라짐) | ✗ "사용할 수 있습니다"라고 단정 | ✓ "문서에서 확인되지 않는다" + 문서에 있는 스타터만 안내 [근거] |
| 6 | Kafka 4.0.x | 브로커 권장 JVM 힙 (문서에 없음) | ✗ "6GB(-Xmx6g)"라는 근거 없는 수치 | ✓ "문서에서 확인되지 않는다" |

| 기준 | LLM만 | RAG |
|---|---|---|
| 사실 정확성 (1~5번, 5개) | 2 / 5 | **5 / 5** |
| 근거 제시 (답이 있는 1~5번) | 0 / 5 | **5 / 5** |
| 모름 응답 (5·6번) | 0 / 2 | **2 / 2** |

**해석**
- LLM만 쓰면 **최신 버전(4.0)의 변경을 모르고 3.x 지식으로 답한다** (1, 3번). 3.5.x처럼 학습된 지식과 맞는 버전은 맞힌다 (2, 4번). 이 서비스가 버전 인지형이어야 하는 이유가 여기서 드러난다.
- "모르면 모른다고 하라"고 지시해도 LLM만으로는 **없어진 기능을 있다고 하거나(5번) 그럴듯한 수치를 지어낸다(6번)**. RAG는 근거에 없으면 "확인되지 않는다"고 답했다.
- RAG의 6번 답에는 근거 번호가 없다. 인용할 근거가 없는 "모름" 답이라 맞는 동작이다.

**관찰: 항목과 무관한 질문**
처음에는 "Kafka 항목에서 GraphQL 스키마 위치를 묻는 질문"을 답이 없는 질문으로 넣었다. 그런데 RAG는 수집 단계에서 Spring Boot GraphQL 문서를 찾아와 `spring.graphql.schema.locations`를 근거와 함께 정확히 답했다. 지어낸 답이 아니라서 "모름" 질문에서 빼고, 실제로 문서에 없는 6번으로 바꿨다. 항목과 무관한 질문도 Spring Boot 문서 안에 답이 있으면 답한다는 뜻이다.

**한계**
- 질문 6개, 각 1회 측정이다. 같은 질문도 답이 달라질 수 있다.
- 판정 단어는 질문마다 직접 정했다.

### 2.1 답변 모델을 바꾼 뒤 (`gpt-6.1-sol`)

| # | 항목·버전 | LLM만 | RAG |
|---|---|---|---|
| 1 | Kafka 4.0.x | ✓ `JacksonJsonDeserializer`, `boot.kafka.autoconfigure` (3.x 값은 "이전 버전 기준"이라고 구분) | ✓ [근거] |
| 2 | Kafka 3.5.x | ✓ | ✓ [근거] |
| 3 | Web 4.0.x | ✓ `tools.jackson.databind` | ✓ `tools.jackson.databind.json` [근거] |
| 4 | SpringDoc 3.5.x | ✓ | ✓ [근거] |
| 5 | Pulsar 4.0.x | ✓ "4.0에서 리액티브 스타터 제거"라고 정확히 답함 | ✓ "문서에서 확인되지 않는다" + 문서에 있는 스타터만 안내 [근거] |
| 6 | Kafka 4.0.x | ✗ "브로커당 6GB 힙 권장"이라는 출처를 확인할 수 없는 수치 | ✓ "문서에서 확인되지 않는다" |

| 기준 | mini: LLM만 → RAG | sol: LLM만 → RAG |
|---|---|---|
| 사실 정확성 (1~5번) | 2 / 5 → 5 / 5 | 5 / 5 → 5 / 5 |
| 근거 제시 (1~5번) | 0 / 5 → 5 / 5 | 0 / 5 → **5 / 5** |
| 지어내지 않음 (5·6번) | 0 / 2 → 2 / 2 | 1 / 2 → **2 / 2** |

**해석**
- 더 최근 지식을 가진 sol은 LLM만으로도 Boot 4.0의 변경(Jackson 3 패키지, `KafkaProperties` 이동, Pulsar 리액티브 스타터 제거)을 맞혔다. 학습된 버전 안에서는 사실 정확성 차이가 사라진다. 모델이 학습한 뒤에 나온 버전에서는 mini에서 본 문제가 다시 생길 수 있다.
- 그래도 LLM만 답한 쪽은 근거를 하나도 제시하지 못했고, 문서에 없는 질문(6번)에는 "모르면 모른다고 하라"는 지시에도 수치를 지어냈다. RAG는 두 모델 모두 근거를 붙이고 6번에 "확인되지 않는다"고 답했다.
- 5번은 sol의 LLM만 답이 RAG보다 유용했다. RAG는 근거(4.0 문서)에 리액티브 스타터가 없다는 사실만 확인할 수 있어 "확인되지 않는다"로 답했다. 문서 근거만 쓰는 규칙의 대가다.
- 1차 자동 판정은 sol LLM만 1번을 ✗로 봤다(옛 패키지 이름이 답에 들어 있음). 전문을 보면 옛 이름은 "이전 버전 기준이므로 구분"하라는 문장 안에 있어 ✓로 확정했다.

## 3. 답변 전문

### 1. Spring for Apache Kafka · 4.0.x

**질문**: JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나? KafkaProperties의 패키지는?

**LLM만**

Spring Boot 4.0.x 기준으로 답하면, **JSON 값 역직렬화 설정**에는 보통 `org.springframework.kafka.support.serializer.JsonDeserializer` 클래스를 사용합니다.

또한 **`KafkaProperties`의 패키지**는  
`org.springframework.boot.autoconfigure.kafka.KafkaProperties` 입니다.

원하시면 이어서 `application.yml`에서의 설정 예시도 같이 드리겠습니다.

**RAG**

Spring Boot 4.0.x 기준

1. JSON 값 역역직렬화 설정에 쓰는 클래스는 `org.springframework.kafka.support.serializer.JacksonJsonDeserializer`입니다. [근거 4]

2. `KafkaProperties`의 패키지는 `org.springframework.boot.kafka.autoconfigure`입니다. [근거 3]

### 2. Spring for Apache Kafka · 3.5.x

**질문**: JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나? KafkaProperties의 패키지는?

**LLM만**

Spring Boot 3.5.x 기준으로 답하면, **JSON 값 역직렬화 설정**에는 보통 **`org.springframework.kafka.support.serializer.JsonDeserializer`** 클래스를 사용합니다.

그리고 **`KafkaProperties`의 패키지**는 **`org.springframework.boot.autoconfigure.kafka.KafkaProperties`** 입니다.

원하시면 이어서 `application.yml`에서 `spring.kafka.consumer.value-deserializer`를 어떻게 설정하는지도 예시로 보여드릴게요.

**RAG**

Spring Boot 3.5.x 기준입니다.

1. JSON 값 역역렬화 설정에 쓰는 클래스는 `org.springframework.kafka.support.serializer.JsonDeserializer`입니다. [근거 4]

2. `KafkaProperties`의 패키지는 `org.springframework.boot.autoconfigure.kafka`입니다. 즉 전체 이름은 `org.springframework.boot.autoconfigure.kafka.KafkaProperties`입니다. [근거 3, 5]

### 3. Spring Web · 4.0.x

**질문**: JSON 직렬화(Jackson)를 설정할 때 쓰는 패키지는?

**LLM만**

Spring Boot 4.0.x 기준, JSON 직렬화(Jackson)를 설정할 때 주로 사용하는 패키지는 **`com.fasterxml.jackson`** 계열입니다.

예를 들면:
- `com.fasterxml.jackson.databind`
- `com.fasterxml.jackson.databind.module`
- `com.fasterxml.jackson.annotation`

Spring Boot에서 Jackson 설정 자체를 다룰 때는 보통 **Spring 설정 패키지인 `org.springframework.boot.autoconfigure.jackson`** 도 함께 보게 됩니다.

정리하면:
- **Jackson 라이브러리 패키지:** `com.fasterxml.jackson.*`
- **Spring Boot의 Jackson 자동설정 관련 패키지:** `org.springframework.boot.autoconfigure.jackson`

정확히 “어떤 설정을 하려는지”에 따라 사용하는 패키지가 조금 달라질 수 있습니다.

**RAG**

Spring Boot 4.0.x 기준, JSON 직렬화(Jackson)를 설정할 때 관련 패키지는 문서에서 확인되는 범위 내에서 다음과 같습니다.

- Jackson 3 관련 클래스는 `org.springframework.boot.jackson` 패키지를 사용합니다. 예를 들어 `org.springframework.boot.jackson.JacksonMixin`, `org.springframework.boot.jackson.JacksonMixinModule`, `org.springframework.boot.jackson.ObjectValueSerializer`, `org.springframework.boot.jackson.ObjectValueDeserializer`가 있습니다. [근거 4, 6]
- Jackson 3의 자동 구성 대상인 `tools.jackson.databind.json.JsonMapper`도 문서에 나타납니다. [근거 3]

다만, 질문의 “JSON 직렬화(Jackson)를 설정할 때 쓰는 패키지”가 정확히 어떤 패키지를 뜻하는지 문서에서는 하나로 명시하지 않습니다. 따라서 문서에서 확인되는 관련 패키지는 `org.springframework.boot.jackson`와 `tools.jackson.databind.json`이며, 그 외는 문서에서 확인되지 않는다. [근거 3, 4, 6]

### 4. SpringDoc OpenAPI · 3.5.x

**질문**: Swagger UI 경로를 바꾸려면 어떤 속성을 쓰나?

**LLM만**

Spring Boot 3.5.x 기준, Swagger UI 경로는 `springdoc.swagger-ui.path` 속성으로 변경합니다.

예:
```properties
springdoc.swagger-ui.path=/api-docs
```

그러면 Swagger UI는 기본 `/swagger-ui.html` 또는 `/swagger-ui/index.html` 대신 지정한 경로로 접근하게 됩니다.

참고로 OpenAPI 문서 경로는 별도로 `springdoc.api-docs.path`로 바꿀 수 있습니다.

**RAG**

Spring Boot 3.5.x 기준, `swagger-ui` 경로를 바꾸려면 `springdoc.swagger-ui.path` 속성을 사용합니다. 기본값은 `/swagger-ui.html`이며, `swagger-ui` HTML 문서의 커스텀 경로를 지정하는 속성입니다. [근거 4]

### 5. Spring for Apache Pulsar · 4.0.x

**질문**: 리액티브 Pulsar 스타터(spring-boot-starter-pulsar-reactive)를 쓸 수 있나?

**LLM만**

Spring Boot 4.0.x 기준으로 답하면, **네. `spring-boot-starter-pulsar-reactive`를 사용할 수 있습니다.**

다만 몇 가지를 함께 알아두면 좋습니다.

- 이 스타터는 **Reactive Streams 기반으로 Pulsar를 사용**할 때 필요한 의존성을 포함합니다.
- 일반적인 `spring-boot-starter-pulsar`는 **동기식/기본 사용** 쪽에 가깝고,
- `spring-boot-starter-pulsar-reactive`는 **리액티브 애플리케이션에서 Pulsar를 통합**할 때 사용합니다.

즉, Spring Boot 4.0.x에서 **리액티브 Pulsar 클라이언트 지원을 원하면 이 스타터를 쓰는 방향이 맞습니다.**

원하시면 제가 이어서
1. Gradle/Maven 의존성 예시  
2. `ReactivePulsarTemplate` / reactive consumer 사용 예시  
3. 일반 Pulsar 스타터와의 차이  
까지 정리해드릴게요.

**RAG**

Spring Boot 4.0.x 기준으로, `spring-boot-starter-pulsar-reactive`를 사용할 수 있는지는 **문서에서 확인되지 않는다**.

근거에서 확인되는 것은 `spring-boot-starter-pulsar` 스타터와 `org.springframework.pulsar:spring-pulsar`에 대한 자동 구성뿐이며, 리액티브 Pulsar 스타터에 대한 언급은 없다 [근거 2].

### 6. Spring for Apache Kafka · 4.0.x

**질문**: Kafka 브로커에 권장되는 JVM 힙 메모리 크기는?

**LLM만**

Spring Boot 4.0.x 기준, Kafka 브로커의 **권장 JVM 힙 메모리 크기**는 **일반적으로 6GB(예: `-Xmx6g`) 정도**로 많이 안내됩니다.

다만 이 값은 **Spring Boot 자체의 설정값이라기보다 Kafka 브로커 운영 가이드에서 흔히 권장되는 경험적 기준**입니다. 실제 권장 크기는 다음에 따라 달라질 수 있습니다.

- 브로커에 저장되는 파티션 수
- 메시지 처리량
- 페이지 캐시 사용량
- 복제(replication) 및 압축 사용 여부
- 디스크/네트워크 성능
- JVM 버전과 GC 설정

즉, **“정답은 무조건 6GB”는 아니며**, 부하가 큰 환경에서는 더 크게 잡거나, 반대로 작은 환경에서는 더 작게도 운영할 수 있습니다.

원하시면 제가 **Kafka 브로커 메모리 구성(힙 vs off-heap vs OS page cache)** 도 함께 정리해드릴게요.

**RAG**

Spring Boot 4.0.x 기준, 질문하신 `Kafka 브로커`에 권장되는 JVM 힙 메모리 크기는 문서에서 확인되지 않는다.

## 4. 외부 문서 추가 효과 (2026-10-22)

재현: `python -m scripts.compare_sources`. 외부 문서 출처를 넣은 14개 항목에 질문을 하나씩 던져, 같은 질문을 **Boot 문서만** 근거로(외부 출처를 넣기 전 상태: 수집 단계가 고른 문서 중 Spring Boot 문서만) 답한 것과 **외부 문서 포함**으로 답한 것을 비교했다. 1차 판정은 정답 키워드(외부 문서 원문에서 확인한 클래스·설정 이름) 포함 여부이고, 아래 표는 답변 전문을 읽고 확정했다.

| 항목·버전 | 질문 | Boot 문서만 | 외부 문서 포함 |
|---|---|---|---|
| data-r2dbc 4.0.x | R2dbcEntityTemplate으로 조건 조회 | ✗ | ✓ `R2dbcEntityTemplate`, `Criteria` |
| data-jpa 4.0.x | @EntityGraph로 연관 엔티티 함께 조회 | ✗ | ✓ `attributePaths` |
| data-redis 3.5.x | RedisTemplate 직렬화 변경 | ✗ | ✓ `Jackson2JsonRedisSerializer` |
| data-elasticsearch 4.1.x | 검색 쿼리 작성 | ✗ | ✓ `CriteriaQuery` |
| kafka 4.0.x | 재시도 후 DLT | ✗ | ✓ `DeadLetterPublishingRecoverer` |
| batch 4.0.x | 청크 기반 Step | ✗ | ✓ `StepBuilder` + `chunk` |
| springdoc-openapi 3.5.x | Swagger UI 경로 변경 | ✗ (근거 없음) | ✓ `springdoc.swagger-ui.path` |
| data-jdbc 4.1.x | 메서드 이름 쿼리로 join 되나? | △ `@Query`만 언급, join 가능 여부는 "확인되지 않는다" | ✓ "쿼리 유도는 join 없이 WHERE까지 → `@Query`" |
| data-mongodb 4.0.x | MongoTemplate 집계 쿼리 | ✗ | ✓ `newAggregation` + `aggregate` 예시 (처음 측정 △) |
| security 4.0.x | 특정 경로만 인증 없이 허용 | ✗ | △ `requestMatchers`·`securityMatcher`까지, `permitAll` 없음 (다른 실행에서는 나옴) |
| oauth2-client 3.5.x | 구글 로그인 설정 | ✓ | ✓ (더 자세함) |
| rabbitmq 3.5.x | 재시도 소진 시 메시지 처리 | ✓ | ✓ |
| session-data-redis 3.4.x | 사용자 이름으로 세션 찾기 | ✗ | ✓ `FindByIndexNameSessionRepository`, 주체 이름 인덱스 (처음 측정 ✗) |
| lombok 4.1.x | @Data가 포함하는 애너테이션 | ✗ (항목 소개 한 줄뿐) | ✓ `@ToString`·`@EqualsAndHashCode`·`@Getter`·`@Setter`·`@RequiredArgsConstructor` |

**해석**
- 14개 중 11개가 외부 문서로 답할 수 있게 됐고(✗/△ → ✓), security 1개는 나아졌지만 `permitAll`이 빠졌다(✗ → △). 표는 수집 후보 점수 상한과 문서 고르기 프롬프트를 고친 뒤(아래) 다시 잰 값이다. Boot 문서는 자동 구성과 설정 속성까지만 다루고, 클래스 사용법(`R2dbcEntityTemplate`, `@EntityGraph`, `DeadLetterPublishingRecoverer` 등)은 각 프로젝트 문서에 있기 때문이다.
- Lombok은 Initializr 문서 링크가 비어 있고 Boot 문서에도 기능 설명이 없어, 추가 전에는 근거가 항목 소개 한 줄뿐이었다. Lombok 행은 추가 직후 같은 스크립트로 이 항목만 잰 값이다.
- oauth2-client, rabbitmq는 Boot 문서에 이미 해당 설정이 설명돼 있어 차이가 작다.
- 처음 측정에서 session-data-redis는 ✗였다. 원문에 이 질문을 다룬 가이드(`guides/boot-findbyusername.adoc`)가 있는데, 수집 후보 점수가 검색어 등장 횟수의 합이라 흔한 검색어("spring session")가 긴 문서에서 점수를 독차지해 가이드가 후보 10개 밖으로 밀렸다. 검색어 하나의 본문 횟수를 10까지만 세고(`term_cap`), 문서 고르기 프롬프트에 "프로젝트 문서도 고를 수 있다, 주제를 제목으로 직접 다룬 가이드를 먼저"를 넣은 뒤 ✓가 됐다. mongodb도 △ → ✓.

**한계**: 질문마다 1회 측정이다. security처럼 같은 질문도 실행마다 답이 달라질 수 있다.

**답변 모델을 `gpt-6.1-sol`로 바꾼 뒤**: 같은 14개 질문의 판정이 같다 (✗/△ → ✓ 11개, security ✗ → △, oauth2-client·rabbitmq 둘 다 ✓). 키워드 자동 판정은 data-jdbc의 Boot 문서만 답을 O로 봤지만, 전문은 join 가능 여부를 "확인되지 않는다"로 답해 △로 확정했다.

## 5. 답변 전문 (`gpt-6.1-sol`)

### 1. Spring for Apache Kafka · 4.0.x

**질문**: JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나? KafkaProperties의 패키지는?

**LLM만**

**Spring Boot 4.0.x 기준**, Kafka 메시지의 JSON 값 역직렬화에는 Jackson 3 기반의 **`JacksonJsonDeserializer`**를 사용합니다.

- **JSON 값 역직렬화 클래스**
  ```java
  org.springframework.kafka.support.serializer.JacksonJsonDeserializer
  ```
  ```yaml
  spring:
    kafka:
      consumer:
        value-deserializer: org.springframework.kafka.support.serializer.JacksonJsonDeserializer
  ```

- **`KafkaProperties` 패키지**
  ```java
  import org.springframework.boot.kafka.autoconfigure.KafkaProperties;
  ```

기존 예제의 `JsonDeserializer`나 `org.springframework.boot.autoconfigure.kafka.KafkaProperties`는 이전 버전 기준이므로 구분해야 합니다.

**RAG**

Spring Boot 4.0.x 기준으로, 두 질문에 각각 답하면 다음과 같습니다.

1. **JSON 값 역직렬화 설정에 사용하는 클래스**  
   `org.springframework.kafka.support.serializer.JacksonJsonDeserializer`를 사용합니다. `spring.kafka.consumer.value-deserializer`에 이 클래스의 전체 이름을 지정합니다. [근거 2]

2. **`KafkaProperties`의 패키지**  
   전체 클래스 이름은 `org.springframework.boot.kafka.autoconfigure.KafkaProperties`이므로, 패키지는 `org.springframework.boot.kafka.autoconfigure`입니다. [근거 4]

### 2. Spring for Apache Kafka · 3.5.x

**질문**: JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나? KafkaProperties의 패키지는?

**LLM만**

Spring Boot 3.5.x 기준, Kafka 메시지의 JSON 값 역직렬화에는 Spring Kafka의 `JsonDeserializer`를 사용합니다.

- **JSON 값 역직렬화 클래스**: `org.springframework.kafka.support.serializer.JsonDeserializer`
- **`KafkaProperties`의 패키지**: `org.springframework.boot.autoconfigure.kafka`
  - 전체 클래스명: `org.springframework.boot.autoconfigure.kafka.KafkaProperties`

설정 예시는 다음과 같습니다.

```yaml
spring:
  kafka:
    consumer:
      value-deserializer: org.springframework.kafka.support.serializer.JsonDeserializer
```

**RAG**

Spring Boot 3.5.x 기준으로 각각 답하면 다음과 같다.

1. **JSON 값 역직렬화에 사용하는 클래스**  
   `org.springframework.kafka.support.serializer.JsonDeserializer`를 사용한다. `spring.kafka.consumer.value-deserializer`에 이 클래스의 전체 이름을 설정한다. [근거 2]

2. **`KafkaProperties`의 패키지**  
   전체 클래스 이름은 `org.springframework.boot.autoconfigure.kafka.KafkaProperties`이며, 패키지는 `org.springframework.boot.autoconfigure.kafka`다. [근거 3]

### 3. Spring Web · 4.0.x

**질문**: JSON 직렬화(Jackson)를 설정할 때 쓰는 패키지는?

**LLM만**

Spring Boot 4.0.x 기준, 기본 JSON 라이브러리는 **Jackson 3**이며, JSON 직렬화 설정에 사용하는 핵심 패키지는 **`tools.jackson.databind`**입니다.

용도별로 구분하면 다음과 같습니다.

| 용도 | 패키지 / 대표 클래스 |
|---|---|
| Jackson 직렬화·역직렬화 API | `tools.jackson.databind` |
| JSON 매퍼 설정 | `tools.jackson.databind.json.JsonMapper` |
| Spring Boot의 Jackson 자동 설정·커스터마이징 | `org.springframework.boot.jackson.autoconfigure` |
| `@JsonIgnore`, `@JsonProperty` 등의 애너테이션 | `com.fasterxml.jackson.annotation` |

즉, **Jackson 2의 `com.fasterxml.jackson.databind`와 혼동하지 않아야 합니다.** 다만 애너테이션 패키지는 Jackson 3에서도 `com.fasterxml.jackson.annotation`을 사용합니다.

**RAG**

Spring Boot 4.0.x 기준, Jackson JSON 설정 대상인 `tools.jackson.databind.json.JsonMapper`의 패키지는 **`tools.jackson.databind.json`**이다. Jackson이 클래스패스에 있으면 이 클래스의 빈이 자동 구성되며, 설정 속성으로 구성을 조정할 수 있다. [근거 6]

커스텀 직렬화·역직렬화를 뜻한다면, `org.springframework.boot.jackson.ObjectValueSerializer`와 `org.springframework.boot.jackson.ObjectValueDeserializer`의 패키지는 **`org.springframework.boot.jackson`**이다. [근거 8]

### 4. SpringDoc OpenAPI · 3.5.x

**질문**: Swagger UI 경로를 바꾸려면 어떤 속성을 쓰나?

**LLM만**

Spring Boot 3.5.x 기준, SpringDoc OpenAPI의 Swagger UI 경로는 **`springdoc.swagger-ui.path`** 속성으로 변경합니다.

```yaml
springdoc:
  swagger-ui:
    path: /docs
```

이렇게 설정하면 `/docs`로 접속해 Swagger UI를 열 수 있습니다. 기본값은 `/swagger-ui.html`입니다.

참고로 OpenAPI JSON 문서 경로는 별도 속성인 `springdoc.api-docs.path`로 설정합니다.

**RAG**

Spring Boot 3.5.x 기준, Swagger UI 경로를 바꾸려면 `springdoc.swagger-ui.path` 속성을 사용한다. 기본값은 `/swagger-ui.html`이다. [근거 3]

예를 들어 `/api-docs-ui.html`로 변경하려면 다음과 같이 설정한다. [근거 3]

```properties
springdoc.swagger-ui.path=/api-docs-ui.html
```

### 5. Spring for Apache Pulsar · 4.0.x

**질문**: 리액티브 Pulsar 스타터(spring-boot-starter-pulsar-reactive)를 쓸 수 있나?

**LLM만**

Spring Boot 4.0.x 기준으로 `spring-boot-starter-pulsar-reactive`는 더 이상 제공되지 않습니다.

Spring Boot 4.0에서 사용하는 **Spring for Apache Pulsar 2.0이 리액티브 지원을 제거**했기 때문에, Boot의 리액티브 Pulsar 스타터와 관련 자동 구성도 제거되었습니다.

대신 일반 Pulsar 스타터를 사용해야 합니다.

```gradle
implementation("org.springframework.boot:spring-boot-starter-pulsar")
```

이 스타터에서는 `PulsarTemplate`, `@PulsarListener` 등을 사용할 수 있지만, 기존의 `ReactivePulsarTemplate` 같은 리액티브 API를 제공하지는 않습니다. **이전 버전의 리액티브 스타터를 Boot 4.0.x에 섞어 사용하는 것은 권장하지 않습니다.**

**RAG**

Spring Boot 4.0.x 기준, 제공된 문서에서는 `spring-boot-starter-pulsar-reactive`의 제공 여부나 사용 가능 여부가 **문서에서 확인되지 않는다**.

문서에 명시된 스타터는 `spring-boot-starter-pulsar`이며, Spring for Apache Pulsar 사용에 필요한 의존성을 모으는 용도로 제공된다. [근거 2] 따라서 제공된 근거만으로는 리액티브 스타터를 사용할 수 있다고 단정할 수 없다.

### 6. Spring for Apache Kafka · 4.0.x

**질문**: Kafka 브로커에 권장되는 JVM 힙 메모리 크기는?

**LLM만**

Spring Boot 4.0.x 기준, **Spring for Apache Kafka 자체는 Kafka 브로커의 JVM 힙 크기를 지정하거나 권장하지 않습니다.** 브로커는 Spring Boot 애플리케이션과 별도로 설정합니다.

일반적인 운영 환경에서는 **브로커당 6GB 힙을 시작점으로 권장**합니다. 이는 Confluent의 운영 환경 권장값이며, 모든 환경에 적용되는 고정값은 아닙니다.

```bash
export KAFKA_HEAP_OPTS="-Xms6g -Xmx6g"
```

- **서버 메모리 전체를 힙에 할당하지 않습니다.** Kafka는 OS 페이지 캐시를 적극 활용하므로 여유 메모리가 중요합니다.
- 실제 크기는 파티션 수, 메시지 크기, 처리량, GC 상태를 관찰하며 조정합니다.
- 위 설정은 **Kafka 브로커용**이며, Spring Boot의 Kafka 프로듀서·컨슈머 애플리케이션 힙 권장값이 아닙니다.

**RAG**

Spring Boot 4.0.x 기준, 제공된 문서에서 Kafka 브로커에 권장되는 JVM 힙 메모리 크기는 문서에서 확인되지 않는다.
