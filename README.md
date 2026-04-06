# Travel Agent PoC — LangGraph 기반 여행 추천 에이전트

LangGraph StateGraph를 활용한 여행지 추천 AI 에이전트 PoC.
9개 노드로 구성된 순차 파이프라인이 날씨 조회, 장소 검색, 실내/실외 분류, 태그 매칭, 벡터 검색, 점수 산출, 경로 최적화, 응답 생성까지를 자동으로 수행한다.

---

## 아키텍처

```
parse_request
      │
      ▼
fetch_weather
      │
      ▼
search_places ──(결과 없음)──▶ generate_response ──▶ END
      │
      ▼
filter_places        ← Gemini (Tier 3 실내/외 판단)
      │
      ▼
match_tags
      │
      ▼
vector_search
      │
      ▼
score_and_select
      │
      ▼
optimize_route
      │
      ▼
generate_response    ← Gemini (추천 이유 생성)
      │
      ▼
     END
```

### 노드별 역할

| 노드 | 역할 | LLM 사용 |
|------|------|---------|
| `parse_request` | 요청 파싱, 날짜 기본값 설정 | - |
| `fetch_weather` | 날씨 조회 (Mock: 맑음 22°C) | - |
| `search_places` | 장소 검색 (Mock: 서울 10곳) | - |
| `filter_places` | 실내/실외 분류 (Tier 1-2 규칙 + Tier 3 Gemini) | O |
| `match_tags` | 태그 매칭 점수 (Mock: 랜덤) | - |
| `vector_search` | 의미 검색 유사도 (Mock: 랜덤) | - |
| `score_and_select` | 가중 점수 산출 및 Top-N 선정 | - |
| `optimize_route` | 최근접 이웃 경로 최적화 (Mock: haversine) | - |
| `generate_response` | 추천 이유 자연어 생성 | O |

### 점수 공식

```
최종 점수 = (태그 매칭 × 0.4) + (벡터 유사도 × 0.4) + (날씨 적합도 × 0.2)
```

- 날씨 적합도: 악천후+실내 또는 맑음+실외 → 1.0, 그 외 → 0.5

---

## 실제 연동 vs Mock

| 컴포넌트 | 상태 | 비고 |
|---------|------|------|
| Gemini 2.0 Flash | **실제 연동** | 실내/실외 분류 + 추천 이유 생성 |
| OpenWeatherMap | Mock | 맑음 22°C 고정 반환 |
| TourAPI | Mock | 서울 주요 장소 10곳 하드코딩 |
| 태그 매칭 (DB) | Mock | 랜덤 점수 0.2~0.9 |
| 벡터 검색 (pgvector) | Mock | 랜덤 유사도 0.3~0.95 |
| 경로 최적화 (네이버) | Mock | haversine 직선거리 기반 |

---

## 사전 요구 사항

- **Python 3.11 이상** (3.12 권장)
- **Gemini API 키** — https://aistudio.google.com/apikey 에서 무료 발급
- **LangSmith 계정** (LangGraph Studio 사용 시) — https://smith.langchain.com

---

## 설치

```bash
# 1. 저장소 클론
git clone <repository-url>
cd travel-agent-poc

# 2. 가상환경 생성 (권장)
python3 -m venv .venv
source .venv/bin/activate

# 3. 의존성 설치
pip install -e ".[dev]"

# 4. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 GEMINI_API_KEY 값 입력
```

### 환경 변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `GEMINI_API_KEY` | O | Google Gemini API 키. 미설정 시 LLM 기능이 fallback으로 동작 |
| `OPENWEATHER_API_KEY` | X | 향후 실제 날씨 연동용 (현재 Mock) |
| `TOURAPI_SERVICE_KEY` | X | 향후 실제 장소 검색 연동용 (현재 Mock) |

> `GEMINI_API_KEY` 없이도 실행 가능. LLM이 필요한 Tier 3 분류는 기본값("outdoor")으로 대체되고, 추천 이유는 빈 문자열로 반환된다.

---

## 실행

### 1. FastAPI 서버

```bash
uvicorn main:app --reload --port 8000
```

API 문서 확인: http://localhost:8000/docs

### 2. LangGraph Studio (그래프 시각화)

```bash
# langgraph-cli[inmem] 설치 확인
pip install -U "langgraph-cli[inmem]"

# Studio 실행 (--allow-blocking: Gemini SDK 동기 호출 허용)
langgraph dev --allow-blocking
```

- API 서버: http://127.0.0.1:2024
- Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- LangSmith 로그인 필요

---

## API 사용법

### POST /api/v1/recommend

```bash
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 37.5665,
    "longitude": 126.978,
    "travel_date": "2026-04-06",
    "mobility_type": "walk",
    "selected_tags": ["#힐링", "#조용한"],
    "free_text": "공원 근처 조용한 곳",
    "num_places": 5
  }'
```

### 요청 필드

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `latitude` | float | (필수) | 위도 |
| `longitude` | float | (필수) | 경도 |
| `travel_date` | string | 오늘 | 여행 날짜 (YYYY-MM-DD) |
| `mobility_type` | string | "walk" | 이동 수단 (walk / transit / car) |
| `selected_tags` | list[str] | [] | 선호 태그 |
| `free_text` | string | "" | 자연어 검색 쿼리 |
| `num_places` | int | 5 | 추천 장소 수 |

### 응답 예시

```json
{
  "places": [
    {
      "content_id": "567890",
      "name": "청계천",
      "address": "서울특별시 종로구 청계천로",
      "latitude": 37.5696,
      "longitude": 126.9784,
      "indoor_outdoor": "outdoor",
      "tag_score": 0.85,
      "vector_score": 0.72,
      "weather_score": 1.0,
      "total_score": 0.828,
      "overview": "도심을 관통하는 생태 하천으로 산책과 휴식에 좋습니다."
    }
  ],
  "route": {
    "ordered_places": [...],
    "legs": [
      {
        "from_place": "청계천",
        "to_place": "경복궁",
        "distance_m": 1200,
        "duration_min": 15
      }
    ],
    "total_distance_m": 5400,
    "total_duration_min": 67
  },
  "weather": {
    "condition": "Clear",
    "temperature": 22.0,
    "feels_like": 21.5,
    "humidity": 45,
    "wind_speed": 2.3,
    "description": "맑음",
    "is_bad_weather": false,
    "icon": "01d"
  },
  "reasoning": "맑은 날씨에 야외 활동을 즐기기 좋은 장소들을 추천합니다..."
}
```

### GET /health

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

---

## LangGraph Studio 시연 가이드

Studio에서 그래프를 실행할 때 다음 JSON을 입력으로 사용한다:

```json
{
  "raw_request": {
    "latitude": 37.5665,
    "longitude": 126.978,
    "travel_date": "2026-04-06",
    "mobility_type": "walk",
    "selected_tags": ["#힐링", "#조용한"],
    "free_text": "공원 근처 조용한 곳",
    "num_places": 5
  }
}
```

**확인 포인트**:
- 9개 노드가 순차 실행되며 각 노드의 상태 변화를 State Inspector에서 확인
- `search_places` 노드의 조건 분기 (결과 있음 → `filter_places`, 결과 없음 → `generate_response`)
- `GEMINI_API_KEY` 설정 시 `generate_response`에서 자연어 추천 이유 생성

---

## 테스트

```bash
# 전체 테스트 실행
pytest tests/ -v

# 개별 테스트
pytest tests/test_graph.py::test_full_pipeline_returns_places -v
```

### 테스트 목록 (6개)

| 테스트 | 검증 내용 |
|--------|----------|
| `test_full_pipeline_returns_places` | 5개 장소 + 경로 + 날씨 정상 반환 |
| `test_places_have_required_fields` | 각 장소의 필수 필드 존재 여부 |
| `test_places_sorted_by_score` | 점수 내림차순 정렬 |
| `test_minimal_request_defaults` | 최소 입력(위도, 경도만)으로 정상 동작 |
| `test_scoring_formula` | 가중 점수 공식 정확성 |
| `test_no_results_branch` | 검색 결과 없을 때 조건 분기 동작 |

---

## 프로젝트 구조

```
travel-agent-poc/
├── langgraph.json              # LangGraph Studio 설정
├── pyproject.toml              # 패키지 메타데이터 + 의존성
├── .env.example                # 환경 변수 템플릿
├── .gitignore
├── main.py                     # FastAPI 앱 (POST /api/v1/recommend, GET /health)
├── config.py                   # pydantic-settings 환경 변수 + Gemini LLM 초기화
├── agent/
│   ├── state.py                # AgentState TypedDict (11개 상태 필드)
│   ├── graph.py                # StateGraph 빌드 + 컴파일 (Studio 진입점)
│   ├── nodes.py                # 9개 노드 함수
│   └── prompts.py              # Gemini 프롬프트 + asyncio.to_thread 래퍼
├── tools/
│   ├── weather.py              # Mock 날씨 (맑음 22°C)
│   ├── place_search.py         # Mock 장소 검색 (서울 10곳)
│   ├── place_filter.py         # 3단계 실내/실외 분류 (규칙 + LLM)
│   ├── tag_search.py           # Mock 태그 매칭
│   ├── vector_search.py        # Mock 벡터 검색
│   └── route_optimize.py       # Mock 경로 최적화 (haversine)
├── models/
│   └── schemas.py              # Pydantic 스키마 전체
└── tests/
    └── test_graph.py           # E2E 그래프 테스트 (6개)
```

---

## 기술 스택

| 구분 | 기술 | 버전 |
|------|------|------|
| 그래프 엔진 | LangGraph | >= 1.1.0 |
| LLM | Gemini 2.0 Flash (langchain-google-genai) | >= 4.2.1 |
| 웹 프레임워크 | FastAPI | >= 0.115.0 |
| 데이터 검증 | Pydantic | >= 2.10.0 |
| HTTP 클라이언트 | httpx | >= 0.28.0 |
| 시각화 | LangGraph Studio | langgraph-cli[inmem] |

---

## Mock → 실제 전환 체크리스트

실제 서비스로 전환할 때 교체가 필요한 항목:

- [ ] **날씨 조회**: `tools/weather.py` → OpenWeatherMap API 연동 (`OPENWEATHER_API_KEY` 필요)
- [ ] **장소 검색**: `tools/place_search.py` → TourAPI locationBasedList1 연동 (`TOURAPI_SERVICE_KEY` 필요)
- [ ] **태그 매칭**: `tools/tag_search.py` → PostgreSQL + place_tags 테이블 연동
- [ ] **벡터 검색**: `tools/vector_search.py` → pgvector + text-embedding-004 연동
- [ ] **경로 최적화**: `tools/route_optimize.py` → 네이버 Directions API 연동
