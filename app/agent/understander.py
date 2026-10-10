from __future__ import annotations

import json

from app.llm.base import LLMClient
from app.models.understanding import Understanding


class Understander:
    """
    Converts a user's engineering request into structured data.
    """

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def understand(self, goal: str) -> Understanding:
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
        return f"""
You are the understanding component of DevPilot,
an engineering intelligence agent.

Interpret the user's engineering request.
Do not create an execution plan or execute tools.
Do not invent information.

Return ONLY valid JSON with exactly these fields:

{{
    "intent": "inspect_project",
    "project_id": null,
    "entities": {{}},
    "constraints": {{}},
    "desired_outcome": "string"
}}

Supported intents are:

- inspect_project
- investigate_health
- manage_issue
- investigate_ci
- read_repository_file
- unknown

Rules:

1. If the user explicitly requests reading, opening, or showing
   the contents of a specific repository file, use the intent
   "read_repository_file".

2. For file-reading requests, store the exact repository-relative
   file path in entities under the key "path".
   Example: {{"path": "app/main.py"}}

3. Do not invent a file path if the user did not provide one.

4. For other requests, select the best matching supported intent.

5. project_id must be a numeric ID if explicitly specified,
   otherwise null.

6. entities and constraints must be dictionaries with string
   keys and string values.

7. desired_outcome must describe what the user wants to achieve.

8. Return valid JSON only. Do not use Markdown or code fences.

User request:
{goal}
""".strip()