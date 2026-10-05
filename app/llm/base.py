from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """
    Generic interface for an LLM provider.
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate a normal text response from the LLM.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        schema_name: str,
    ) -> str:
        """
        Generate a structured JSON response from the LLM
        using the provided JSON schema.
        """
        raise NotImplementedError