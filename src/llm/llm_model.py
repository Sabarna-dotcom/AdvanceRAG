"""
Local LLM model using Ollama.
"""

import ollama

from src.config.llm_config import (
    get_config
)

from src.utils.logger import (
    get_logger
)

from src.utils.exceptions import (
    LLMException
)

# ==========================================
# Logger
# ==========================================

logger = get_logger(__name__)


class OllamaLLM:
    """
    Wrapper for Ollama LLM models.
    """

    def __init__(self):
        """
        Initialize Ollama client.
        """

        try:

            logger.info(
                "Initializing Ollama LLM..."
            )

            self.config = get_config()

            self.model_name = (
                self.config.model_name
            )

            self.client = ollama.Client(
                host=(
                    self.config
                    .ollama_base_url
                )
            )

            logger.info(
                f"Ollama LLM initialized "
                f"successfully | "
                f"Model: {self.model_name}"
            )

        except Exception as error:

            logger.exception(
                "Failed to initialize "
                "Ollama LLM."
            )

            raise LLMException(

                message=(
                    "LLM initialization failed"
                ),

                details=str(error)

            ) from error

    def generate(
        self,
        prompt: str
    ) -> str:
        """
        Generate response from LLM.
        """

        try:

            logger.info(
                "Generating LLM response."
            )

            if not prompt.strip():

                logger.warning(
                    "Empty prompt received."
                )

                raise LLMException(
                    message="Prompt cannot be empty"
                )

            response = self.client.chat(

                model=self.model_name,

                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            generated_text = (
                response["message"]["content"]
            )

            logger.info(
                "LLM response generated "
                "successfully."
            )

            return generated_text

        except LLMException:

            raise

        except Exception as error:

            logger.exception(
                "LLM generation failed."
            )

            raise LLMException(

                message=(
                    "Failed to generate "
                    "LLM response"
                ),

                details=str(error)

            ) from error

    def get_model_name(self) -> str:
        """
        Return current model name.
        """

        logger.debug(
            f"Fetching model name: "
            f"{self.model_name}"
        )

        return self.model_name


# ==========================================
# Example Usage
# ==========================================

if __name__ == "__main__":

    try:

        llm = OllamaLLM()

        response = llm.generate(
            "Explain vector databases simply"
        )

        print(response)

    except LLMException as error:

        logger.error(
            f"Application failed: {error}"
        )

        print(
            f"Error: {error}"
        )