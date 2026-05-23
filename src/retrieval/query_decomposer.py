"""
Query decomposer - uses Ollama LLM to break
complex queries into simpler sub-questions.

This `QueryDecomposer` code helps the RAG system handle complex user queries by breaking a large or multi-part question into several smaller and simpler sub-questions using an Ollama LLM.
The system sends the original query to the LLM with a prompt asking for 3–5 sub-questions, then parses and cleans the generated response into a structured list.
These smaller queries can later be processed individually for retrieval, which improves context understanding, retrieval accuracy, and coverage of different aspects of a complex question.

"""

from typing import List

from src.llm.llm_model import OllamaLLM
from src.utils.logger import get_logger
from src.utils.exceptions import LLMException

logger = get_logger(__name__)


class QueryDecomposer:
    """
    Decomposes a complex query into multiple
    simpler sub-questions using the LLM.
    """

    def __init__(self):

        try:

            logger.info(
                "Initializing QueryDecomposer."
            )

            self.llm = OllamaLLM()

            logger.info(
                "QueryDecomposer initialized successfully."
            )

        except Exception as error:

            logger.exception(
                "QueryDecomposer initialization failed."
            )

            raise LLMException(
                message="Failed to initialize QueryDecomposer",
                details=str(error)
            ) from error

    def decompose(
        self,
        query: str
    ) -> List[str]:
        """
        Break a complex query into 3-5 sub-questions.

        Args:

            query:
                The original user query

        Returns:

            List of sub-questions
            (includes original query)
        """

        try:

            logger.info(
                f"Decomposing query: "
                f"{query[:80]}..."
            )

            prompt = f"""
            Break the following question into 3 to 5 simpler sub-questions.

            Each sub-question should be on its own line starting with a dash (-).
            Only return the sub-questions, nothing else.

            Question: {query}

            Sub-questions:
            """

            response = self.llm.generate(prompt)

            sub_questions = self.parse_sub_questions(
                response
            )

            # Always include original query
            if query not in sub_questions:

                sub_questions.insert(0, query)

            logger.info(
                f"Decomposed into "
                f"{len(sub_questions)} sub-questions."
            )

            return sub_questions

        except LLMException:

            raise

        except Exception as error:

            logger.exception(
                "Query decomposition failed."
            )

            # Fallback: return original query only
            logger.warning(
                "Falling back to original query."
            )

            return [query]

    def parse_sub_questions(
        self,
        response: str
    ) -> List[str]:
        """
        Parse LLM response into a list of sub-questions.
        """

        lines = response.strip().split("\n")

        questions = []

        for line in lines:

            line = line.strip()

            # Remove leading dashes, numbers, bullets
            for prefix in ["-", "*", "•"]:

                if line.startswith(prefix):

                    line = line[len(prefix):].strip()

            # Remove numbered prefixes like "1." "2)"
            if (
                len(line) > 2
                and line[0].isdigit()
                and line[1] in [".", ")"]
            ):

                line = line[2:].strip()

            if line and len(line) > 5:

                questions.append(line)

        return questions