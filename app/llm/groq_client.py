from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq

from app.llm.base import LLMClient


load_dotenv()


class GroqClient(LLMClient):
    """
    Groq implementation of the generic LLM client.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "openai/gpt-oss-20b",
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set."
            )

        self.model = model
        self.client = Groq(api_key=self.api_key)

    def generate(self, prompt: str) -> str:
        """
        Generate a normal text response from Groq.
        """

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response.choices[0].message.content or ""

    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        schema_name: str,
    ) -> str:
        """
        Generate a structured JSON response from Groq.
        """

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        if not schema:
            raise ValueError("Schema cannot be empty.")

        if not schema_name.strip():
            raise ValueError("Schema name cannot be empty.")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        )

        return response.choices[0].message.content or ""