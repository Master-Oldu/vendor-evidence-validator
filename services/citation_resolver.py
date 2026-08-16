def normalize_evidence_display_name(file_name):
    """
    Return a cleaner display-only evidence filename.

    This does not modify the original filename or backend
    provenance. It is used only for user-facing labels.
    """

    if file_name is None:
        return ""

    display_name = str(file_name).strip()

    known_extensions = (
        ".pdf",
        ".docx",
        ".xlsx",
        ".csv",
        ".txt",
    )

    lower_name = display_name.lower()

    for extension in known_extensions:
        if lower_name.endswith(extension):
            display_name = display_name[
                :-len(extension)
            ]
            break

    display_name = display_name.replace(
        "_",
        " ",
    )

    display_name = " ".join(
        display_name.split()
    )

    return display_name


def _same_display_text(first, second):
    if not first or not second:
        return False

    normalize = lambda value: " ".join(
        str(value).lower().split()
    )

    return normalize(first) == normalize(second)


def build_citation_label(evidence_item):
    file_name = evidence_item["file_name"]

    display_name = (
        normalize_evidence_display_name(
            file_name
        )
    )

    file_type = evidence_item.get(
        "file_type",
        "",
    )

    provenance = evidence_item.get(
        "provenance",
        {},
    )

    parts = [display_name]

    # PDF
    if file_type == ".pdf":
        pdf_page_number = provenance.get(
            "pdf_page_number"
        )

        reference_identifier = provenance.get(
            "reference_identifier"
        )

        section_heading = provenance.get(
            "section_heading"
        )

        if pdf_page_number is not None:
            parts.append(
                f"Page {pdf_page_number}"
            )

        if reference_identifier:
            parts.append(
                reference_identifier
            )

        elif (
            section_heading
            and not _same_display_text(
                section_heading,
                display_name,
            )
        ):
            parts.append(
                section_heading
            )

    # DOCX
    elif file_type == ".docx":
        heading = provenance.get(
            "heading"
        )

        block_number = provenance.get(
            "block_number"
        )

        block_type = provenance.get(
            "block_type"
        )

        table_number = provenance.get(
            "table_number"
        )

        row_number = provenance.get(
            "row_number"
        )

        if heading:
            parts.append(
                heading
            )

        if block_number is not None:
            parts.append(
                f"Block {block_number}"
            )

        if (
            block_type == "table_row"
            and table_number is not None
        ):
            parts.append(
                f"Table {table_number}"
            )

        if (
            block_type == "table_row"
            and row_number is not None
        ):
            parts.append(
                f"Row {row_number}"
            )

    # XLSX
    elif file_type == ".xlsx":
        sheet_name = provenance.get(
            "sheet_name"
        )

        row_number = provenance.get(
            "row_number"
        )

        cell_range = provenance.get(
            "cell_range"
        )

        if sheet_name:
            parts.append(
                f"Sheet: {sheet_name}"
            )

        if row_number is not None:
            parts.append(
                f"Row {row_number}"
            )

        if cell_range:
            parts.append(
                f"Cells {cell_range}"
            )

    # CSV
    elif file_type == ".csv":
        row_number = provenance.get(
            "row_number"
        )

        if row_number is not None:
            parts.append(
                f"Row {row_number}"
            )

    # TXT
    elif file_type == ".txt":
        start_line = provenance.get(
            "start_line"
        )

        end_line = provenance.get(
            "end_line"
        )

        if (
            start_line is not None
            and end_line is not None
        ):
            if start_line == end_line:
                parts.append(
                    f"Line {start_line}"
                )
            else:
                parts.append(
                    f"Lines {start_line}-{end_line}"
                )

    return " | ".join(parts)


def resolve_source_references(
    validation_result,
    retrieved_evidence,
):
    """
    Resolve AI-selected source IDs back to
    backend-owned evidence metadata.

    The AI may select source IDs.

    Filenames, page numbers, headings,
    sheets, rows, cells, line numbers,
    and evidence excerpts come only from
    backend evidence records.
    """

    evidence_by_source_id = {
        item["source_id"]: item
        for item in retrieved_evidence
    }

    resolved_sources = []

    for source_id in validation_result.get(
        "source_references",
        [],
    ):
        evidence_item = (
            evidence_by_source_id.get(
                source_id
            )
        )

        if evidence_item is None:
            raise ValueError(
                "Could not resolve cited source ID: "
                f"{source_id}"
            )

        resolved_sources.append(
            {
                "source_id": source_id,
                "evidence_id": evidence_item[
                    "evidence_id"
                ],
                "file_name": evidence_item[
                    "file_name"
                ],
                "display_name": (
                    normalize_evidence_display_name(
                        evidence_item[
                            "file_name"
                        ]
                    )
                ),
                "file_type": evidence_item[
                    "file_type"
                ],
                "provenance": evidence_item[
                    "provenance"
                ],
                "citation_label": (
                    build_citation_label(
                        evidence_item
                    )
                ),
                "evidence_excerpt": evidence_item[
                    "text"
                ],
            }
        )

    return resolved_sources