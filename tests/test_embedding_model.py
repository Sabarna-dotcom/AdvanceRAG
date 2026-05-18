"""
Tests for embedding model.
"""

import unittest

from src.embeddings.embedding_model import (
    OllamaEmbeddingModel
)


class TestOllamaEmbeddingModel(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        """
        Initialize embedding model once.
        """

        cls.embedder = (
            OllamaEmbeddingModel()
        )

    def test_single_embedding(self):
        """
        Test single text embedding.
        """

        text = (
            "Artificial Intelligence"
        )

        result = self.embedder.embed(
            text
        )

        self.assertIsInstance(
            result,
            list
        )

        self.assertGreater(
            len(result),
            0
        )

        self.assertIsInstance(
            result[0],
            list
        )

    def test_multiple_embeddings(self):
        """
        Test multiple embeddings.
        """

        texts = [
            "Machine Learning",
            "Deep Learning"
        ]

        result = self.embedder.embed(
            texts
        )

        self.assertEqual(
            len(result),
            2
        )

    def test_embedding_dimension(self):
        """
        Test embedding dimension.
        """

        dimension = (
            self.embedder.get_dimension()
        )

        self.assertIsInstance(
            dimension,
            int
        )

        self.assertGreater(
            dimension,
            0
        )

    def test_model_name(self):
        """
        Test model name.
        """

        model_name = (
            self.embedder.get_model_name()
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