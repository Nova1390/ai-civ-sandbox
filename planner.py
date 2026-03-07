from __future__ import annotations

import asyncio
import json
import re
import urllib.error
import urllib.request
from typing import Optional


class Planner:
    """
    Planner che chiama Ollama locale via HTTP.
    Default:
      http://127.0.0.1:11434/api/generate
    """

    def __init__(
        self,
        model: str = "phi3",
        base_url: str = "http://127.0.0.1:11434",
        timeout_s: float = 2.5,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def propose_goal(self, prompt: str) -> str:
        """
        Chiamata sincrona a Ollama.
        Ritorna sempre un goal pulito oppure 'survive'.
        """
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as e:
            print(f"[Planner] ollama unreachable: {e}")
            return "survive"
        except Exception as e:
            print(f"[Planner] error: {e}")
            return "survive"

        text = self._parse_ollama_response(raw)
        goal = self._extract_goal(text)

        return self._normalize_goal(goal)

    async def propose_goal_async(self, prompt: str) -> str:
        """
        Wrapper non bloccante.
        Esegue propose_goal in thread separato.
        """
        return await asyncio.to_thread(self.propose_goal, prompt)

    def _parse_ollama_response(self, raw: str) -> str:
        """
        Con stream=False Ollama di solito ritorna un singolo JSON del tipo:
        {"response":"...", "done": true, ...}
        Però manteniamo anche un fallback per output multilinea.
        """
        cleaned = raw.strip()
        if not cleaned:
            return ""

        try:
            obj = json.loads(cleaned)
            if isinstance(obj, dict):
                if "response" in obj:
                    return str(obj["response"]).strip()
                if "error" in obj:
                    return ""
        except json.JSONDecodeError:
            pass

        # fallback compatibile anche con vecchi output multilinea
        parts = []
        for line in cleaned.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    if "response" in obj:
                        parts.append(str(obj["response"]))
            except json.JSONDecodeError:
                parts.append(line)

        return "".join(parts).strip()

    def _extract_goal(self, text: str) -> Optional[str]:
        """
        Estrae un goal da:
        - testo normale
        - JSON
        - ```json ... ```
        """
        if not text:
            return None

        cleaned = text.strip()

        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            obj = json.loads(cleaned)
            if isinstance(obj, dict):
                g = obj.get("goal") or obj.get("task") or obj.get("objective")
                if isinstance(g, str) and g.strip():
                    return g.strip()
        except Exception:
            pass

        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if not lines:
            return None

        return lines[0][:120].strip()

    def _normalize_goal(self, goal: Optional[str]) -> str:
        if not goal:
            return "survive"

        g = goal.strip().lower()

        allowed = {
            "gather food",
            "gather wood",
            "gather stone",
            "explore",
            "expand village",
            "build storage",
            "build house",
            "improve logistics",
            "stabilize",
            "survive",
        }

        # match permissivo
        if "food" in g or "eat" in g or "hunt" in g:
            return "gather food"
        if "wood" in g or "tree" in g or "legn" in g:
            return "gather wood"
        if "stone" in g or "rock" in g or "pietr" in g:
            return "gather stone"
        if "explore" in g or "esplora" in g:
            return "explore"
        if "expand" in g or "village" in g:
            return "expand village"
        if "storage" in g or "granary" in g:
            return "build storage"
        if "house" in g or "housing" in g:
            return "build house"
        if "logistic" in g or "road" in g:
            return "improve logistics"
        if "stabil" in g:
            return "stabilize"

        if g in allowed:
            return g

        return "survive"