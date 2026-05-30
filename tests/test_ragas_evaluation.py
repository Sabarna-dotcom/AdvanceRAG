"""
RAGAS Evaluation Test for the RAG pipeline.

Evaluates the full RAG pipeline using RAGAS metrics:
- Faithfulness: Is the answer grounded in the retrieved context?
- Answer Relevancy: Is the answer relevant to the question?
- Context Precision: Are the retrieved chunks relevant to the question?
- Context Recall: Do the retrieved chunks cover the ground truth?

Run with:

python -m tests.test_ragas_evaluation

or

python tests/test_ragas_evaluation.py
"""

import sys
import traceback

# ============================================================
# Helpers
# ============================================================

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_result(label: str, value):
    print(f"✓ {label}: {value}")


def print_fail(label: str, error):
    print(f"✗ {label}: {error}")


# ============================================================
# Thresholds — adjust as project matures
# ============================================================

FAITHFULNESS_MIN = 0.50
ANSWER_RELEVANCY_MIN = 0.50
CONTEXT_PRECISION_MIN = 0.40
CONTEXT_RECALL_MIN = 0.40


# ============================================================
# Eval Dataset
# Covers both PDF (biotechnology) and
# audio (Sigma Web Development) collections.
# ============================================================

EVAL_SAMPLES = [
    {
        "question": "What is biotechnology and its applications in agriculture?",
        "ground_truth": (
            "Biotechnology uses biological systems to develop products. "
            "In agriculture it includes somatic hybridization, genetic modification, "
            "and transgenic animals to increase food production."
        ),
        "collection": "pdf",
    },
    {
        "question": "What topics are covered in the Sigma Web Development course?",
        "ground_truth": (
            "The Sigma Web Development course covers all web development technologies "
            "including HTML, CSS, and JavaScript to build websites from scratch."
        ),
        "collection": "audio",
    },
    {
        "question": "How does recombinant DNA technology help in medicine?",
        "ground_truth": (
            "Recombinant DNA technology enables mass production of safe and effective "
            "therapeutic drugs."
        ),
        "collection": "pdf",
    },
]


# ============================================================
# Step 1: Run RAG pipeline and collect results
# ============================================================

def run_pipeline():
    print_header("STEP 1: Running RAG Pipeline")

    try:
        from src.retrieval.retrieval_manager import RetrievalManager
        from src.generation.generation_manager import GenerationManager

        retriever = RetrievalManager()
        print_result("Initialized", "RetrievalManager")

        manager = GenerationManager(use_self_reflection=False)
        print_result("Initialized", "GenerationManager")

    except Exception as e:
        print_fail("Initialization FAILED", e)
        traceback.print_exc()
        return None

    records = []

    for sample in EVAL_SAMPLES:
        question = sample["question"]
        ground_truth = sample["ground_truth"]
        collection = sample.get("collection")

        print(f"\n➜ Query: {question[:60]}...")

        try:
            # Retrieve
            chunks = retriever.retrieve(
                query=question,
                collection=collection,
                top_k=10,
            )

            print_result("Chunks retrieved", len(chunks))

            # Generate
            result = manager.generate(
                query=question,
                chunks=chunks,
                retriever=retriever,
                collection=collection,
            )

            answer = result.get("answer", "")
            contexts = [
                c.get("text", "")
                for c in chunks
                if c.get("text")
            ]

            print_result("Has answer", result["has_answer"])
            print_result("Answer preview", answer[:80])

            records.append(
                {
                    "question": question,
                    "answer": answer,
                    "contexts": contexts if contexts else ["No context retrieved."],
                    "ground_truth": ground_truth,
                }
            )

        except Exception as e:
            print_fail("Pipeline failed", e)
            traceback.print_exc()

            # Add placeholder so RAGAS still runs
            records.append(
                {
                    "question": question,
                    "answer": "",
                    "contexts": ["No context retrieved."],
                    "ground_truth": ground_truth,
                }
            )

    return records


# ============================================================
# Step 2: Run RAGAS evaluation
# ============================================================

def _build_ollama_llm():
    """
    Build a LangChain ChatOllama instance using project settings.
    Used as the judge LLM for RAGAS metrics.
    """

    from src.config.settings import get_settings
    from langchain_ollama import ChatOllama

    settings = get_settings()

    return ChatOllama(
        model=settings.ollama_llm_model,
        base_url=settings.ollama_base_url,
        temperature=0.0,
    )


def _build_ollama_embeddings():
    """
    Build a LangChain OllamaEmbeddings instance using project settings.
    Used by answer_relevancy metric.
    """

    from src.config.settings import get_settings
    from langchain_ollama import OllamaEmbeddings

    settings = get_settings()

    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )

def run_ragas(records):
    print_header("STEP 2: Running RAGAS Evaluation")

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            Faithfulness,
            ResponseRelevancy,
            LLMContextPrecisionWithoutReference,
            LLMContextRecall,
        )

        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper

        # Build Ollama judge LLM + embeddings
        ollama_llm = _build_ollama_llm()
        ollama_embeddings = _build_ollama_embeddings()

        ragas_llm = LangchainLLMWrapper(ollama_llm)
        ragas_embeds = LangchainEmbeddingsWrapper(ollama_embeddings)

        print_result("Judge LLM", ollama_llm.model)
        print_result("Embeddings", ollama_embeddings.model)

        # Inject Ollama into each metric (no OpenAI needed)
        metrics = [
            Faithfulness(),
            ResponseRelevancy(),
            LLMContextPrecisionWithoutReference(),
            LLMContextRecall(),
        ]

        for m in metrics:
            m.llm = ragas_llm
            if hasattr(m, "embeddings"):
                m.embeddings = ragas_embeds

        dataset = Dataset.from_list(records)
        print_result("Dataset size", len(dataset))

        result = evaluate(
            dataset,
            metrics=metrics,
        )

        df = result.to_pandas()

        print("\n" + "=" * 60)
        print("RAGAS RETURNED COLUMNS")
        print("=" * 60)
        print(df.columns.tolist())

        print("\n" + "=" * 60)
        print("RAGAS DATAFRAME")
        print("=" * 60)
        print(df)

        return df

    except ImportError as e:
        print_fail("Import FAILED", e)
        print("    -> Install with: pip install ragas datasets langchain-ollama")
        traceback.print_exc()
        return None

    except Exception as e:
        print_fail("RAGAS evaluation FAILED", e)
        traceback.print_exc()
        return None

# ============================================================
# Step 3: Assert metric thresholds
# ============================================================

def test_metrics(df):
    print_header("STEP 3: Metric Threshold Checks")
    threshold_map = {
        "faithfulness": FAITHFULNESS_MIN,
        "answer_relevancy": ANSWER_RELEVANCY_MIN,
        "response_relevancy": ANSWER_RELEVANCY_MIN,
        "context_precision": CONTEXT_PRECISION_MIN,
        "llm_context_precision_without_reference": CONTEXT_PRECISION_MIN,
        "context_recall": CONTEXT_RECALL_MIN,
        "llm_context_recall": CONTEXT_RECALL_MIN,
    }

    print("\nDetected columns:")
    print(df.columns.tolist())

    all_passed = True

    for col in df.columns:
        if col not in threshold_map:
            continue

        score = df[col].mean()
        if score >= threshold_map[col]:
            print(
                f"✓ {col:<45} "
                f"mean={score:.4f}"
            )
        else:
            print(
                f"✗ {col:<45} "
                f"mean={score:.4f}"
            )
            all_passed = False

    return all_passed

# ============================================================
# Step 4: Null check
# ============================================================

def test_no_nulls(df):
    print_header("STEP 4: Null Score Check")
    all_passed = True
    metric_cols = df.select_dtypes(include=["number"]).columns

    for col in metric_cols:

        nulls = df[col].isnull().sum()

        if nulls == 0:
            print(f"✓ {col}: no nulls")
        else:
            print(f"✗ {col}: {nulls} null values")
            all_passed = False

    return all_passed


# ============================================================
# Step 5: Per-sample breakdown
# ============================================================

def print_per_sample(df):
    print_header("STEP 5: Per-Sample Score Breakdown")

    metric_cols = df.select_dtypes(include=["number"]).columns

    for i, row in df.iterrows():

        print(f"\nSample {i+1}")

        for col in metric_cols:

            val = row[col]

            if val != val:
                print(f" ✗ {col:<45} NaN")
            else:
                print(f" ✓ {col:<45} {val:.4f}")

# ============================================================
# Step 6: Summary table
# ============================================================

def print_summary(df):
    print_header("RAGAS Score Summary")

    metric_cols = df.select_dtypes(include=["number"]).columns

    print(
        f"{'Metric':<45}"
        f"{'Mean':>10}"
        f"{'Min':>10}"
        f"{'Max':>10}"
    )

    print("-" * 80)

    for col in metric_cols:

        print(
            f"{col:<45}"
            f"{df[col].mean():>10.4f}"
            f"{df[col].min():>10.4f}"
            f"{df[col].max():>10.4f}"
        )

# ============================================================
# Main Runner
# ============================================================

def main():
    print("\n" + "=" * 40)
    print(" RAGAS EVALUATION SUITE")
    print("=" * 40)

    results = {}

    # Step 1
    records = run_pipeline()

    if not records:
        print("\n❌ Pipeline failed — cannot continue.")
        return False

    # Step 2
    df = run_ragas(records)

    if df is None:
        print("\n❌ RAGAS evaluation failed — cannot continue.")
        return False

    # Step 3
    results["Metric Thresholds"] = test_metrics(df)

    # Step 4
    results["No Null Scores"] = test_no_nulls(df)

    # Step 5
    print_per_sample(df)

    # Step 6
    print_summary(df)

    # Final result
    print_header("FINAL RESULTS")

    passed = 0
    failed = 0

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"

        print(f"{status} {test_name}")

        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 ALL RAGAS CHECKS PASSED")
    else:
        print(f"\n⚠️ {failed} check(s) failed — review scores above")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)