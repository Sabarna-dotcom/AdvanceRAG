
# Advanced PDF RAG Ingestion Pipeline — Complete Explanation

# 1. Purpose

This pipeline processes PDF documents and converts them into structured AI-searchable chunks for Retrieval-Augmented Generation (RAG).

Flow:

PDF Documents → Structured Chunks → Vector Database → Better LLM Answers

---

# 2. Overall PDF Pipeline Architecture

```text
RAW PDF FILES
      ↓
pdf_loader.py
      ↓
document_processor.py
      ↓
chunking_strategies.py
      ↓
parent_child_chunker.py
      ↓
metadata_extractor.py
      ↓
run_pdf_pipeline.py
      ↓
processed/
├── chunks/
├── parent_chunks/
├── child_chunks/
└── metadata/
```

---

# 3. run_pdf_pipeline.py

This is the execution file for all PDFs.

Responsibilities:

- Reads all PDF files
- Processes PDFs
- Creates parent chunks
- Creates child chunks
- Extracts metadata
- Saves processed outputs

---

# 4. PDF Processing Flow

## Step 1 — Read PDF Files

```python
pdf_dir = "data/raw/pdfs"
```

Loops through:

```python
for file_name in os.listdir(pdf_dir):
```

Processes every:

```python
.pdf
```

file.

---

# 5. document_processor.py

Main orchestration layer.

Responsible for:

- PDF loading
- Chunk generation
- Parent-child mapping
- Metadata attachment

---

# Internal Flow

```text
Load PDF
    ↓
Extract text
    ↓
Create parent chunks
    ↓
Create child chunks
    ↓
Attach metadata
    ↓
Return structured chunks
```

---

# 6. chunking_strategies.py

Defines:

- chunk size
- overlap
- semantic splitting logic

Example:

```python
chunk_size = 500
overlap = 50
```

Purpose:

- better embeddings
- semantic retrieval
- optimized vector search

---

# 7. parent_child_chunker.py

Most important module.

Creates:

1. Parent chunks
2. Child chunks

---

# Example PDF Content

```text
Human reproduction is a biological process.
Reproductive organs are essential.
Fertilization occurs inside the body.
```

---

# Parent Chunk Example

```json
{
   "parent_id": "P1",
   "parent_text": "Human reproduction is a biological process..."
}
```

Large contextual block.

---

# Child Chunk Example

```json
{
   "chunk_id": "C1",
   "parent_id": "P1",
   "text": "Fertilization occurs inside the body."
}
```

Small searchable semantic chunk.

---

# Parent-Child Relationship Diagram

```text
                    PARENT CHUNK
┌─────────────────────────────────────────┐
│ Parent ID : P1                         │
│ Human reproduction biological process  │
│ Reproductive organs essential          │
│ Fertilization occurs inside body       │
└──────────────────┬──────────────────────┘
                   │
      ┌────────────┼────────────┐
      ▼            ▼            ▼

┌───────────┐ ┌───────────┐ ┌───────────┐
│ CHILD C1  │ │ CHILD C2  │ │ CHILD C3  │
│ Human     │ │ Organs    │ │ Fertiliza │
│ reproduct │ │ essential │ │ tion body │
└───────────┘ └───────────┘ └───────────┘
```

---

# 8. metadata_extractor.py

Adds metadata:

```json
{
   "source_type": "pdf",
   "source_name": "Human Reproduction.pdf",
   "page": 1
}
```

Purpose:

- source tracking
- citations
- filtering
- provenance

---

# 9. Generated Outputs

## A. pdf_chunks.json

Contains:

- parent chunk
- child chunk
- metadata

Used for:
- debugging
- inspection
- testing

---

## B. pdf_parent_chunks.json

Contains:

```json
{
   "parent_id": "...",
   "parent_text": "..."
}
```

Used for:
- contextual retrieval

---

## C. pdf_child_chunks.json

Contains:

```json
{
   "chunk_id": "...",
   "parent_id": "...",
   "text": "..."
}
```

Used for:
- vector embeddings
- semantic similarity search

---

## D. pdf_metadata.json

Contains:

```json
{
   "chunk_id": "...",
   "metadata": {...}
}
```

Used for:
- filtering
- citations
- tracing sources

---

# 10. Retrieval Flow Example

User asks:

```text
What is fertilization?
```

---

# Step 1 — Vector Search

Search happens on:

```text
child chunks
```

Matching chunk:

```text
Fertilization occurs inside the body.
```

---

# Step 2 — Parent Retrieval

Using:

```text
parent_id
```

System retrieves full context:

```text
Human reproduction biological process...
Reproductive organs essential...
Fertilization occurs inside body...
```

---

# Step 3 — LLM Answer

LLM receives:

- matching child chunk
- full parent context

Result:

- accurate answer
- better context
- fewer hallucinations

---

# 11. Why Parent-Child Retrieval?

## Small Child Chunks

Good for:
- semantic search
- embedding similarity

---

## Large Parent Chunks

Good for:
- contextual understanding
- answer generation

---

# Combined Benefit

Your architecture provides:

- better retrieval quality
- scalable design
- production-grade RAG
- accurate contextual answers

---

# 12. Simple Analogy

Parent Chunk:
- whole chapter

Child Chunk:
- paragraph inside chapter

Retrieval:
1. Search paragraph
2. Retrieve chapter
3. Generate contextual answer
