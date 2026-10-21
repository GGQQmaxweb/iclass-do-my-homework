from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class ActivityType(str, Enum):
    NONE = "none"
    EXAM = "exam"
    CLASSROOM_EXAM = "classroom_exam"
    COURSEWARE_QUIZ = "courseware_quiz"
    QUESTIONNAIRE = "questionnaire"
    VOTE = "vote"
    HOMEWORK = "homework"
    UNKNOWN = "unknown"


class QuestionType(str, Enum):
    SINGLE = "single_selection"
    MULTIPLE = "multiple_selection"
    TRUE_FALSE = "true_or_false"
    FILL_BLANK = "fill_in_blank"
    SHORT_ANSWER = "short_answer"
    CLOZE = "cloze"
    MATCHING = "matching"
    MEDIA = "media"
    ANALYSIS = "analysis"
    SECTION = "paragraph_desc"
    UNKNOWN = "unknown"


class AnswerSource(str, Enum):
    NONE = "none"
    REPLAY = "replay"
    LLM = "llm"


SELECTION_TYPES = (QuestionType.SINGLE, QuestionType.MULTIPLE, QuestionType.TRUE_FALSE)
BLANK_TYPES = (QuestionType.FILL_BLANK, QuestionType.CLOZE)
GROUP_TYPES = (QuestionType.MEDIA, QuestionType.ANALYSIS)
SKIP_TYPES = (QuestionType.SECTION,)


@dataclass(frozen=True)
class Option:
    id: int
    content: str = ""
    is_answer: Optional[bool] = None
    sort: int = 0


@dataclass(frozen=True)
class Question:
    subject_id: int
    qtype: QuestionType = QuestionType.UNKNOWN
    stem: str = ""
    options: Tuple[Option, ...] = field(default_factory=tuple)
    blank_count: int = 0
    correct_texts: Tuple[str, ...] = field(default_factory=tuple)
    parent_id: int = 0

    @property
    def correct_option_ids(self) -> Tuple[int, ...]:
        return tuple(opt.id for opt in self.options if opt.is_answer is True)

    @property
    def is_selection(self) -> bool:
        return self.qtype in SELECTION_TYPES

    @property
    def is_blank(self) -> bool:
        return self.qtype in BLANK_TYPES


@dataclass(frozen=True)
class Answer:
    subject_id: int
    answer_option_ids: Tuple[int, ...] = field(default_factory=tuple)
    answer_text: str = ""
    blanks: Tuple[Tuple[int, str], ...] = field(default_factory=tuple)
    parent_id: int = 0
    answer_type: str = ""

    def to_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "subject_id": self.subject_id,
            "answer_option_ids": list(self.answer_option_ids),
            "answer": self.answer_text,
        }
        if self.blanks:
            payload["answers"] = [{"sort": s, "content": c} for s, c in self.blanks]
        if self.parent_id:
            payload["parent_id"] = self.parent_id
        return payload


@dataclass(frozen=True)
class AnswerPlan:
    source: AnswerSource
    answers: Tuple[Answer, ...] = field(default_factory=tuple)
    pending: Tuple[Question, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AnswerResult:
    ok: bool
    status: str
    activity_id: str = ""
    submission_id: Any = None
    score: Any = None
    source: AnswerSource = AnswerSource.NONE
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    final_answers: Tuple[Answer, ...] = field(default_factory=tuple)
