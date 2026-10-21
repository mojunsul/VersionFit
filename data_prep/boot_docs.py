"""spring-boot 저장소의 공식 문서(AsciiDoc)를 버전별로 받아 로컬에 두고, 검색어로 후보 문서를 찾는다. (F2004)

원문은 GitHub에서 한 번만 받아 `paths.boot_docs_dir`에 저장한다. 서비스는 이 사본만 읽는다.
"""
import re
import time
from pathlib import Path

import requests

from config import CONFIG, ROOT

# 지원 버전(브랜치) → Antora 모듈 상위 경로. 4.x와 3.2~3.5의 문서 위치가 다르다.
VERSIONS = {
    "4.1.x": "documentation/spring-boot-docs/src/docs/antora/modules",
    "4.0.x": "documentation/spring-boot-docs/src/docs/antora/modules",
    "3.5.x": "spring-boot-project/spring-boot-docs/src/docs/antora/modules",
    "3.4.x": "spring-boot-project/spring-boot-docs/src/docs/antora/modules",
}
# Initializr 문서 링크가 가리키는 모듈 전부 (reference 66, how-to 6, specification 1)
MODULES = ("reference", "how-to", "specification")

REPO = "spring-projects/spring-boot"
HEADERS = {"User-Agent": "ssafy-rag-project/0.1 (student project)"}
INTERVAL = 1.1  # NF2006: 호출 간격 1초 이상
_last_call = 0.0


def _get(url: str, **headers) -> requests.Response:
    global _last_call
    for attempt in range(3):
        time.sleep(max(0.0, _last_call + INTERVAL - time.monotonic()))
        _last_call = time.monotonic()
        try:
            resp = requests.get(url, headers={**HEADERS, **headers}, timeout=30)
        except requests.RequestException:
            if attempt == 2:
                raise
            continue
        if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
            raise RuntimeError("GitHub API 호출 한도(시간당 60회)를 넘었습니다. 한 시간 뒤 다시 실행하세요.")
        if resp.status_code < 500 or attempt == 2:
            resp.raise_for_status()
            return resp
    raise AssertionError("unreachable")


def docs_dir(version: str) -> Path:
    return ROOT / CONFIG["paths"]["boot_docs_dir"] / version


def download(version: str) -> int:
    """버전의 문서 목록을 Trees API로 받고, 아직 없는 파일만 raw로 받는다. 받은 파일 수를 돌려준다."""
    base = VERSIONS[version]
    tree = _get(f"https://api.github.com/repos/{REPO}/git/trees/{version}?recursive=1",
                Accept="application/vnd.github+json").json()
    doc_ids = [t["path"][len(base) + 1:] for t in tree["tree"]
               if t["path"].startswith(base + "/") and t["path"].endswith(".adoc")]
    doc_ids = [d for d in doc_ids if d.split("/")[0] in MODULES and "/pages/" in d]
    fetched = 0
    for doc_id in doc_ids:
        path = docs_dir(version) / doc_id
        if path.exists():
            continue
        text = _get(f"https://raw.githubusercontent.com/{REPO}/{version}/{base}/{doc_id}").text
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        fetched += 1
    return fetched


def clean(text: str) -> str:
    """AsciiDoc 매크로를 읽을 수 있는 글로 바꾼다. javadoc은 패키지 전체 이름을 남긴다(버전별 패키지 차이가 답이 된다)."""
    text = re.sub(r"(?m)^\[\[[^\]]+\]\]\n", "", text)
    # 외부 javadoc 속성 접두사({url-...-javadoc}/)는 버리고, 멤버 참조(Class#method(...))는 남긴다
    text = re.sub(r"javadoc:(?:\{[^}]+\}/)?([^\s\[]+)\[([^\]]*)\]", lambda m: m[2] or f"`{m[1]}`", text)
    text = re.sub(r"configprop:([\w.\-\[\]*]+?)\[[^\]]*\]", r"`\1`", text)
    # javadoc을 먼저 바꿔야 표시문 안의 [] 중첩이 사라진다
    text = re.sub(r"xref:([^\[\s]+)\[([^\]]*)\]", lambda m: m[2] or m[1].split("#")[-1], text)
    return text


def load_docs(version: str) -> dict[str, str]:
    """로컬 사본을 {doc_id: 정리된 본문}으로 읽는다. doc_id 예: reference/pages/messaging/kafka.adoc"""
    root = docs_dir(version)
    return {p.relative_to(root).as_posix(): clean(p.read_text(encoding="utf-8"))
            for p in sorted(root.rglob("*.adoc"))}


def search(docs: dict[str, str], terms: list[str], limit: int) -> list[str]:
    """검색어가 경로·본문에 나오는 횟수로 후보 doc_id를 고른다. 경로 일치는 문서 주제라서 가중치를 크게 준다."""
    scores = {}
    for doc_id, text in docs.items():
        body, path = text.lower(), doc_id.lower()
        score = sum(body.count(t.lower()) + 20 * path.count(t.lower()) for t in terms if t.strip())
        if score:
            scores[doc_id] = score
    return sorted(scores, key=scores.get, reverse=True)[:limit]


def doc_title(text: str) -> str:
    m = re.search(r"(?m)^= (.+)$", text)
    return m[1].strip() if m else ""


def doc_id_for_item(doc_url: str) -> str | None:
    """Initializr의 doc_url 템플릿을 doc_id로 바꾼다. Boot 문서 링크가 아니면 None."""
    m = re.match(r"https://docs\.spring\.io/spring-boot/\{bootVersion\}/([\w-]+)/([^#?]+)\.html", doc_url)
    return f"{m[1]}/pages/{m[2]}.adoc" if m else None


def source_url(version: str, doc_id: str) -> str:
    module, page = doc_id.removesuffix(".adoc").split("/pages/", 1)
    return f"https://docs.spring.io/spring-boot/{version.removesuffix('.x')}/{module}/{page}.html"


def repo_url(version: str, doc_id: str) -> str:
    return f"https://github.com/{REPO}/blob/{version}/{VERSIONS[version]}/{doc_id}"
