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
            "used_demo": self.used_demo,
        }


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).lower().strip())


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
            raise LanguageGameServiceError(
                "Mô hình không trả về dữ liệu game hợp lệ."
            ) from exc
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


class LanguageGameService:
    """Sinh phản hồi cho game nhập vai; tự rơi về demo khi chưa có API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: str = "low",
        max_output_tokens: int = 1400,
    ) -> None:
        self.api_key = str(api_key or "").strip()
        self.model = str(model or "gpt-5.6-luna").strip() or "gpt-5.6-luna"
        self.reasoning_effort = str(reasoning_effort or "low").strip() or "low"
        self.max_output_tokens = max(500, int(max_output_tokens))
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    @property
    def is_configured(self) -> bool:
        return self.client is not None

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
            return self._ai_reply(
                scene=scene,
                state=state,
                message=message,
                history=history,
            )
        except Exception:
            # Game vẫn chạy được khi API tạm lỗi. Không đưa chi tiết kỹ thuật ra UI.
            fallback = self._demo_reply(scene=scene, state=state, message=message)
            return LanguageReply(
                **{
                    **fallback.as_dict(),
                    "narrator": (
                        f"{fallback.narrator} Hệ thống trực tuyến vừa vấp dây điện, "
                        "lượt này tạm dùng chế độ dự phòng."
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
        nonsense = any(
            item in text
            for item in ["banana", "con mèo", "cat", "火星", "pizza", "boom"]
        )

        if len(text.split()) < 2 or nonsense:
            quality, score_delta, progress_delta = "chaos", -8, 8
        elif hits >= 2 and nice >= 1:
            quality, score_delta, progress_delta = "great", 12, 24
        elif hits >= 1 or nice >= 1:
            quality, score_delta, progress_delta = "okay", 3, 14
        else:
            quality, score_delta, progress_delta = "okay", -1, 10

        score = clamp(int(state.get("score", 50)) + score_delta)
        progress = clamp(int(state.get("progress", 0)) + progress_delta)
        completed = progress >= 100

        reply_pool = (
            scene.get("ending_replies", [])
            if completed
            else (scene.get("demo_replies") or {}).get(quality, [])
        )
        narrator_pool = (
            scene.get("ending_narrator", [])
            if completed
            else (scene.get("narrator") or {}).get(quality, [])
        )
        feedback_pool = (scene.get("feedback") or {}).get(quality, [])
        suggestion_pool = scene.get("suggestions") or [""]

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
            used_demo=True,
        )

    def _instructions(self, scene: dict[str, Any], state: dict[str, Any]) -> str:
        target = "English" if scene.get("language") == "en" else "Traditional Chinese"
        return f"""You are an NPC and game director in a visual role-play language game.
Target language: {target}. Player level: {state.get('level', 'A1-A2')}. Humor: {state.get('humor', 'chaotic-meme')}.
Scene: {scene.get('title', '')}. Player role: {scene.get('player_role', '')}. NPC role: {scene.get('npc_role', '')}.
Mission: {scene.get('mission', '')}. Current score: {state.get('score', 50)}/100. Current progress: {state.get('progress', 0)}/100.
Stay in character. NPC dialogue must be in the target language and limited to 1-3 short sentences.
React naturally inside the role-play first. Then give one short Vietnamese feedback note and one better target-language response.
Keep the story moving even when grammar is imperfect. Be playful and meme-friendly, but never humiliating, sexual, violent, discriminatory or cruel.
Progress may increase by 8-25 points. Score delta must remain between -12 and +15.
Return only valid JSON with keys: reply, narrator, feedback, suggestion, quality, effect, mood, score_delta, progress_delta, completed.
Allowed values: quality=great|okay|chaos; effect=spark|wiggle|boom; mood=happy|confused|shocked."""

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
        # GPT-5 family supports reasoning; older/fallback models may not.
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

        score_delta = clamp(int(data.get("score_delta", 0)), -12, 15)
        progress_delta = clamp(int(data.get("progress_delta", 10)), 8, 25)
        score = clamp(int(state.get("score", 50)) + score_delta)
        progress = clamp(int(state.get("progress", 0)) + progress_delta)
        completed = bool(data.get("completed", False) or progress >= 100)

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
            used_demo=False,
        )
