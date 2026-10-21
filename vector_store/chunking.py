"""문서를 헤더 단위로 나눈 뒤 청크 크기·중복 설정에 맞춰 자른다. 코드 블록은 중간에 자르지 않는다. (F2005)

AsciiDoc 헤더용 분할기가 langchain-text-splitters에 없고, 글자 수 분할기는 코드 블록을 자를 수 있어 직접 나눈다.
"""
import re

from config import CONFIG

HEADING = re.compile(r"^(={1,4}) (\S.*)$")
DELIMITERS = {"----", "....", "|==="}  # 코드·리터럴·표 블록. 안의 '=' 줄과 빈 줄은 구조가 아니다


def _sections(text: str) -> list[tuple[str, list[str]]]:
    """[(헤더 경로, 블록 목록)]. 블록은 빈 줄로 나뉜 문단이고, 구분자 블록은 통째로 한 블록에 든다."""
    sections, path, blocks, lines, fence = [], [], [], [], None

    def end_block():
        if lines:
            blocks.append("\n".join(lines))
            lines.clear()

    def end_section():
        end_block()
        if blocks:
            sections.append((" > ".join(t for _, t in path), blocks.copy()))
            blocks.clear()

    for line in text.splitlines():
        s = line.rstrip()
        if fence:
            lines.append(line)
            fence = None if s == fence else fence
        elif s in DELIMITERS:
            lines.append(line)
            fence = s
        elif m := HEADING.match(s):
            end_section()
            level = len(m[1])
            path = [(lv, t) for lv, t in path if lv < level] + [(level, m[2].strip())]
        elif not s:
            end_block()
        else:
            lines.append(line)
    end_section()
    return sections


def _joined_len(blocks: list[str]) -> int:
    return sum(map(len, blocks)) + 2 * max(len(blocks) - 1, 0)


def _split_long(block: str, budget: int) -> list[str]:
    """빈 줄 없이 이어진 긴 문단(목록 등)은 줄 단위로 나눈다. 구분자 블록은 그대로 둔다."""
    lines = block.splitlines()
    if len(block) <= budget or any(l.rstrip() in DELIMITERS for l in lines):
        return [block]
    parts, cur = [], ""
    for line in lines:
        if cur and len(cur) + 1 + len(line) > budget:
            parts.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    return parts + [cur]


def chunk(text: str) -> list[str]:
    """청크마다 앞에 헤더 경로를 붙인다. 청크만 검색돼도 어느 섹션인지 알 수 있게 한다."""
    size, overlap = CONFIG["chunk"]["size"], CONFIG["chunk"]["overlap"]
    chunks = []
    for heading, blocks in _sections(text):
        prefix = f"{heading}\n\n" if heading else ""
        budget = size - len(prefix)
        cur = []
        for block in (p for b in blocks for p in _split_long(b, budget)):
            if cur and _joined_len(cur + [block]) > budget:
                chunks.append(prefix + "\n\n".join(cur))
                tail = []
                while cur and _joined_len([cur[-1]] + tail) <= overlap:
                    tail.insert(0, cur.pop())
                cur = tail if _joined_len(tail + [block]) <= budget else []
            # shortcut: 크기를 넘는 단일 블록(긴 코드·표)은 자르지 않고 한 청크로 둔다. 검색 품질이 떨어지면 줄 단위 분할 추가
            cur.append(block)
        if cur:
            chunks.append(prefix + "\n\n".join(cur))
    return chunks
