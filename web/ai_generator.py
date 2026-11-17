import json
import os
import re

from flask import current_app, has_app_context

MAX_LESSON_CHARS = 12000

SYSTEM_PROMPT = """You are an expert educational assessment designer for QuizCloud.
Generate multiple-choice questions (MCQs) strictly based on the provided lesson text.

Rules:
1. Keep the EXACT SAME LANGUAGE as the input lesson text (e.g., if the text is in Vietnamese, write questions and options in Vietnamese; if in English, write in English).
2. Each question must have 4 options: "A", "B", "C", "D".
3. "correct" must be either a single option letter (e.g. "B") or multiple correct option letters separated by a semicolon (e.g. "A;C").
4. "points" should be a number (default 1).
5. Return ONLY a valid JSON object matching this exact schema:
{"questions": [{"question": "...", "A": "...", "B": "...", "C": "...", "D": "...", "correct": "A", "points": 1}]}
"""


def _cfg(key: str, default: str = "") -> str:
    if has_app_context():
        return (current_app.config.get(key) or default).strip()
    return (os.environ.get(key) or default).strip()


def _demo_questions(lesson_text: str) -> list[dict]:
    cleaned = re.sub(r"\s+", " ", lesson_text).strip()
    snippet = cleaned[:90] + ("..." if len(cleaned) > 90 else "")
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", cleaned) if len(s.strip()) > 15]
    first_fact = sentences[0][:120] if sentences else snippet
    second_fact = sentences[1][:120] if len(sentences) > 1 else first_fact

    # Heuristic check for Vietnamese diacritics to match the input language in demo mode
    is_vi = bool(re.search(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", cleaned.lower()))

    if is_vi:
        return [
            {
                "question": f"Nội dung trọng tâm nào được đề cập trong tài liệu: \"{snippet}\"?",
                "A": first_fact,
                "B": "Một chủ đề hoàn toàn không xuất hiện trong bài học",
                "C": "Thông tin ngoài phạm vi chương trình đào tạo",
                "D": "Không có khái niệm nào được trình bày",
                "correct": "A",
                "points": 1,
            },
            {
                "question": "(Nhiều đáp án) Những nhận định nào đúng khi tổng hợp nội dung bài học trên?",
                "A": f"Tài liệu tập trung vào: {first_fact[:80]}",
                "B": "Tài liệu không liên quan đến nội dung học tập",
                "C": f"Chi tiết bổ trợ được nêu: {second_fact[:80]}",
                "D": "Nội dung văn bản hoàn toàn rỗng",
                "correct": "A;C",
                "points": 1,
            },
        ]

    return [
        {
            "question": f" Which key concept is directly discussed in the lesson excerpt: \"{snippet}\"?",
            "A": first_fact,
            "B": "An unrelated topic not mentioned in the lesson",
            "C": "A deprecated concept outside the syllabus",
            "D": "None of the statements above",
            "correct": "A",
            "points": 1,
        },
        {
            "question": "(Multiple answers) Select the statements supported by the provided lesson text:",
            "A": f"Key point covered: {first_fact[:80]}",
            "B": "The lesson text is completely unrelated to the course",
            "C": f"Supporting detail: {second_fact[:80]}",
            "D": "The provided material is empty",
            "correct": "A;C",
            "points": 1,
        },
    ]


def generate_mcqs_from_text(lesson_text: str, num_questions: int = 5) -> list[dict]:
    try:
        num_questions = int(num_questions)
    except (TypeError, ValueError):
        num_questions = 5
    num_questions = max(1, min(15, num_questions))

    lesson_text = (lesson_text or "").strip()[:MAX_LESSON_CHARS]
    if not lesson_text:
        raise ValueError("Lesson text cannot be empty.")

    endpoint = _cfg("AZURE_OPENAI_ENDPOINT")
    api_key = _cfg("AZURE_OPENAI_API_KEY")
    deployment = _cfg("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini") or "gpt-4.1-mini"
    api_version = _cfg("AZURE_OPENAI_API_VERSION", "2024-10-21") or "2024-10-21"

    if not (endpoint and api_key):
        return _demo_questions(lesson_text)

    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )
    user_prompt = (
        f"Generate exactly {num_questions} multiple-choice question(s) from the following lesson text:\n\n"
        f"{lesson_text}"
    )
    response = client.chat.completions.create(
        model=deployment,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )
    raw_content = response.choices[0].message.content or "{}"
    parsed = json.loads(raw_content)
    questions = parsed.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError("Azure OpenAI response did not contain a valid 'questions' list.")
    return questions[:num_questions]
