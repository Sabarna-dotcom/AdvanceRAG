"""
Generation layer package.

Exposes:
    ContextBuilder     - formats retrieved chunks into numbered context string
    PromptBuilder      - builds RAG, reflection, and rephrase prompts
    ResponseParser     - extracts answer and citations from LLM output
    SelfReflection     - evaluates answer quality and signals corrective retrieval
    GenerationManager  - full pipeline orchestrator (retrieve -> generate -> reflect)
"""

from src.generation.context_builder import ContextBuilder
from src.generation.prompt_builder import PromptBuilder
from src.generation.response_parser import ResponseParser
from src.generation.self_reflection import SelfReflection
from src.generation.generation_manager import GenerationManager

__all__ = [
    "ContextBuilder",
    "PromptBuilder",
    "ResponseParser",
    "SelfReflection",
    "GenerationManager",
]