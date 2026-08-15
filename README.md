# Vendor Questionnaire Evidence Validator

An AI-assisted GRC engineering MVP that evaluates vendor questionnaire questions against submitted evidence.

The application retrieves relevant evidence, asks a local language model to assess whether the evidence supports the questionnaire requirement, validates the model's structured output, and resolves citations back to the original source.

## What It Does

For each questionnaire question, the application can:

- retrieve relevant evidence chunks
- determine a validation status
- explain what the evidence proves
- identify what the evidence does not prove
- identify gaps and contradictions
- recommend additional evidence
- provide a reviewer action
- cite the exact evidence source used
- preserve source provenance such as PDF page, section, spreadsheet row, or text line

## Validation Statuses

- validated
- partially_validated
- not_validated
- contradicted
- insufficient_evidence

The application includes consistency guardrails. For example, a result cannot be marked validated without supporting evidence and a valid source citation.

## Supported Questionnaire Formats

- XLSX
- CSV

## Supported Evidence Formats

- PDF
- DOCX
- XLSX
- CSV
- TXT

Images are not supported in the current MVP.

Scanned or image-only PDFs are not OCR'd.

## Architecture

The current MVP uses:

- Flask for the web application
- PyMuPDF for PDF extraction
- python-docx for DOCX extraction
- openpyxl and pandas for spreadsheet processing
- Sentence Transformers for semantic retrieval
- TF-IDF for lexical retrieval
- Ollama for local AI inference
- structured validation and citation verification in Python

Evidence provenance is created by the application rather than invented by the language model.

The model may cite only source IDs supplied by the retrieval layer. The backend resolves those IDs to the original file and source location.

## Local AI

The current development configuration uses Ollama with qwen3:14b.

Ollama must be installed and running locally before AI validation can be performed.

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

Run the full automated test suite with:

    python -m unittest discover -s tests -v

The test suite covers validation behavior, citation guardrails, and key Flask error-handling paths without requiring Ollama.

## Data Safety

The uploads/ directory is excluded from Git.

Do not commit real vendor evidence, questionnaires, client information, confidential assessment data, or other sensitive materials.

Public demonstrations should use synthetic or otherwise approved non-confidential data only.

## Current MVP Limitations

The following are intentionally deferred:

- OCR
- image evidence
- authentication
- user accounts
- production deployment
- external GRC integrations
- vector database
- persistent assessment storage
- automated remediation workflows
- large-scale batch optimization

The current workflow is:

    Question
    -> retrieve evidence
    -> evaluate requirement
    -> validate structured result
    -> verify citation
    -> present for human review

## Human Review

This tool is designed to assist a GRC reviewer, not replace reviewer judgment.

All results should remain subject to human review before being used for risk decisions.
