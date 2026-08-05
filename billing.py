from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PricingConfigError(RuntimeError):
    pass


class PricingCatalog:
    """Load and validate the public pricing catalog from JSON."""

    def __init__(self, path: Path):
        self.path = path
        self._data = self._load()
        self._plans = {
            str(plan["id"]): plan
            for group in ("topups", "monthly")
            for plan in self._data.get(group, [])
        }

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PricingConfigError(f"Không đọc được bảng giá: {exc}") from exc

        if not isinstance(data, dict):
            raise PricingConfigError("Bảng giá phải là một JSON object.")
        for group in ("topups", "monthly"):
            plans = data.get(group)
            if not isinstance(plans, list) or not plans:
                raise PricingConfigError(f"Bảng giá thiếu nhóm {group}.")
            for plan in plans:
                self._validate_plan(plan, group)
        return data

    @staticmethod
    def _validate_plan(plan: Any, group: str) -> None:
        if not isinstance(plan, dict):
            raise PricingConfigError(f"Plan trong {group} phải là object.")
        required = {"id", "name", "price_vnd", "kind"}
        missing = required - set(plan)
        if missing:
            raise PricingConfigError(f"Plan thiếu field: {', '.join(sorted(missing))}")
        if plan["kind"] not in {"topup", "monthly"}:
            raise PricingConfigError(f"Plan {plan['id']} có kind không hợp lệ.")
        if group == "topups" and plan["kind"] != "topup":
            raise PricingConfigError(f"Plan {plan['id']} nằm sai nhóm.")
        if group == "monthly" and plan["kind"] != "monthly":
            raise PricingConfigError(f"Plan {plan['id']} nằm sai nhóm.")
        if int(plan["price_vnd"]) < 2000:
            raise PricingConfigError(f"Plan {plan['id']} có giá quá thấp.")
        if plan["kind"] == "topup" and int(plan.get("credits", 0)) <= 0:
            raise PricingConfigError(f"Plan {plan['id']} thiếu credits.")
        if plan["kind"] == "monthly":
            if not bool(plan.get("unlimited", False)) and int(plan.get("messages", 0)) <= 0:
                raise PricingConfigError(f"Plan {plan['id']} thiếu messages.")
            if bool(plan.get("unlimited", False)) and int(plan.get("daily_fair_limit", 0)) <= 0:
                raise PricingConfigError(f"Plan {plan['id']} thiếu daily_fair_limit.")

    def public_data(self) -> dict[str, Any]:
        """Return only fields safe to expose to the browser."""
        return {
            "currency": self._data.get("currency", "VND"),
            "free": self._data.get("free", {}),
            "topups": [dict(item) for item in self._data["topups"] if item.get("active", True)],
            "monthly": [dict(item) for item in self._data["monthly"] if item.get("active", True)],
            "notes": self._data.get("notes", []),
        }

    def get(self, plan_id: str) -> dict[str, Any] | None:
        plan = self._plans.get(str(plan_id))
        if not plan or not plan.get("active", True):
            return None
        return dict(plan)
