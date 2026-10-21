from __future__ import annotations
import html
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from api.quiz_models import (
    BLANK_TYPES,
    GROUP_TYPES,
    SELECTION_TYPES,
    SKIP_TYPES,
    Answer,
    AnswerPlan,
    AnswerSource,
    Option,
    Question,
    QuestionType,
)

_TAG_RE = re.compile(r"<[^>]+>")
_BLANK_MARKER_RE = re.compile(r"__blank__|_{2,}|＿{2,}")

_QTYPE_MAP = {
    "single_selection": QuestionType.SINGLE,
    "single": QuestionType.SINGLE,
    "multiple_selection": QuestionType.MULTIPLE,
    "multiple": QuestionType.MULTIPLE,
    "true_or_false": QuestionType.TRUE_FALSE,
    "true_false": QuestionType.TRUE_FALSE,
    "fill_in_blank": QuestionType.FILL_BLANK,
    "fill_blank": QuestionType.FILL_BLANK,
    "completion": QuestionType.FILL_BLANK,
    "short_answer": QuestionType.SHORT_ANSWER,
    "essay": QuestionType.SHORT_ANSWER,
    "cloze": QuestionType.CLOZE,
    "matching": QuestionType.MATCHING,
    "media": QuestionType.MEDIA,
    "analysis": QuestionType.ANALYSIS,
    "paragraph_desc": QuestionType.SECTION,
}

_QTYPE_LABEL_ZH = {
    QuestionType.SINGLE: "單選題",
    QuestionType.MULTIPLE: "多選題",
    QuestionType.TRUE_FALSE: "是非題",
    QuestionType.FILL_BLANK: "填空題",
    QuestionType.SHORT_ANSWER: "簡答題",
    QuestionType.CLOZE: "克漏字",
    QuestionType.MATCHING: "配對題",
    QuestionType.MEDIA: "題組題",
    QuestionType.ANALYSIS: "綜合題",
}


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def strip_html_tags(value: Any) -> str:
    return normalize_text(html.unescape(_TAG_RE.sub(" ", str(value or ""))))


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def option_label(index: int) -> str:
    """0 -> 'A', 1 -> 'B', ..."""
    if index < 26:
        return chr(ord("A") + index)
    return "A" + chr(ord("A") + (index % 26))


def map_qtype(value: Any) -> QuestionType:
    return _QTYPE_MAP.get(normalize_text(value).lower(), QuestionType.UNKNOWN)


def _matching_sub_options(container_options: Any, sub_index: int, sub_count: int) -> List[Dict[str, Any]]:
    opts = sorted(
        (o for o in (container_options or []) if isinstance(o, dict)),
        key=lambda o: _as_int(o.get("id")),
    )
    k = (len(opts) // sub_count) if sub_count else 0
    if k <= 0:
        return opts
    return opts[sub_index * k : (sub_index + 1) * k]


def parse_question(raw: Dict[str, Any], parent_id: int = 0) -> Question:
    options = []
    for opt in raw.get("options") or []:
        if not isinstance(opt, dict):
            continue
        options.append(
            Option(
                id=_as_int(opt.get("id")),
                content=strip_html_tags(opt.get("content")),
                is_answer=opt.get("is_answer") if "is_answer" in opt else None,
                sort=_as_int(opt.get("sort")),
            )
        )
    qtype = map_qtype(raw.get("type"))
    raw_correct = raw.get("correct_answers")
    correct_texts: Tuple[str, ...] = ()
    if isinstance(raw_correct, list):
        ordered = sorted(
            (c for c in raw_correct if isinstance(c, dict)),
            key=lambda c: _as_int(c.get("sort")),
        )
        correct_texts = tuple(strip_html_tags(c.get("content")) for c in ordered)
    blank_count = _as_int(raw.get("answer_number"))
    if not blank_count and qtype in BLANK_TYPES:
        markers = len(_BLANK_MARKER_RE.findall(str(raw.get("description") or "")))
        blank_count = markers or len(correct_texts) or 1

    return Question(
        subject_id=_as_int(raw.get("id") or raw.get("subject_id")),
        qtype=qtype,
        stem=strip_html_tags(raw.get("description") or raw.get("content") or raw.get("stem")),
        options=tuple(options),
        blank_count=blank_count,
        correct_texts=correct_texts,
        parent_id=parent_id,
    )


def parse_questions(raw_subjects: Any) -> List[Question]:
    out: List[Question] = []
    for raw in raw_subjects or []:
        if not isinstance(raw, dict):
            continue
        qtype = map_qtype(raw.get("type"))
        if qtype in SKIP_TYPES:
            continue
        subs = [
            s
            for s in (raw.get("sub_subjects") or [])
            if isinstance(s, dict) and map_qtype(s.get("type")) not in SKIP_TYPES
        ]
        if qtype == QuestionType.MATCHING:
            parent_id = _as_int(raw.get("id") or raw.get("subject_id"))
            if not subs:
                out.append(parse_question(raw))
                continue
            subs = sorted(subs, key=lambda s: _as_int(s.get("id")))
            for i, sub in enumerate(subs):
                block = sub.get("options") or _matching_sub_options(raw.get("options"), i, len(subs))
                out.append(
                    parse_question(
                        dict(sub, options=block, type="single_selection"),
                        parent_id=parent_id,
                    )
                )
            continue
        if qtype in GROUP_TYPES or subs:
            for sub in subs:
                out.append(parse_question(sub))
            continue
        out.append(parse_question(raw))
    return out


def _mk(question: Question, **kw: Any) -> Answer:
    return Answer(
        subject_id=question.subject_id,
        parent_id=question.parent_id,
        answer_type=question.qtype.value,
        **kw,
    )


def _replay_answer(question: Question) -> Optional[Answer]:
    if question.correct_option_ids:
        return _mk(question, answer_option_ids=question.correct_option_ids)
    if question.correct_texts:
        if question.is_blank:
            return _mk(question, blanks=tuple((i, t) for i, t in enumerate(question.correct_texts)))
        return _mk(question, answer_text=question.correct_texts[0])
    return None


def decide_paper(questions: Iterable[Question]) -> AnswerPlan:
    answers: List[Answer] = []
    pending: List[Question] = []
    saw_replay = False

    for question in questions:
        replay = _replay_answer(question)
        if replay is not None:
            answers.append(replay)
            saw_replay = True
        else:
            pending.append(question)

    if pending:
        source = AnswerSource.LLM
    elif saw_replay:
        source = AnswerSource.REPLAY
    else:
        source = AnswerSource.NONE
    return AnswerPlan(source=source, answers=tuple(answers), pending=tuple(pending))


def parse_choice_labels(text: str, option_count: int) -> List[str]:
    if option_count <= 0:
        return []
    valid = {option_label(i) for i in range(option_count)}
    text = normalize_text(text)
    found: List[str] = []
    for ch in re.findall(r"(?<![A-Za-z])([A-Z])(?![A-Za-z])", text):
        if ch in valid and ch not in found:
            found.append(ch)
    if found:
        return found
    compact = re.sub(r"[^A-Za-z]", "", text).upper()
    if compact and len(compact) <= option_count and all(ch in valid for ch in compact):
        for ch in compact:
            if ch not in found:
                found.append(ch)
    return found


def match_choice_by_content(question: Question, reply_text: str) -> List[str]:
    reply = strip_html_tags(reply_text).lower()
    if not reply:
        return []
    contents = [(i, strip_html_tags(o.content).lower()) for i, o in enumerate(question.options)]
    exact = [option_label(i) for i, c in contents if c and c == reply]
    if exact:
        return exact
    return [option_label(i) for i, c in contents if c and c in reply]


def answer_from_labels(question: Question, labels: Iterable[str]) -> Answer:
    indices: List[int] = []
    for label in labels:
        idx = ord(normalize_text(label).upper()[:1] or "?") - ord("A")
        if 0 <= idx < len(question.options) and idx not in indices:
            indices.append(idx)
    if question.qtype in (QuestionType.SINGLE, QuestionType.TRUE_FALSE):
        indices = indices[:1]
    option_ids: Tuple[int, ...] = tuple(question.options[i].id for i in indices)
    return _mk(question, answer_option_ids=option_ids)


def parse_blank_answers(text: str, count: int) -> List[str]:
    text = normalize_text(text)
    parts = [p.strip() for p in re.split(r"\s*\|\|\|\s*|\n+", text) if p.strip()]
    if not parts and text:
        parts = [text]
    if count > 0:
        parts = (parts + [""] * count)[:count]
    return parts


def answer_from_blanks(question: Question, reply_text: str) -> Answer:
    parts = parse_blank_answers(reply_text, question.blank_count or 0)
    return _mk(question, blanks=tuple((i, p) for i, p in enumerate(parts)))


def answer_from_llm_reply(question: Question, reply_text: str) -> Answer:
    if (question.is_selection or question.qtype == QuestionType.MATCHING) and question.options:
        labels = parse_choice_labels(reply_text, len(question.options))
        if not labels:
            labels = match_choice_by_content(question, reply_text)
        return answer_from_labels(question, labels)
    if question.is_blank:
        return answer_from_blanks(question, reply_text)
    return _mk(question, answer_text=normalize_text(reply_text))


def is_answered(answer: Answer) -> bool:
    if answer.answer_option_ids:
        return True
    if normalize_text(answer.answer_text):
        return True
    return any(normalize_text(content) for _sort, content in answer.blanks)


def format_answer_canonical(question: Question, answer: Answer) -> str:
    if (question.is_selection or question.qtype == QuestionType.MATCHING) and question.options:
        index_by_id = {opt.id: i for i, opt in enumerate(question.options)}
        letters = [option_label(index_by_id[oid]) for oid in answer.answer_option_ids if oid in index_by_id]
        return ",".join(letters) if letters else "(未作答)"
    if question.is_blank or answer.blanks:
        blanks_text = " ||| ".join(strip_html_tags(c) for _, c in answer.blanks)
        return blanks_text if blanks_text else "(未作答)"
    return strip_html_tags(answer.answer_text) or "(未作答)"


def format_answer_with_content(question: Question, answer: Optional[Answer]) -> str:
    if not answer:
        return "(未作答)"
    if (question.is_selection or question.qtype == QuestionType.MATCHING) and question.options:
        chosen = []
        for idx, opt in enumerate(question.options):
            if opt.id in answer.answer_option_ids:
                lbl = option_label(idx)
                content = strip_html_tags(opt.content)
                if content:
                    chosen.append(f"{lbl}. {content}")
                else:
                    chosen.append(lbl)
        return ", ".join(chosen) if chosen else "(未作答)"
    if question.is_blank or answer.blanks:
        blanks_text = " ||| ".join(strip_html_tags(c) for _, c in answer.blanks)
        return blanks_text if blanks_text else "(未作答)"
    return strip_html_tags(answer.answer_text) or "(未作答)"


def format_paper_canonical(questions: Iterable[Question], answers: Iterable[Answer]) -> str:
    by_id = {a.subject_id: a for a in answers}
    groups: Dict[str, List[str]] = {}
    for index, question in enumerate(questions, 1):
        ans = by_id.get(question.subject_id)
        rendered = format_answer_canonical(question, ans) if ans is not None else "(未作答)"
        label = _QTYPE_LABEL_ZH.get(question.qtype, "其他")
        groups.setdefault(label, []).append(f"{index}. {rendered}")
    return "\n".join(f"**{label}**：{'  '.join(cells)}" for label, cells in groups.items())


def format_paper_qa(questions: Iterable[Question], answers: Iterable[Answer]) -> str:
    by_id = {a.subject_id: a for a in answers}
    lines: List[str] = []
    for index, q in enumerate(questions, 1):
        ans = by_id.get(q.subject_id)
        ans_repr = format_answer_with_content(q, ans)
        stem = q.stem or "(題目)"
        lines.append(f"**{index}. Q**: {stem}\n   **A**: {ans_repr}")
    return "\n\n".join(lines)


def format_paper_detailed_markdown(
    title: str, course_name: str, questions: List[Question], answers: List[Answer]
) -> str:
    by_id = {a.subject_id: a for a in answers}
    lines = [
        f"# 測驗解答清單: {title}",
        f"**課程**: {course_name}",
        f"**總題數**: {len(questions)} 題",
        "",
        "---",
        "",
    ]

    for idx, q in enumerate(questions, 1):
        ans = by_id.get(q.subject_id)
        ans_repr = format_answer_canonical(q, ans) if ans else "(未作答)"
        qtype_zh = _QTYPE_LABEL_ZH.get(q.qtype, q.qtype.value)

        lines.append(f"### 第 {idx} 題 [{qtype_zh}]")
        lines.append(f"**題目**: {q.stem or '(無題目內文)'}")

        if q.options:
            lines.append("**選項**:")
            for o_idx, opt in enumerate(q.options):
                lbl = option_label(o_idx)
                selected_mark = " ✅" if (ans and opt.id in ans.answer_option_ids) else ""
                lines.append(f"- **{lbl}**. {opt.content}{selected_mark}")

        lines.append(f"**AI 解答**: `{ans_repr}`")
        lines.append("")

    return "\n".join(lines)
