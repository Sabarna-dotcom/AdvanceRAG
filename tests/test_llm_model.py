"""
Tests for Ollama LLM model.
"""

import unittest

from src.llm.llm_model import (
    OllamaLLM
)


class TestOllamaLLM(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        """
        Initialize LLM once.
        """

        cls.llm = OllamaLLM()

    def test_generate_response(self):
        """
        Test LLM response generation.
        """

        prompt = (
            "Explain vector databases simply."
        )

        response = self.llm.generate(
            prompt
        )

        self.assertIsInstance(
            response,
            str
        )

        self.assertGreater(
            len(response),
            0
        )

    def test_model_name(self):
        """
        Test model name retrieval.
        """

        model_name = (
            self.llm.get_model_name()
        )

        self.assertIsInstance(
            model_name,
            str
        )

        self.assertGreater(
            len(model_name),
            0
        )


if __name__ == "__main__":

    unittest.main()