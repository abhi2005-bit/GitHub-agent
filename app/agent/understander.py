from __future__ import annotations

import json

from app.llm.base import LLMClient
from app.models.understanding import Understanding


class Understander:
    """
    Converts a user goal into a structured Understanding using an LLM.
    """

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def understand(self, goal: str) -> Understanding:
        """
        Use the LLM to understand the user's engineering goal.
        """

        if not goal or not goal.strip():
            raise ValueError("Goal cannot be empty.")

        prompt = self._build_prompt(goal)

        response = self.llm.generate(prompt)

        try:
            data = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "LLM returned an invalid JSON response."
            ) from exc

        return Understanding.model_validate(data)

    @staticmethod
    def _build_prompt(goal: str) -> str:
        """
        Build the structured understanding prompt.
        """

        return f"""
You are the understanding component of DevPilot,
an engineering intelligence agent.

Your job is to understand the user's engineering request
and convert it into structured JSON.

Do not create an execution plan.
Do not execute any tools.
Do not invent information that is not present in the request.

Return ONLY valid JSON with exactly these fields:

{{
    "intent": "string",
    "project_id": null,
    "entities": {{}},
    "constraints": {{}},
    "desired_outcome": "string"
}}

Rules:

- intent: describe what the user is asking for.
- project_id: numeric project ID if explicitly provided, otherwise null.
- entities: important named entities from the request.
- constraints: explicit requirements or limitations.
- desired_outcome: describe what the user wants to achieve.

User request:
{goal}
""".strip()