from pathlib import Path

from flask import Flask, render_template, request

from services.ai_provider import OllamaProvider
from services.citation_resolver import (
    resolve_source_references,
)
from services.evidence_parser import process_evidence_files
from services.evidence_retriever import EvidenceRetriever
from services.evidence_validator import validate_question
from services.questionnaire_parser import (
    detect_questionnaire_sheets,
    parse_questionnaire_with_mapping,
)


app = Flask(__name__)

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

DEFAULT_VALIDATION_START = 1
DEFAULT_VALIDATION_BATCH_SIZE = 3

ALLOWED_VALIDATION_BATCH_SIZES = {
    1,
    3,
    5,
}


def render_validation_error(
    message,
    detail=None,
    status_code=400,
):
    return (
        render_template(
            "error.html",
            message=message,
            detail=detail,
        ),
        status_code,
    )


def get_validation_start(form_value):
    try:
        validation_start = int(
            form_value
        )
    except (TypeError, ValueError):
        return DEFAULT_VALIDATION_START

    if validation_start < 1:
        return DEFAULT_VALIDATION_START

    return validation_start


def get_validation_limit(form_value):
    try:
        validation_limit = int(
            form_value
        )
    except (TypeError, ValueError):
        return DEFAULT_VALIDATION_BATCH_SIZE

    if (
        validation_limit
        not in ALLOWED_VALIDATION_BATCH_SIZES
    ):
        return DEFAULT_VALIDATION_BATCH_SIZE

    return validation_limit


def summarize_evidence_document(document):
    summary = {
        "evidence_id": document["evidence_id"],
        "file_name": document["file_name"],
        "file_type": document["file_type"],
        "extraction_status": document["extraction_status"],
        "chunk_count": document["chunk_count"],
    }

    optional_fields = [
        "page_count",
        "extractable_page_count",
        "block_count",
        "row_count",
        "line_count",
    ]

    for field in optional_fields:
        if field in document:
            summary[field] = document[field]

    return summary


def validate_question_batch(
    questions,
    evidence_documents,
    start_position,
    batch_size,
):
    if not questions or not evidence_documents:
        return []

    start_index = start_position - 1

    if start_index >= len(questions):
        return []

    retriever = EvidenceRetriever(
        evidence_documents
    )

    ai_provider = OllamaProvider()

    questions_to_validate = questions[
        start_index:
        start_index + batch_size
    ]

    batch_results = []

    for batch_index, question in enumerate(
        questions_to_validate,
        start=1,
    ):
        question_position = (
            start_index
            + batch_index
        )

        retrieved_evidence = []

        try:
            retrieved_evidence = retriever.search(
                question_text=question[
                    "question_text"
                ],
                description=question.get(
                    "description"
                ),
            )

            if not retrieved_evidence:
                raise ValueError(
                    "No evidence chunks were available "
                    "for validation."
                )

            validation_result = validate_question(
                question=question,
                retrieved_evidence=(
                    retrieved_evidence
                ),
                ai_provider=ai_provider,
            )

            resolved_sources = (
                resolve_source_references(
                    validation_result,
                    retrieved_evidence,
                )
            )

            batch_results.append(
                {
                    "batch_index": batch_index,
                    "question_position": (
                        question_position
                    ),
                    "question": question,
                    "retrieval": {
                        "results_found": len(
                            retrieved_evidence
                        ),
                        "retrieved_evidence": (
                            retrieved_evidence
                        ),
                    },
                    "validation": (
                        validation_result
                    ),
                    "resolved_sources": (
                        resolved_sources
                    ),
                    "error": None,
                }
            )

        except Exception as error:
            batch_results.append(
                {
                    "batch_index": batch_index,
                    "question_position": (
                        question_position
                    ),
                    "question": question,
                    "retrieval": {
                        "results_found": len(
                            retrieved_evidence
                        ),
                        "retrieved_evidence": (
                            retrieved_evidence
                        ),
                    },
                    "validation": None,
                    "resolved_sources": [],
                    "error": str(error),
                }
            )

    return batch_results


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        questionnaire = request.files.get(
            "questionnaire"
        )

        evidence_files = request.files.getlist(
            "evidence"
        )

        if (
            not questionnaire
            or not questionnaire.filename
        ):
            return render_validation_error(
                "A questionnaire file is required.",
                (
                    "Upload an XLSX or CSV "
                    "questionnaire before continuing."
                ),
            )

        valid_evidence_files = [
            file
            for file in evidence_files
            if file and file.filename
        ]

        if not valid_evidence_files:
            return render_validation_error(
                "At least one evidence file is required.",
                (
                    "Upload supporting evidence before "
                    "running questionnaire validation."
                ),
            )

        questionnaire_path = (
            UPLOAD_FOLDER
            / questionnaire.filename
        )

        questionnaire.save(
            questionnaire_path
        )

        saved_evidence_names = []

        for file in valid_evidence_files:
            evidence_path = (
                UPLOAD_FOLDER
                / file.filename
            )

            file.save(
                evidence_path
            )

            saved_evidence_names.append(
                file.filename
            )

        sheets = detect_questionnaire_sheets(
            questionnaire_path
        )

        if not sheets:
            return render_validation_error(
                "No questionnaire worksheets could be detected.",
                (
                    "Check that the uploaded file contains "
                    "readable questionnaire data."
                ),
            )

        return render_template(
            "select_sheets.html",
            questionnaire_name=(
                questionnaire.filename
            ),
            evidence_names=(
                saved_evidence_names
            ),
            sheets=sheets,
        )

    return render_template(
        "index.html"
    )


@app.route(
    "/select-sheets",
    methods=["POST"],
)
def select_sheets():
    questionnaire_name = request.form.get(
        "questionnaire_name"
    )

    selected_sheets = request.form.getlist(
        "selected_sheets"
    )

    evidence_names = request.form.getlist(
        "evidence_names"
    )

    if not questionnaire_name:
        return render_validation_error(
            "Questionnaire information is missing."
        )

    questionnaire_path = (
        UPLOAD_FOLDER
        / questionnaire_name
    )

    if not questionnaire_path.exists():
        return render_validation_error(
            "The questionnaire file could not be found.",
            questionnaire_name,
            status_code=404,
        )

    if not selected_sheets:
        return render_validation_error(
            "Select at least one worksheet.",
            (
                "Choose the worksheet or worksheets "
                "that contain questionnaire questions."
            ),
        )

    all_sheets = detect_questionnaire_sheets(
        questionnaire_path
    )

    selected_sheet_structures = [
        sheet
        for sheet in all_sheets
        if sheet["sheet_name"]
        in selected_sheets
    ]

    if not selected_sheet_structures:
        return render_validation_error(
            "None of the selected worksheets could be processed."
        )

    return render_template(
        "map_selected_sheets.html",
        questionnaire_name=(
            questionnaire_name
        ),
        evidence_names=evidence_names,
        sheets=selected_sheet_structures,
    )


@app.route(
    "/map-selected-sheets",
    methods=["POST"],
)
def map_selected_sheets():
    questionnaire_name = request.form.get(
        "questionnaire_name"
    )

    evidence_names = request.form.getlist(
        "evidence_names"
    )

    validation_start = get_validation_start(
        request.form.get(
            "validation_start"
        )
    )

    validation_limit = get_validation_limit(
        request.form.get(
            "validation_limit"
        )
    )

    if not questionnaire_name:
        return render_validation_error(
            "Questionnaire information is missing."
        )

    questionnaire_path = (
        UPLOAD_FOLDER
        / questionnaire_name
    )

    if not questionnaire_path.exists():
        return render_validation_error(
            "The questionnaire file could not be found.",
            questionnaire_name,
            status_code=404,
        )

    try:
        sheet_count = int(
            request.form.get(
                "sheet_count",
                0,
            )
        )

    except (TypeError, ValueError):
        return render_validation_error(
            "Worksheet count is invalid.",
            (
                "Return to the worksheet selection "
                "step and try again."
            ),
        )

    if sheet_count < 1:
        return render_validation_error(
            "No questionnaire worksheets were provided for mapping."
        )

    all_questions = []
    sheet_results = []

    for index in range(sheet_count):
        sheet_name = request.form.get(
            f"sheet_name_{index}"
        )

        header_row = request.form.get(
            f"header_row_{index}"
        )

        question_column = request.form.get(
            f"question_column_{index}"
        )

        id_column = request.form.get(
            f"id_column_{index}"
        )

        answer_column = request.form.get(
            f"answer_column_{index}"
        )

        description_column = request.form.get(
            f"description_column_{index}"
        )

        if (
            not sheet_name
            or not header_row
            or not question_column
        ):
            return render_validation_error(
                "Worksheet mapping is incomplete.",
                (
                    "Each selected worksheet must "
                    "include a question column."
                ),
            )

        try:
            questions = (
                parse_questionnaire_with_mapping(
                    file_path=questionnaire_path,
                    sheet_name=sheet_name,
                    header_row=int(
                        header_row
                    ),
                    question_column=(
                        question_column
                    ),
                    id_column=(
                        id_column or None
                    ),
                    answer_column=(
                        answer_column or None
                    ),
                    description_column=(
                        description_column
                        or None
                    ),
                )
            )

        except (TypeError, ValueError) as error:
            return render_validation_error(
                "The worksheet mapping could not be processed.",
                str(error),
            )

        all_questions.extend(
            questions
        )

        sheet_results.append(
            {
                "sheet_name": sheet_name,
                "questions_parsed": len(
                    questions
                ),
                "mapping": {
                    "question_column": (
                        question_column
                    ),
                    "id_column": (
                        id_column or None
                    ),
                    "answer_column": (
                        answer_column or None
                    ),
                    "description_column": (
                        description_column
                        or None
                    ),
                },
            }
        )

    if not all_questions:
        return render_validation_error(
            "No questionnaire questions were parsed.",
            (
                "Check the worksheet and column "
                "mapping selections."
            ),
        )

    if validation_start > len(
        all_questions
    ):
        return render_validation_error(
            "The selected starting question is outside the questionnaire.",
            (
                f"This questionnaire contains "
                f"{len(all_questions)} parsed questions, "
                f"but you requested question "
                f"{validation_start}."
            ),
        )

    if not evidence_names:
        return render_validation_error(
            "No evidence files are available for validation."
        )

    evidence_paths = [
        UPLOAD_FOLDER / evidence_name
        for evidence_name in evidence_names
    ]

    missing_evidence = [
        path.name
        for path in evidence_paths
        if not path.exists()
    ]

    if missing_evidence:
        return render_validation_error(
            "One or more evidence files could not be found.",
            ", ".join(
                missing_evidence
            ),
            status_code=404,
        )

    evidence_documents = (
        process_evidence_files(
            evidence_paths
        )
    )

    evidence_results = [
        summarize_evidence_document(
            document
        )
        for document in evidence_documents
    ]

    total_chunks = sum(
        document["chunk_count"]
        for document in evidence_documents
    )

    if total_chunks == 0:
        return render_validation_error(
            "No usable evidence content could be extracted.",
            (
                "Supported evidence types are PDF, DOCX, XLSX, "
                "CSV, and TXT. Image files are not supported, "
                "and scanned or image-only PDFs are not OCR'd "
                "in this version."
            ),
        )

    validation_batch = (
        validate_question_batch(
            questions=all_questions,
            evidence_documents=(
                evidence_documents
            ),
            start_position=(
                validation_start
            ),
            batch_size=(
                validation_limit
            ),
        )
    )

    successful_validations = sum(
        1
        for result in validation_batch
        if (
            result["validation"]
            is not None
            and result["error"] is None
        )
    )

    failed_validations = sum(
        1
        for result in validation_batch
        if result["error"] is not None
    )

    return render_template(
        "results.html",
        questionnaire_name=(
            questionnaire_name
        ),
        questions_parsed=len(
            all_questions
        ),
        questions_attempted=len(
            validation_batch
        ),
        successful_validations=(
            successful_validations
        ),
        failed_validations=(
            failed_validations
        ),
        validation_start=(
            validation_start
        ),
        validation_batch_size=(
            validation_limit
        ),
        validation_results=(
            validation_batch
        ),
        evidence_files_processed=len(
            evidence_documents
        ),
        total_evidence_chunks=(
            total_chunks
        ),
        evidence_results=(
            evidence_results
        ),
        sheet_results=(
            sheet_results
        ),
    )


if __name__ == "__main__":
    app.run(
        debug=True
    )