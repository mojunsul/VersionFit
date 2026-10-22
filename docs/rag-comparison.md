# RAG 전후 비교 (F2015)

2026-10-22 측정, 같은 날 질문별 문서 범위 검색·MMR lambda_mult 0.6으로 바꾼 뒤 재측정 (판정 같음, 답변 전문은 재측정 결과). 검색 질의에 영어 검색어를 붙인 뒤(rag-design.md 6.1-1), 외부 문서(Spring Kafka 등)를 추가하고 항목 자체 Boot 문서 근거를 먼저 확보하게 한 뒤(6.1-2), 답변 규칙에 "근거의 기능으로 해결 방법이 분명하면 먼저 설명"을 넣은 뒤에도 판정은 같다. 재현: `python -m scripts.compare_rag`

## 1. 방법

- 같은 모델(`gpt-5.4-mini`)로 같은 질문에 두 번 답한다.
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
