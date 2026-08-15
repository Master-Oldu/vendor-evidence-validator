from pathlib import Path

import pandas as pd


HEADER_HINTS = {
    "question",
    "question text",
    "security question",
    "control",
    "control id",
    "requirement",
    "description",
    "response",
    "answer",
    "vendor answer",
    "unique identifier",
    "identifier",
    "id",
    "justification",
    "question type",
    "pre-selected options",
    "options",
}

QUESTION_HINTS = {
    "question",
    "question text",
    "security question",
    "control",
    "requirement",
}


def inspect_questionnaire(file_path):
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".xlsx":
        workbook = pd.ExcelFile(file_path)

        result = {}

        for sheet_name in workbook.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            result[sheet_name] = {
                "rows": len(df),
                "columns": df.columns.tolist(),
            }

        return result

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)

        return {
            "CSV": {
                "rows": len(df),
                "columns": df.columns.tolist(),
            }
        }

    raise ValueError("Unsupported questionnaire format")


def _find_best_header_for_sheet(file_path, sheet_name):
    raw_df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        header=None,
    )

    candidates = []

    for row_index in range(min(25, len(raw_df))):
        raw_values = [
            str(value).strip()
            for value in raw_df.iloc[row_index].tolist()
            if pd.notna(value) and str(value).strip()
        ]

        if len(raw_values) < 2:
            continue

        normalized_values = [
            value.lower()
            for value in raw_values
        ]

        header_hint_count = sum(
            1
            for value in normalized_values
            if value in HEADER_HINTS
        )

        question_hint_count = sum(
            1
            for value in normalized_values
            if value in QUESTION_HINTS
        )

        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=row_index,
        )

        columns = [
            str(column).strip()
            for column in df.columns
            if not str(column).startswith("Unnamed:")
        ]

        if len(columns) < 2:
            continue

        non_empty_rows = df.dropna(how="all").shape[0]

        candidates.append(
            {
                "sheet_name": sheet_name,
                "header_row": row_index,
                "columns": columns,
                "data_rows": non_empty_rows,
                "header_hint_count": header_hint_count,
                "question_hint_count": question_hint_count,
            }
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: (
            item["question_hint_count"],
            item["header_hint_count"],
            len(item["columns"]),
            item["data_rows"],
        ),
    )


def detect_questionnaire_sheets(file_path):
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".xlsx":
        workbook = pd.ExcelFile(file_path)
        detected_sheets = []

        for sheet_name in workbook.sheet_names:
            candidate = _find_best_header_for_sheet(
                file_path,
                sheet_name,
            )

            if candidate is None:
                continue

            detected_sheets.append(
                {
                    "sheet_name": candidate["sheet_name"],
                    "header_row": candidate["header_row"],
                    "columns": candidate["columns"],
                    "data_rows": candidate["data_rows"],
                    "likely_questionnaire": (
                        candidate["question_hint_count"] > 0
                    ),
                }
            )

        if not detected_sheets:
            raise ValueError(
                "Could not identify any usable worksheets."
            )

        return detected_sheets

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)

        columns = [
            str(column).strip()
            for column in df.columns
        ]

        normalized_columns = [
            column.lower()
            for column in columns
        ]

        return [
            {
                "sheet_name": "CSV",
                "header_row": 0,
                "columns": columns,
                "data_rows": len(df),
                "likely_questionnaire": any(
                    column in QUESTION_HINTS
                    for column in normalized_columns
                ),
            }
        ]

    raise ValueError("Unsupported questionnaire format")


def detect_questionnaire_structure(file_path):
    detected_sheets = detect_questionnaire_sheets(file_path)

    likely_sheets = [
        sheet
        for sheet in detected_sheets
        if sheet["likely_questionnaire"]
    ]

    candidates = (
        likely_sheets
        if likely_sheets
        else detected_sheets
    )

    return max(
        candidates,
        key=lambda item: item["data_rows"],
    )


def parse_questionnaire(file_path):
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".xlsx":
        workbook = pd.ExcelFile(file_path)
        candidates = []

        for sheet_name in workbook.sheet_names:
            raw_df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                header=None,
            )

            for row_index in range(min(25, len(raw_df))):
                row_values = [
                    str(value).strip().lower()
                    for value in raw_df.iloc[row_index].tolist()
                    if pd.notna(value)
                ]

                if "question" not in row_values:
                    continue

                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=row_index,
                )

                if "Question" not in df.columns:
                    continue

                question_count = df["Question"].notna().sum()

                candidates.append(
                    {
                        "sheet_name": sheet_name,
                        "header_row": row_index,
                        "dataframe": df,
                        "question_count": question_count,
                    }
                )

        if not candidates:
            raise ValueError(
                "Could not identify a questionnaire sheet containing a Question column."
            )

        best_candidate = max(
            candidates,
            key=lambda item: item["question_count"],
        )

        sheet_name = best_candidate["sheet_name"]
        row_index = best_candidate["header_row"]
        df = best_candidate["dataframe"]

        questions = []

        for index, row in df.iterrows():
            if pd.isna(row.get("Question")):
                continue

            question_id = row.get("Unique Identifier")

            if pd.isna(question_id):
                question_id = f"Q{index + 1:03d}"

            questions.append(
                {
                    "question_id": str(question_id),
                    "question_text": str(row.get("Question")).strip(),
                    "description": (
                        None
                        if pd.isna(row.get("Description"))
                        else str(row.get("Description")).strip()
                    ),
                    "vendor_answer": (
                        None
                        if pd.isna(row.get("Response"))
                        else str(row.get("Response")).strip()
                    ),
                    "source_sheet": sheet_name,
                    "source_row": index + row_index + 2,
                }
            )

        return questions

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)

        if "Question" not in df.columns:
            raise ValueError(
                "Could not identify a Question column in the CSV."
            )

        questions = []

        for index, row in df.iterrows():
            if pd.isna(row.get("Question")):
                continue

            question_id = row.get("Unique Identifier")

            if pd.isna(question_id):
                question_id = f"Q{index + 1:03d}"

            questions.append(
                {
                    "question_id": str(question_id),
                    "question_text": str(row.get("Question")).strip(),
                    "description": (
                        None
                        if pd.isna(row.get("Description"))
                        else str(row.get("Description")).strip()
                    ),
                    "vendor_answer": (
                        None
                        if pd.isna(row.get("Response"))
                        else str(row.get("Response")).strip()
                    ),
                    "source_sheet": "CSV",
                    "source_row": index + 2,
                }
            )

        return questions

    raise ValueError("Unsupported questionnaire format")


def parse_questionnaire_with_mapping(
    file_path,
    sheet_name,
    header_row,
    question_column,
    id_column=None,
    answer_column=None,
    description_column=None,
):
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".xlsx":
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=header_row,
        )

    elif file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)
        sheet_name = "CSV"
        header_row = 0

    else:
        raise ValueError("Unsupported questionnaire format")

    if question_column not in df.columns:
        raise ValueError(
            f"Selected question column '{question_column}' was not found."
        )

    questions = []

    for index, row in df.iterrows():
        question_value = row.get(question_column)

        if pd.isna(question_value):
            continue

        question_text = str(question_value).strip()

        if not question_text:
            continue

        question_id = None

        if id_column and id_column in df.columns:
            id_value = row.get(id_column)

            if pd.notna(id_value):
                question_id = str(id_value).strip()

        if not question_id:
            question_id = f"Q{len(questions) + 1:03d}"

        vendor_answer = None

        if answer_column and answer_column in df.columns:
            answer_value = row.get(answer_column)

            if pd.notna(answer_value):
                vendor_answer = str(answer_value).strip()

        description = None

        if description_column and description_column in df.columns:
            description_value = row.get(description_column)

            if pd.notna(description_value):
                description = str(description_value).strip()

        questions.append(
            {
                "question_id": question_id,
                "question_text": question_text,
                "description": description,
                "vendor_answer": vendor_answer,
                "source_sheet": sheet_name,
                "source_row": index + header_row + 2,
            }
        )

    return questions