from __future__ import annotations

import json

from app.llm.base import LLMClient
from app.models.understanding import Understanding


class Understander:
    """
    Converts a user's engineering request into structured Understanding
    using an LLM.
    """

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def understand(self, goal: str) -> Understanding:
        """
        Interpret the user's goal and validate the resulting structure.
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
        Build the prompt used to understand the user's request.
        """

        return f"""
You are the understanding component of DevPilot,
an engineering intelligence agent.

Your job is to interpret the user's engineering request
and convert it into structured JSON.

Do not create an execution plan.
Do not execute any tools.
Do not invent information that is not present in the request.

Return ONLY valid JSON with exactly these fields:

{{
    "intent": "inspect_project",
    "project_id": null,
    "entities": {{}},
    "constraints": {{}},
    "desired_outcome": "string"
}}

Rules:

- intent MUST be exactly one of:
  "inspect_project",
  "investigate_health",
  "manage_issue",
  "investigate_ci",
  "unknown".

- project_id: numeric project ID if explicitly provided
  in the user's request; otherwise null.

- entities: important named entities from the request,
  represented as a dictionary of string keys and values.

- constraints: explicit requirements or limitations,
  represented as a dictionary of string keys and values.

- desired_outcome: describe what the user wants to achieve.

- Do not return Markdown or code fences.
- Return valid JSON only.

User request:
{goal}
""".strip()