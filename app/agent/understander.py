from __future__ import annotations

import json
import re
from typing import Any

from app.llm.base import LLMClient
from app.models.understanding import Understanding, UnderstandingIntent


class Understander:
    """
    Converts a user's engineering request into structured understanding.
    """

    # Extract repository-relative paths explicitly mentioned by the user.
    FILE_PATH_PATTERN = re.compile(
        r"(?<![\w.-])"
        r"(?:[A-Za-z0-9_.-]+[/\\])*"
        r"[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,10}"
        r"(?![\w.-])"
    )

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def understand(self, goal: str) -> Understanding:
        """
        Understand the user's goal and extract explicitly named file paths.
        """

        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("Goal cannot be empty.")

        normalized_goal = goal.strip()
        prompt = self._build_prompt(normalized_goal)
        response = self.llm.generate(prompt)

        try:
            data: Any = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "LLM returned an invalid JSON response."
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "LLM must return a JSON object for understanding."
            )

        # File paths must come from the user's request, not be invented
        # by the LLM. Repository-based discovery will be added separately.
        file_paths = self._extract_file_paths(normalized_goal)

        data["file_paths"] = file_paths

        # Keep compatibility with the current single-file Planner.
        entities = data.get("entities")

        if not isinstance(entities, dict):
            entities = {}

        data["entities"] = entities

        if (
            data.get("intent") == UnderstandingIntent.READ_REPOSITORY_FILE.value
            and file_paths
        ):
            entities["path"] = file_paths[0]

        return Understanding.model_validate(data)

    @classmethod
    def _extract_file_paths(cls, goal: str) -> list[str]:
        """
        Extract unique, explicitly mentioned repository-relative paths.
        """

        paths: list[str] = []
        seen: set[str] = set()

        for match in cls.FILE_PATH_PATTERN.finditer(goal):
            path = match.group(0).replace("\\", "/")

            # Reject absolute paths and traversal components.
            if path.startswith("/") or any(
                part in {".", ".."} for part in path.split("/")
            ):
                continue

            if path not in seen:
                paths.append(path)
                seen.add(path)

        return paths

    @staticmethod
    def _build_prompt(goal: str) -> str:
        """
        Build the goal-understanding prompt.
        """

        return f"""
You are the understanding component of DevPilot,
an AI-powered software engineering agent.

Interpret the user's engineering request.
Do not create an execution plan or execute tools.
Do not invent information.

Return ONLY valid JSON with exactly these fields:

{{
    "intent": "inspect_project",
    "project_id": null,
    "entities": {{}},
    "constraints": {{}},
    "desired_outcome": "string",
    "file_paths": []
}}

Supported intents:

- inspect_project
- investigate_health
- manage_issue
- investigate_ci
- read_repository_file
- review_code
- unknown

Rules:

1. Choose the best supported intent for the request.

2. Use "read_repository_file" when the user explicitly requests
   reading or showing one or more repository files.

3. file_paths must contain only paths explicitly mentioned
   by the user. Never invent paths or infer unmentioned paths.

4. If no file paths are explicitly mentioned, return an empty
   file_paths list.

5. For a single-file request, entities may contain the key "path".

6. project_id must be numeric if explicitly provided;
   otherwise return null.

7. entities and constraints must be dictionaries with string
   keys and values.

8. desired_outcome must describe the user's intended result.

9. Return valid JSON only. Do not use Markdown code fences.

10. Choose "review_code" when the user asks to review,
    inspect for bugs, evaluate code quality, identify
    potential issues, or recommend code improvements.
    Preserve explicitly mentioned file paths in file_paths.
    Do not choose "read_repository_file" when the primary
    goal is code review.

USER REQUEST:
{goal}
""".strip()