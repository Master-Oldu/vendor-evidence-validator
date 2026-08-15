# Vendor Evidence Validator

An AI-assisted third-party risk evidence-validation MVP that evaluates vendor questionnaire items against submitted evidence and returns structured, source-cited results for human review.

The project focuses on a common TPRM problem: a questionnaire response may state that a control exists, but the response itself is not proof. When a vendor answer is available, the application treats it as a claim to be validated rather than as evidence.

The workflow retrieves relevant evidence, evaluates whether the submitted material supports the questionnaire item, validates the AI's structured output, verifies cited source IDs, and resolves those citations back to the original evidence location.

## Demo

![Synthetic validation results](docs/assets/vendor-validator-results-demo.png)

*Synthetic demonstration of third-party risk evidence validation results. No real vendor or client data is used.*

## What It Does

For each vendor questionnaire item, the application can:

- retrieve the most relevant submitted evidence
- determine a structured validation status
- explain what the evidence supports
- identify what the evidence does not establish
- identify evidence gaps and contradictions
- recommend additional evidence when needed
- provide a reviewer action
- cite the evidence used in the assessment
- preserve source provenance such as PDF page, document section, spreadsheet row, or text line
- require human review before a final risk decision

## Validation Statuses

The application uses five validation outcomes:

- `validated`
- `partially_validated`
- `not_validated`
- `contradicted`
- `insufficient_evidence`

These statuses are subject to backend consistency checks.

For example, a result cannot be accepted as `validated` unless supporting evidence exists and the cited source reference is valid. A contradiction must also be supported by retrieved evidence rather than inferred without a source.

## Evidence and Citation Model

Evidence provenance is created by the application, not by the language model.

Each extracted evidence chunk receives a source ID. Depending on the file type, provenance can include information such as:

- PDF page number and section
- DOCX heading or block location
- spreadsheet sheet, row, and cell range
- CSV row
- TXT line range

The language model may cite only source IDs supplied by the retrieval layer.

The backend then verifies those source IDs and resolves them to the original file and source location. This prevents the model from inventing filenames, page numbers, section names, or other citation details.

## Retrieval

The current retrieval layer combines:

- Sentence Transformers semantic similarity
- TF-IDF lexical similarity

The two scores are combined to retrieve the evidence chunks most relevant to each questionnaire item before AI validation occurs.

Retrieval happens before the language model is asked to make a validation decision.

## Supported Formats

**Questionnaires**

- XLSX
- CSV

**Evidence**

- PDF
- DOCX
- XLSX
- CSV
- TXT

Images are not supported in the current MVP.

Scanned or image-only PDF pages are not OCR'd.

## Architecture

The current MVP uses:

- Flask for the web application
- PyMuPDF for PDF extraction
- python-docx for DOCX extraction
- openpyxl and pandas for spreadsheet processing
- Sentence Transformers for semantic retrieval
- TF-IDF for lexical retrieval
- Ollama for local AI inference
- Python validation logic for structured-output consistency and citation verification

The core flow is:

    Questionnaire item
        ↓
    Retrieve relevant evidence
        ↓
    AI-assisted evidence assessment
        ↓
    Validate structured result
        ↓
    Verify cited source IDs
        ↓
    Resolve source provenance
        ↓
    Present result for human review

The language model performs reasoning over retrieved evidence, while provenance and citation integrity remain controlled by the application backend.

## Local AI

The current development configuration uses Ollama with `qwen3:14b`.

AI inference runs locally rather than through an external LLM API. Vendor evidence therefore remains within the local environment during model inference.

Ollama must be installed and running before AI validation can be performed.

The application expects Ollama at:

    http://localhost:11434

## Setup

Create and activate a Python virtual environment.

Install dependencies:

    pip install -r requirements.txt

Install Ollama separately and pull the configured model:

    ollama pull qwen3:14b

Run the application:

    python app.py

Then open the local Flask URL shown in Terminal.

## Tests

Run the automated test suite with:

    python -m unittest discover -s tests -v

The test suite covers validation behavior, status consistency, citation guardrails, unsupported source references, normalization behavior, and key Flask error-handling paths without requiring Ollama.

## Data Safety

The `uploads/` directory is excluded from Git.

Real vendor evidence, questionnaires, client information, confidential assessment data, and other sensitive materials should never be committed to the public repository.

Public demonstrations should use synthetic or otherwise approved non-confidential data only.

## Current MVP Limitations

The following are intentionally deferred from the current version:

- OCR
- image and screenshot evidence
- authentication
- user accounts
- production deployment
- external GRC platform integrations
- vector database
- persistent assessment storage
- automated remediation workflows
- large-scale batch optimization

These are product-expansion opportunities rather than requirements for demonstrating the core evidence-validation workflow.

## Human Review

Vendor evidence is rarely binary, and assessment context matters.

This tool is designed to support a third-party risk reviewer, not replace professional judgment. The application retrieves evidence, structures the reasoning, exposes gaps and contradictions, and provides traceable citations, but the final validation and risk decision remain human-owned.