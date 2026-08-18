from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


class LanguageGameServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class LanguageReply:
    reply: str
    narrator: str
    feedback: str
    suggestion: str
    quality: str
    effect: str
    mood: str
    score: int
    progress: int
    completed: bool
    task_success: int
    communication: int
    language_quality: int
    independence: int
    objectives_completed: list[str]
    skills_practiced: list[str]
    vocab_events: list[dict[str, Any]]
    xp_earned: int
    stars: int
    used_demo: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "reply": self.reply,
            "narrator": self.narrator,
            "feedback": self.feedback,
            "suggestion": self.suggestion,
            "quality": self.quality,
            "effect": self.effect,
            "mood": self.mood,
            "score": self.score,
            "progress": self.progress,
            "completed": self.completed,
            "task_success": self.task_success,
            "communication": self.communication,
            "language_quality": self.language_quality,
            "independence": self.independence,
            "objectives_completed": self.objectives_completed,
            "skills_practiced": self.skills_practiced,
            "vocab_events": self.vocab_events,
            "xp_earned": self.xp_earned,
            "stars": self.stars,
            "used_demo": self.used_demo,
        }


def clamp(value: int | float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(float(value)))))


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).lower().strip())


def _secret_goal_matches(scene: dict[str, Any], message: str) -> bool:
    goal = scene.get("secret_goal") or {}
    answer = str(goal.get("answer", "")).strip()
    if not answer:
        return False
    goal_type = str(goal.get("type", "phrase")).strip().lower()
    raw = str(message or "")
    if goal_type == "code":
        expected = re.sub(r"\D", "", answer)
        found = re.findall(r"\d+", raw)
        joined = "".join(found)
        return bool(expected) and (expected in joined or any(re.sub(r"\D", "", part) == expected for part in found))
    candidates = [answer] + [str(x) for x in goal.get("aliases", []) if str(x).strip()]
    haystack = re.sub(r"[^a-z0-9\u00c0-\u024f\u4e00-\u9fff]+", " ", raw.lower()).strip()
    for candidate in candidates:
        needle = re.sub(r"[^a-z0-9\u00c0-\u024f\u4e00-\u9fff]+", " ", candidate.lower()).strip()
        if needle and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack):
            return True
    return False


def _extract_json(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.S)
        if not match:
            raise LanguageGameServiceError("Mô hình không trả về dữ liệu game hợp lệ.")
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LanguageGameServiceError("Mô hình không trả về dữ liệu game hợp lệ.") from exc
    if not isinstance(parsed, dict):
        raise LanguageGameServiceError("Dữ liệu game trả về không đúng định dạng.")
    return parsed


def _response_text(response: Any) -> str:
    direct = str(getattr(response, "output_text", "") or "").strip()
    if direct:
        return direct
    chunks: list[str] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", None) == "output_text":
                text = str(getattr(part, "text", "") or "").strip()
                if text:
                    chunks.append(text)
    return "\n".join(chunks).strip()


def _list_of_strings(value: Any, limit: int = 12) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = re.sub(r"\s+", " ", str(item or "").strip())[:120]
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _vocab_events(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        term = re.sub(r"\s+", " ", str(item.get("term", "")).strip())[:120]
        if not term:
            continue
        source = str(item.get("source", "npc")).lower().strip()
        if source not in {"npc", "player", "hint"}:
            source = "npc"
        out.append(
            {
                "term": term,
                "source": source,
                "importance": clamp(item.get("importance", 3), 1, 5),
                "understood": bool(item.get("understood", source == "player")),
                "meaning": str(item.get("meaning", "")).strip()[:160],
                "context": str(item.get("context", "")).strip()[:240],
            }
        )
    return out


def _overall_score(task: int, communication: int, language_quality: int, independence: int) -> int:
    return clamp(task * 0.45 + communication * 0.30 + language_quality * 0.15 + independence * 0.10)


def _stars(score: int, completed: bool, independence: int) -> int:
    if not completed:
        return 0
    if score >= 86 and independence >= 70:
        return 3
    if score >= 68:
        return 2
    return 1


class LanguageGameService:
    """AI role-play engine: chấm theo ý nghĩa và mục tiêu giao tiếp, không theo từ khóa cứng."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: str = "low",
        max_output_tokens: int = 1700,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.model = str(model or "gpt-5.6-luna").strip() or "gpt-5.6-luna"
        self.reasoning_effort = str(reasoning_effort or "low").strip() or "low"
        self.max_output_tokens = max(700, int(max_output_tokens))
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def dictionary_lookup(self, *, term: str, language: str = "en") -> str:
        """Tra một từ/cụm ngắn và trả kết quả gọn để hiển thị như chat trong game."""
        term = re.sub(r"\s+", " ", str(term or "").strip())[:80]
        if not term:
            raise LanguageGameServiceError("Thiếu từ cần tra.")
        language = "zh" if str(language).strip() == "zh" else "en"

        if self.client is None:
            source = "MDBG" if language == "zh" else "Cambridge"
            return (
                f"{term}\n\n"
                f"Từ điển AI chưa được kết nối ở máy này. "
                f"Mày có thể bấm ‘Mở {source}’ ngay dưới câu trả lời để tra tiếp."
            )

        target_name = "Traditional Chinese" if language == "zh" else "English"
        pronunciation_rule = (
            "For Traditional Chinese, return Hanyu Pinyin with tone marks in pronunciation."
            if language == "zh"
            else "For English, return a short IPA pronunciation when reasonably certain."
        )
        instructions = f"""You are a concise learner dictionary inside a language-learning game.
The lookup language is {target_name}. The learner interface language is Vietnamese.
Explain the requested word or short phrase in Vietnamese.
{pronunciation_rule}
Prioritize the most common, useful meanings first. Do not invent rare senses just to make the list longer.
For a polysemous word, give up to 4 common meanings. For a phrase, explain the phrase as a unit.
Examples must be natural and short, in the lookup language, followed by Vietnamese translation.
Give up to 4 common collocations/phrasal expressions only when genuinely useful.
Do not add motivational text, meta commentary, or a long grammar lecture.
Return ONLY valid JSON with exactly these keys:
headword, pronunciation, part_of_speech, meanings, common_phrases
meanings: list of objects {{meaning, example, translation}}
common_phrases: list of objects {{phrase, meaning}}
"""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": term,
            "max_output_tokens": min(self.max_output_tokens, 850),
            "store": False,
        }
        if self.model.lower().startswith("gpt-5"):
            kwargs["reasoning"] = {"effort": "low"}
        try:
            response = self.client.responses.create(**kwargs)
            data = _extract_json(_response_text(response))
        except Exception as exc:
            raise LanguageGameServiceError("Từ điển trực tuyến đang lỗi tạm thời.") from exc

        headword = re.sub(r"\s+", " ", str(data.get("headword", term)).strip())[:100] or term
        pronunciation = re.sub(r"\s+", " ", str(data.get("pronunciation", "")).strip())[:120]
        part = re.sub(r"\s+", " ", str(data.get("part_of_speech", "")).strip())[:120]

        lines: list[str] = [headword]
        meta = " · ".join(item for item in (pronunciation, part) if item)
        if meta:
            lines.append(meta)

        meanings = data.get("meanings") if isinstance(data.get("meanings"), list) else []
        clean_meanings: list[dict[str, str]] = []
        for item in meanings[:4]:
            if not isinstance(item, dict):
                continue
            meaning = re.sub(r"\s+", " ", str(item.get("meaning", "")).strip())[:220]
            example = re.sub(r"\s+", " ", str(item.get("example", "")).strip())[:260]
            translation = re.sub(r"\s+", " ", str(item.get("translation", "")).strip())[:260]
            if meaning:
                clean_meanings.append({"meaning": meaning, "example": example, "translation": translation})

        if clean_meanings:
            lines.append("")
            lines.append("Nghĩa thường gặp:")
            for index, item in enumerate(clean_meanings, 1):
                lines.append(f"{index}. {item['meaning']}")
                if item["example"]:
                    lines.append(f"   {item['example']}")
                if item["translation"]:
                    lines.append(f"   → {item['translation']}")

        phrases = data.get("common_phrases") if isinstance(data.get("common_phrases"), list) else []
        clean_phrases: list[tuple[str, str]] = []
        for item in phrases[:4]:
            if not isinstance(item, dict):
                continue
            phrase = re.sub(r"\s+", " ", str(item.get("phrase", "")).strip())[:140]
            meaning = re.sub(r"\s+", " ", str(item.get("meaning", "")).strip())[:180]
            if phrase and meaning:
                clean_phrases.append((phrase, meaning))
        if clean_phrases:
            lines.append("")
            lines.append("Cụm hay gặp:")
            for phrase, meaning in clean_phrases:
                lines.append(f"• {phrase} = {meaning}")

        if len(lines) <= 2:
            lines.extend(["", "Chưa tìm được nghĩa đủ rõ cho từ/cụm này."])
        return "\n".join(lines)[:3500]

    def learning_feedback(
        self,
        *,
        module: str,
        prompt: str,
        answer: str,
        language: str = "en",
        level: str = "A1-A2",
        model_answer: str = "",
        focus: list[str] | None = None,
    ) -> dict[str, Any]:
        """Chấm writing/speaking/pronunciation ngắn. Không dùng cho MCQ cố định."""
        module = str(module or "writing").strip().lower()
        answer = str(answer or "").strip()[:1800]
        prompt = str(prompt or "").strip()[:1200]
        model_answer = str(model_answer or "").strip()[:900]
        focus = [str(item) for item in (focus or [])[:6]]
        target_name = "Traditional Chinese" if language == "zh" else "English"
        if not answer:
            return {"score": 0, "feedback": "Chưa có câu trả lời.", "correction": "", "passed": False}

        if self.client is None:
            word_count = len(answer.split()) if language == "en" else len(answer)
            score = min(85, 45 + word_count * (3 if language == "en" else 2))
            return {
                "score": score,
                "feedback": "Câu trả lời đã được ghi nhận. Khi AI trực tuyến hoạt động, hệ thống sẽ chấm chi tiết hơn.",
                "correction": model_answer or answer,
                "passed": score >= 60,
            }

        instructions = f"""You are a concise language coach.
Target language: {target_name}. Learner UI language: Vietnamese. Learner level: {level}. Module: {module}.
Task prompt: {prompt}
Focus points: {json.dumps(focus, ensure_ascii=False)}
Reference answer (only a reference, not the only valid answer): {model_answer}
Evaluate communicative success first. Do not over-penalize small grammar mistakes if meaning is clear.
For A1-A2, value simple correct everyday language over sophisticated vocabulary.
Return ONLY JSON with keys score, feedback, correction, passed.
score: integer 0-100. feedback: Vietnamese, max 2 short sentences, mention only the highest-value improvement.
correction: a natural corrected/polished version preserving the learner's intended meaning; do not add unrelated facts.
passed: boolean, normally true at score >= 60.
"""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": answer,
            "max_output_tokens": min(self.max_output_tokens, 650),
            "store": False,
        }
        if self.model.lower().startswith("gpt-5"):
            kwargs["reasoning"] = {"effort": "low"}
        try:
            response = self.client.responses.create(**kwargs)
            data = _extract_json(_response_text(response))
        except Exception as exc:
            raise LanguageGameServiceError("Không chấm được bài luyện lúc này.") from exc
        score = clamp(data.get("score", 55))
        correction = str(data.get("correction", "")).strip()[:900]
        feedback = str(data.get("feedback", "")).strip()[:700]
        passed = bool(data.get("passed", score >= 60))
        return {"score": score, "feedback": feedback, "correction": correction, "passed": passed}

    def checkpoint_feedback(
        self,
        *,
        language: str,
        level: str,
        speaking_prompt: str,
        speaking_answer: str,
        writing_prompt: str,
        writing_answer: str,
    ) -> dict[str, Any]:
        """Chấm Speaking + Writing của checkpoint bằng một lần gọi AI."""
        speaking_answer = str(speaking_answer or "").strip()[:1800]
        writing_answer = str(writing_answer or "").strip()[:1800]
        target_name = "Traditional Chinese" if language == "zh" else "English"
        if self.client is None:
            def heuristic(text: str, minimum_words: int) -> int:
                if not text:
                    return 0
                count = len(text.split()) if language == "en" else len(text)
                return max(35, min(82, 42 + count * (4 if language == "en" else 2))) if count >= minimum_words else max(20, 35 + count * 3)
            speaking_score = heuristic(speaking_answer, 5)
            writing_score = heuristic(writing_answer, 8)
            return {
                "speaking_score": speaking_score,
                "writing_score": writing_score,
                "feedback": "Bản offline chỉ chấm sơ bộ độ dài và mức hoàn thành. Khi AI trực tuyến hoạt động, checkpoint sẽ chấm communicative success chi tiết hơn.",
            }

        instructions = f"""You are grading a language course level checkpoint.
Target language: {target_name}. Learner UI language: Vietnamese. Claimed level/stage: {level}.
Evaluate communicative success before minor grammar accuracy. Do not reward sophisticated vocabulary if the answer does not fulfill the task.
Speaking prompt: {speaking_prompt}
Writing prompt: {writing_prompt}
Return ONLY JSON with keys speaking_score, writing_score, feedback.
speaking_score and writing_score: integers 0-100.
feedback: Vietnamese, max 3 concise sentences, state the most important weakness preventing progression.
"""
        input_text = f"""SPEAKING ANSWER:
{speaking_answer}

WRITING ANSWER:
{writing_answer}"""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": input_text,
            "max_output_tokens": min(self.max_output_tokens, 700),
            "store": False,
        }
        if self.model.lower().startswith("gpt-5"):
            kwargs["reasoning"] = {"effort": "low"}
        try:
            response = self.client.responses.create(**kwargs)
            data = _extract_json(_response_text(response))
        except Exception as exc:
            raise LanguageGameServiceError("Không chấm được checkpoint lúc này.") from exc
        return {
            "speaking_score": clamp(data.get("speaking_score", 0)),
            "writing_score": clamp(data.get("writing_score", 0)),
            "feedback": str(data.get("feedback", "")).strip()[:1200],
        }

    def reply(
        self,
        *,
        scene: dict[str, Any],
        state: dict[str, Any],
        message: str,
        history: list[dict[str, str]],
    ) -> LanguageReply:
        if self.client is None:
            return self._demo_reply(scene=scene, state=state, message=message)
        try:
            return self._ai_reply(scene=scene, state=state, message=message, history=history)
        except Exception:
            fallback = self._demo_reply(scene=scene, state=state, message=message)
            return LanguageReply(
                **{
                    **fallback.as_dict(),
                    "narrator": (
                        f"{fallback.narrator} Hệ thống trực tuyến vừa lỗi tạm thời; "
                        "lượt này dùng chế độ dự phòng."
                    ).strip(),
                    "used_demo": True,
                }
            )

    def _demo_reply(
        self,
        *,
        scene: dict[str, Any],
        state: dict[str, Any],
        message: str,
    ) -> LanguageReply:
        text = _clean(message)
        expected = scene.get("expected") or {}
        keys = [str(item).lower() for item in expected.get("keywords", [])]
        polite = [str(item).lower() for item in expected.get("polite", [])]
        hits = sum(key in text for key in keys)
        nice = sum(word in text for word in polite)
        word_count = len(text.split())

        if word_count < 2:
            task, communication, language_quality = 32, 38, 45
            quality = "chaos"
        elif hits >= 2 or (hits >= 1 and nice >= 1):
            task, communication, language_quality = 82, 86, 78
            quality = "great"
        elif hits >= 1 or nice >= 1 or word_count >= 5:
            task, communication, language_quality = 65, 73, 66
            quality = "okay"
        else:
            task, communication, language_quality = 52, 61, 58
            quality = "okay"

        help_count = int(state.get("help_count", 0) or 0)
        independence = clamp(90 - help_count * 15)
        objectives = [str(item) for item in scene.get("objectives", [])]
        already = set(str(item) for item in state.get("objectives_completed", []) if item)
        newly: list[str] = []
        if objectives:
            remaining = [item for item in objectives if item not in already]
            if task >= 58 and remaining:
                newly.append(remaining[0])
        completed_set = already | set(newly)
        if objectives:
            progress = clamp(100 * len(completed_set) / len(objectives))
        else:
            progress = clamp(int(state.get("progress", 0)) + (18 if task >= 65 else 10))

        mode = str(state.get("mode", "mission"))
        secret_goal = scene.get("secret_goal") or {}
        has_secret_goal = bool(str(secret_goal.get("answer", "")).strip())
        if has_secret_goal:
            # Secret/guessing games use a dedicated answer box in the UI.
            # Chat is only for collecting clues, so it can never complete the mission.
            completed = False
            progress = min(progress, 85)
        else:
            completed = mode != "free_roam" and (
                (bool(objectives) and len(completed_set) >= len(objectives) and communication >= 50)
                or (not objectives and progress >= 100 and task >= 60)
            )
        score = _overall_score(task, communication, language_quality, independence)
        stars = _stars(score, completed, independence)
        xp = max(6, score // 8) + (35 if completed else 0)

        reply_pool = (
            scene.get("ending_replies", [])
            if completed
            else (scene.get("demo_replies") or {}).get(quality, [])
        )
        if not reply_pool:
            zh = scene.get("language") == "zh"
            if completed:
                reply_pool = ["可以，這件事算解決了。我們繼續吧。" if zh else "That works. We actually solved it. Let's keep moving."]
            elif quality == "great":
                reply_pool = ["我懂了。這樣說很清楚，那接下來呢？" if zh else "Got it. That's clear. So what do you want to do next?"]
            elif quality == "chaos":
                reply_pool = ["我大概抓到一半意思。再說清楚一點，不然事情要往奇怪的方向發展了。" if zh else "I caught about half of that. Clarify it before this situation becomes extremely weird."]
            else:
                reply_pool = ["我大概懂。再補一點細節，我就能接下去了。" if zh else "I mostly get it. Give me one more detail and we can move on."]
        narrator_pool = (
            scene.get("ending_narrator", [])
            if completed
            else (scene.get("narrator") or {}).get(quality, [])
        )
        if not narrator_pool:
            narrator_pool = ["Tình huống tiếp tục theo đúng cách mày vừa xử lý."]
        feedback_pool = (scene.get("feedback") or {}).get(quality, [])
        if not feedback_pool:
            feedback_pool = ["Ý chính đã truyền được. Nếu muốn tự nhiên hơn, ưu tiên nói rõ mục đích trước rồi mới thêm chi tiết."]
        # In demo mode we cannot reliably rewrite the player's exact sentence without the AI evaluator.
        # Returning an unrelated scene-level canned suggestion is worse than returning nothing.
        suggestion_pool = [""]

        vocab_events: list[dict[str, Any]] = []
        meaningful = [w.strip(".,!?;:\"'()") for w in message.split()]
        for word in meaningful:
            if len(word) >= 4 and word.isalpha():
                vocab_events.append(
                    {
                        "term": word,
                        "source": "player",
                        "importance": 3,
                        "understood": True,
                        "meaning": "",
                        "context": message[:180],
                    }
                )
            if len(vocab_events) >= 4:
                break
        for term in (scene.get("core_terms") or scene.get("vocab") or [])[:2]:
            term_text = str(term)
            if term_text.lower() in text:
                continue
            vocab_events.append(
                {
                    "term": term_text,
                    "source": "npc",
                    "importance": 4,
                    "understood": True,
                    "meaning": "",
                    "context": str(random.choice(reply_pool or [scene.get("opening", "")]))[:180],
                }
            )

        return LanguageReply(
            reply=random.choice(reply_pool or ["..."]),
            narrator=random.choice(narrator_pool or [""]),
            feedback=random.choice(feedback_pool or [""]),
            suggestion=random.choice(suggestion_pool),
            quality=quality,
            effect={"great": "spark", "okay": "wiggle", "chaos": "boom"}[quality],
            mood={"great": "happy", "okay": "confused", "chaos": "shocked"}[quality],
            score=score,
            progress=progress,
            completed=completed,
            task_success=task,
            communication=communication,
            language_quality=language_quality,
            independence=independence,
            objectives_completed=newly,
            skills_practiced=_list_of_strings(scene.get("communication_skills", []), 6),
            vocab_events=vocab_events[:8],
            xp_earned=xp,
            stars=stars,
            used_demo=True,
        )

    def _instructions(self, scene: dict[str, Any], state: dict[str, Any]) -> str:
        target = "English" if scene.get("language") == "en" else "Traditional Chinese"
        objectives = scene.get("objectives") or []
        completed_objectives = state.get("objectives_completed") or []
        skills = scene.get("communication_skills") or []
        secret_goal = scene.get("secret_goal") or {}
        has_secret_goal = bool(str(secret_goal.get("answer", "")).strip())
        secret_label = str(secret_goal.get("label", "final answer")).strip()
        clues_revealed = int(state.get("clues_revealed", 0) or 0)
        mode = str(state.get("mode", "mission"))
        humor = str(state.get("humor", "chaotic-meme"))
        humor_contracts = {
            "chaotic-meme": "Fast, playful and absurd-but-coherent. Use unexpected funny details, internet-era humor, and occasional ridiculous twists. Never become random nonsense; always respond directly to what the player just said.",
            "deadpan": "Dry, understated and straight-faced. Humor comes from calm literal reactions, awkward understatement, and subtle irony. Keep delivery concise and never overreact.",
            "dramatic": "Emotionally heightened and cinematic. Use tension, suspicion, urgency, cliffhanger energy, and stronger reactions while keeping the situation believable and coherent.",
            "gentle": "Warm, friendly and lightly funny. Keep pressure low, react kindly, use soft humor, and help the player continue without sounding childish or patronizing.",
        }
        humor_contract = humor_contracts.get(humor, humor_contracts["chaotic-meme"])
        known_vocab = [str(item) for item in (state.get("known_vocabulary") or [])[:80]]
        level = str(state.get('level', 'A1-A2'))
        vocabulary_contract = (
            "Use mostly very common everyday A1-A2 words and short sentences. Prefer the learner's known vocabulary. "
            "Introduce at most 1-2 new reusable words/phrases in a turn, and make their meaning inferable from context. "
            "Avoid niche puzzle vocabulary unless the scene is explicitly marked hardcore."
            if level == "A1-A2"
            else "Use natural everyday language appropriate to the learner's level; avoid unnecessary rare words."
        )
        return f"""You are both an NPC and a semantic evaluator inside an open-world language-learning RPG.
Target language: {target}.
Player level: {state.get('level', 'A1-A2')}. Humor style: {humor}.
HUMOR STYLE CONTRACT: {humor_contract}
VOCABULARY CONTRACT: {vocabulary_contract}
KNOWN/ACTIVE LEARNER VOCABULARY (prefer when natural): {json.dumps(known_vocab, ensure_ascii=False)}
The humor style changes ONLY the NPC's tone, pacing, reactions and narration. It must never change the mission objective, scoring fairness, or the meaning of what the player said.
Mode: {mode}.
Game group: {scene.get('game_group', 'roleplay')}. Gameplay: {scene.get('gameplay', 'conversation')}.
Scene: {scene.get('title', '')}.
Location: {scene.get('location', '')}.
Player role: {scene.get('player_role', '')}.
NPC role: {scene.get('npc_role', '')}.
Story context: {scene.get('story_context', '')}.
Mission: {scene.get('mission', '')}.
Win condition: {scene.get('win_condition', 'Resolve the situation through understandable communication')}.
SECRET-DISCOVERY GAME: {'yes' if has_secret_goal else 'no'}.
SECRET TARGET LABEL: {secret_label if has_secret_goal else 'none'}.
CLUES ALREADY REVEALED BY SERVER: {clues_revealed}.
Communication objectives: {json.dumps(objectives, ensure_ascii=False)}.
Already completed objectives: {json.dumps(completed_objectives, ensure_ascii=False)}.
Communication skills to practice: {json.dumps(skills, ensure_ascii=False)}.
Help already used this session: {int(state.get('help_count', 0) or 0)}.

CORE RULES:
1. Evaluate meaning and communicative success, NOT exact keywords. Many different phrasings can be correct.
2. Grammar mistakes alone must not fail a player if an NPC can clearly understand the meaning.
3. The mission is complete only when its real-world objective is actually resolved and communication is understandable. In free_roam mode never complete the session automatically.
3A. If SECRET-DISCOVERY GAME is yes, chat is ONLY for investigation. NEVER mark mission_completed true from chat, even if the player types a possible final answer. The player must submit the final answer in a separate answer box handled by the server.
3B. The server, not you, owns the exact secret answer and clue values. NEVER invent digits, names, objects, or exact clue facts that are not explicitly present in the public scene. When the player asks a relevant question, respond naturally and encourage the investigation; the server may append an earned clue after your reply.
3C. If the player asks what they are supposed to do, explain simply: ask questions to collect clues, then enter the final answer in the separate answer box. Do not make the player guess the rules of the game.
4. Stay in character first. NPC dialogue must be in the target language, natural for the player's level, and normally 1-3 sentences. ALWAYS respond directly to the player's latest message before introducing any new twist. Never behave as if the player said something they did not say.
4A. Preserve causal story logic. Every clue, question and NPC response must make sense for the player's role, the NPC's role, and why the player cares about the outcome. Never turn the scene into an unrelated riddle. If the player asks “why should I care?” or “what is happening?”, explain the concrete stake in plain language before continuing.
4B. Do not invent a new relationship, location, object, deadline, reward, crime, ex-partner, job, or other plot fact that conflicts with Story context. You may add small flavor details only when they do not alter the causal chain.
5. Adapt difficulty. If the player is weak, scaffold through natural follow-up questions. If the player is strong but gives trivial answers, ask for clarification, reasons, or detail naturally.
6. feedback is one short Vietnamese coaching note for backend learning records. It should focus on the single highest-value improvement and must not interrupt the role-play with a lecture.
7. suggestion MUST be a more natural rewrite of the player's CURRENT message only. Preserve the same meaning, intent, people, objects and facts. Correct grammar/word choice/naturalness, but DO NOT answer the NPC, DO NOT predict the next turn, DO NOT add new information, and DO NOT change the player's communicative intent. If the player's message is already natural, return a lightly polished equivalent or the same sentence.
8. Identify only 0-6 useful vocabulary/phrases worth tracking. Do NOT dump every word. Prefer high-frequency, reusable, context-relevant items. Include player-used items and useful items from your NPC reply. Mark importance from 1 (niche) to 5 (very important/common for this learner).
9. objectives_completed must contain ONLY objectives newly achieved on this turn, copied exactly from the provided objective strings.
10. task_success measures whether the player's action advances/resolves the real situation. communication measures understandability/relevance. language_quality measures grammar, vocabulary and naturalness without dominating success. independence reflects how independently they handled it; reduce it if much help has been used.
11. Keep content safe and non-humiliating.

Return ONLY valid JSON with these keys:
reply, narrator, feedback, suggestion, quality, effect, mood,
task_success, communication, language_quality, independence,
objectives_completed, skills_practiced, vocab_events, mission_completed.

quality: great|okay|chaos
 effect: spark|wiggle|boom
 mood: happy|confused|shocked
 scores: integers 0-100
 skills_practiced: list of short skill ids/labels
 vocab_events: list of objects with term, source(player|npc), importance(1-5), understood(boolean), meaning(short Vietnamese gloss if useful), context(short snippet)
 mission_completed: boolean, but must obey rule 3."""

    def _ai_reply(
        self,
        *,
        scene: dict[str, Any],
        state: dict[str, Any],
        message: str,
        history: list[dict[str, str]],
    ) -> LanguageReply:
        if self.client is None:
            raise LanguageGameServiceError("Dịch vụ ngôn ngữ chưa được cấu hình.")

        payload = {
            "player_message": message,
            "recent_history": history[-10:],
        }
        kwargs: dict[str, Any] = {
            "model": self.model,
            "instructions": self._instructions(scene, state),
            "input": json.dumps(payload, ensure_ascii=False),
            "max_output_tokens": self.max_output_tokens,
            "store": False,
        }
        if self.model.lower().startswith("gpt-5"):
            kwargs["reasoning"] = {"effort": self.reasoning_effort}

        response = self.client.responses.create(**kwargs)
        data = _extract_json(_response_text(response))

        quality = str(data.get("quality", "okay"))
        if quality not in {"great", "okay", "chaos"}:
            quality = "okay"
        effect = str(data.get("effect", "wiggle"))
        if effect not in {"spark", "wiggle", "boom"}:
            effect = "wiggle"
        mood = str(data.get("mood", "confused"))
        if mood not in {"happy", "confused", "shocked"}:
            mood = "confused"

        task = clamp(data.get("task_success", 50))
        communication = clamp(data.get("communication", 55))
        language_quality = clamp(data.get("language_quality", 55))
        independence = clamp(data.get("independence", 75))
        independence = clamp(independence - int(state.get("help_count", 0) or 0) * 5)
        score = _overall_score(task, communication, language_quality, independence)

        scene_objectives = [str(item) for item in scene.get("objectives", [])]
        allowed = set(scene_objectives)
        newly = [
            item
            for item in _list_of_strings(data.get("objectives_completed", []), 12)
            if item in allowed
        ]
        already = set(str(item) for item in state.get("objectives_completed", []) if item)
        merged = already | set(newly)
        if scene_objectives:
            progress = clamp(100 * len(merged) / len(scene_objectives))
        else:
            progress = clamp(int(state.get("progress", 0)) + (18 if task >= 65 else 9))

        mode = str(state.get("mode", "mission"))
        model_completed = bool(data.get("mission_completed", False))
        secret_goal = scene.get("secret_goal") or {}
        has_secret_goal = bool(str(secret_goal.get("answer", "")).strip())
        completed = False
        if mode != "free_roam":
            if has_secret_goal:
                # Final answer is validated only by /api/language/answer.
                completed = False
                progress = min(progress, 85)
            elif scene_objectives:
                completed = len(merged) >= len(scene_objectives) and communication >= 50 and (model_completed or task >= 65)
            else:
                completed = model_completed and task >= 60 and communication >= 50
        if completed:
            progress = 100
        score = _overall_score(task, communication, language_quality, independence)

        stars = _stars(score, completed, independence)
        xp = max(6, score // 8) + (35 if completed else 0)
        skills = _list_of_strings(data.get("skills_practiced", []), 8)
        if not skills:
            skills = _list_of_strings(scene.get("communication_skills", []), 8)

        return LanguageReply(
            reply=str(data.get("reply", "...")).strip()[:1200] or "...",
            narrator=str(data.get("narrator", "")).strip()[:500],
            feedback=str(data.get("feedback", "")).strip()[:800],
            suggestion=str(data.get("suggestion", "")).strip()[:500],
            quality=quality,
            effect=effect,
            mood=mood,
            score=score,
            progress=progress,
            completed=completed,
            task_success=task,
            communication=communication,
            language_quality=language_quality,
            independence=independence,
            objectives_completed=newly,
            skills_practiced=skills,
            vocab_events=_vocab_events(data.get("vocab_events", [])),
            xp_earned=xp,
            stars=stars,
            used_demo=False,
        )
