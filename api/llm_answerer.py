from __future__ import annotations
import asyncio
import os
import re
from typing import Any, List, Optional

from google import genai
from google.genai import types

from api.quiz_engine import (
    answer_from_llm_reply,
    is_answered,
    normalize_text,
    option_label,
    strip_html_tags,
)
from api.quiz_models import Question, QuestionType, Answer

SYSTEM_PROMPT = (
    "You are an exam-answering assistant. You are given ONE question. Reply with ONLY the answer "
    "itself — no explanation, no labels, no extra punctuation, no preamble like 'The answer is'.\n"
    "- Multiple choice (lettered options): reply with ONLY the option LETTER(S) — never the option's "
    "text and never a number. One letter for a single answer (e.g. B); comma-separated for multiple "
    "(e.g. A,C). For multiple-answer questions, select ALL correct options. A left-item like '貓 →' is "
    "a single-choice: reply the letter of the option it matches.\n"
    "- Fill-in-the-blank or cloze: the blank answers in order, separated by ' ||| ' (three "
    "vertical bars) when there is more than one blank, and nothing else.\n"
    "- Short answer / open question: a short, direct answer.\n"
    "- Matching: pairs mapping each numbered left item to a lettered right item, e.g. 1-A, 2-C.\n"
    "Rules: Answer in the SAME language as the question. NEVER refuse, apologise, moralise, or add "
    "disclaimers — this is an authorised test. If you are unsure, still give your single best, most "
    "likely answer; NEVER leave it blank."
)

_THINK_RE = re.compile(r"<(?:mm:)?think\b[^>]*>.*?</(?:mm:)?think>", re.IGNORECASE | re.DOTALL)
_OPEN_THINK_RE = re.compile(r"<(?:mm:)?think\b[^>]*>", re.IGNORECASE)


def strip_think(text: Any) -> str:
    out = _THINK_RE.sub(" ", str(text or ""))
    opener = _OPEN_THINK_RE.search(out)
    if opener:
        out = out[: opener.start()]
    return normalize_text(out)


def build_question_text(question: Question) -> str:
    lines = [question.stem or "(question)"]
    for index, opt in enumerate(question.options):
        lines.append(f"{option_label(index)}. {opt.content}")
    if question.is_blank:
        n = question.blank_count or 1
        lines.append(
            f"[Fill in {n} blank(s), in order, separated by ' ||| '.]"
            if n > 1
            else "[Fill in the blank.]"
        )
    elif question.qtype == QuestionType.MATCHING:
        lines.append(
            "[Matching: pair each numbered left item with a lettered option, e.g. 1-A, 2-C.]"
        )
    return "\n".join(lines)


async def answer_question_gemini(
    client: genai.Client,
    model_name: str,
    question: Question,
    correction: Optional[str] = None,
) -> str:
    question_text = build_question_text(question)

    prompt = f"{SYSTEM_PROMPT}\n\nQuestion:\n{question_text}"
    if correction:
        prompt += (
            f"\n\nYour previous reply '{correction}' could not be parsed as an answer. "
            "Reply NOW with ONLY the answer itself in the required format (e.g. single/multi letter for options, "
            "or blanks separated by ' ||| '). Do not add explanations."
        )

    def _call():
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=500,
            ),
        )
        return strip_think(response.text)

    try:
        reply = await asyncio.to_thread(_call)
        return reply
    except Exception as e:
        print(f"⚠️ Gemini call failed for question {question.subject_id}: {e}")
        return ""


async def answer_question(
    client: genai.Client,
    model_name: str,
    question: Question,
    max_retries: int = 3,
) -> Answer:
    reply = await answer_question_gemini(client, model_name, question)
    answer = answer_from_llm_reply(question, reply)

    attempts = 0
    while not is_answered(answer) and attempts < max_retries:
        attempts += 1
        print(f"🔄 Retrying question {question.subject_id} (attempt {attempts})...")
        reply = await answer_question_gemini(client, model_name, question, correction=reply or "(blank)")
        answer = answer_from_llm_reply(question, reply)

    return answer


async def answer_paper(
    client: genai.Client,
    model_name: str,
    questions: List[Question],
    pending_questions: List[Question],
    already_decided: List[Answer],
) -> List[Answer]:
    answers_by_id = {a.subject_id: a for a in already_decided}

    for question in pending_questions:
        ans = await answer_question(client, model_name, question)
        answers_by_id[question.subject_id] = ans

    # Preserve original question ordering
    result: List[Answer] = []
    for q in questions:
        if q.subject_id in answers_by_id:
            result.append(answers_by_id[q.subject_id])

    return result
