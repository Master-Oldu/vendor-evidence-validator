import json


VALIDATION_STATUSES = {
    "validated",
    "partially_validated",
    "not_validated",
    "contradicted",
    "insufficient_evidence",
}

EVIDENCE_STRENGTH_LEVELS = {
    "weak",
    "moderate",
    "strong",
}

CONFIDENCE_LEVELS = {
    "low",
    "medium",
    "high",
}

REQUIRED_RESULT_FIELDS = {
    "status",
    "evidence_strength",
    "confidence",
    "explanation",
    "evidence_proves",
    "evidence_does_not_prove",
    "gaps",
    "contradictions",
    "additional_evidence_needed",
    "reviewer_action",
    "human_review_required",
    "source_references",
}

LIST_RESULT_FIELDS = {
    "evidence_proves",
    "evidence_does_not_prove",
    "gaps",
    "contradictions",
    "additional_evidence_needed",
    "source_references",
}


VALIDATION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": [
                "validated",
                "partially_validated",
                "not_validated",
                "contradicted",
                "insufficient_evidence",
            ],
        },
        "evidence_strength": {
            "type": "string",
            "enum": [
                "weak",
                "moderate",
                "strong",
            ],
        },
        "confidence": {
            "type": "string",
            "enum": [
                "low",
                "medium",
                "high",
            ],
        },
        "explanation": {
            "type": "string",
        },
        "evidence_proves": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "evidence_does_not_prove": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "gaps": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "contradictions": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "additional_evidence_needed": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "reviewer_action": {
            "type": "string",
        },
        "human_review_required": {
            "type": "boolean",
        },
        "source_references": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "status",
        "evidence_strength",
        "confidence",
        "explanation",
        "evidence_proves",
        "evidence_does_not_prove",
        "gaps",
        "contradictions",
        "additional_evidence_needed",
        "reviewer_action",
        "human_review_required",
        "source_references",
    ],
    "additionalProperties": False,
}


def create_validation_result(
    status,
    evidence_strength,
    confidence,
    explanation,
    evidence_proves=None,
    evidence_does_not_prove=None,
    gaps=None,
    contradictions=None,
    additional_evidence_needed=None,
    reviewer_action=None,
    human_review_required=True,
    source_references=None,
):
    if status not in VALIDATION_STATUSES:
        raise ValueError(
            f"Invalid validation status: {status}"
        )

    if (
        evidence_strength
        not in EVIDENCE_STRENGTH_LEVELS
    ):
        raise ValueError(
            "Invalid evidence strength: "
            f"{evidence_strength}"
        )

    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError(
            f"Invalid confidence level: {confidence}"
        )

    return {
        "status": status,
        "evidence_strength": evidence_strength,
        "confidence": confidence,
        "explanation": explanation,
        "evidence_proves": evidence_proves or [],
        "evidence_does_not_prove": (
            evidence_does_not_prove or []
        ),
        "gaps": gaps or [],
        "contradictions": contradictions or [],
        "additional_evidence_needed": (
            additional_evidence_needed or []
        ),
        "reviewer_action": reviewer_action,
        "human_review_required": (
            human_review_required
        ),
        "source_references": (
            source_references or []
        ),
    }


def validate_source_references(
    validation_result,
    retrieved_evidence,
):
    allowed_source_ids = {
        item["source_id"]
        for item in retrieved_evidence
    }

    cited_source_ids = set(
        validation_result.get(
            "source_references",
            [],
        )
    )

    invalid_source_ids = (
        cited_source_ids
        - allowed_source_ids
    )

    if invalid_source_ids:
        raise ValueError(
            "Validation result cited source IDs "
            "that were not provided to the validator: "
            f"{sorted(invalid_source_ids)}"
        )

    return True


def validate_result_structure(
    validation_result,
):
    if not isinstance(
        validation_result,
        dict,
    ):
        raise ValueError(
            "Validation result must be a dictionary."
        )

    missing_fields = (
        REQUIRED_RESULT_FIELDS
        - set(validation_result)
    )

    if missing_fields:
        raise ValueError(
            "Validation result is missing fields: "
            f"{sorted(missing_fields)}"
        )

    extra_fields = (
        set(validation_result)
        - REQUIRED_RESULT_FIELDS
    )

    if extra_fields:
        raise ValueError(
            "Validation result contains unexpected fields: "
            f"{sorted(extra_fields)}"
        )

    if (
        validation_result["status"]
        not in VALIDATION_STATUSES
    ):
        raise ValueError(
            "Invalid validation status: "
            f"{validation_result['status']}"
        )

    if (
        validation_result["evidence_strength"]
        not in EVIDENCE_STRENGTH_LEVELS
    ):
        raise ValueError(
            "Invalid evidence strength: "
            f"{validation_result['evidence_strength']}"
        )

    if (
        validation_result["confidence"]
        not in CONFIDENCE_LEVELS
    ):
        raise ValueError(
            "Invalid confidence level: "
            f"{validation_result['confidence']}"
        )

    for field in LIST_RESULT_FIELDS:
        if not isinstance(
            validation_result[field],
            list,
        ):
            raise ValueError(
                f"{field} must be a list."
            )

    if not isinstance(
        validation_result[
            "human_review_required"
        ],
        bool,
    ):
        raise ValueError(
            "human_review_required must be a boolean."
        )

    return True


def normalize_validation_result(
    validation_result,
):
    """
    Correct narrow taxonomy inconsistencies
    without changing the model's substantive
    evidence analysis.
    """

    normalized_result = dict(
        validation_result
    )

    status = normalized_result.get(
        "status"
    )

    evidence_proves = normalized_result.get(
        "evidence_proves",
        [],
    )

    contradictions = normalized_result.get(
        "contradictions",
        [],
    )

    source_references = normalized_result.get(
        "source_references",
        [],
    )

    if (
        status == "not_validated"
        and not evidence_proves
        and not contradictions
        and not source_references
    ):
        normalized_result[
            "status"
        ] = "insufficient_evidence"

    return normalized_result


def validate_result_consistency(
    validation_result,
):
    status = validation_result["status"]

    evidence_proves = (
        validation_result[
            "evidence_proves"
        ]
    )

    gaps = validation_result["gaps"]

    contradictions = (
        validation_result["contradictions"]
    )

    evidence_does_not_prove = (
        validation_result[
            "evidence_does_not_prove"
        ]
    )

    additional_evidence_needed = (
        validation_result[
            "additional_evidence_needed"
        ]
    )

    source_references = (
        validation_result[
            "source_references"
        ]
    )

    if status == "validated":
        problems = []

        if not evidence_proves:
            problems.append(
                "no evidence was identified as "
                "proving the requirement"
            )

        if not source_references:
            problems.append(
                "no supporting source references "
                "were cited"
            )

        if gaps:
            problems.append(
                "material gaps were reported"
            )

        if contradictions:
            problems.append(
                "contradictions were reported"
            )

        if evidence_does_not_prove:
            problems.append(
                "required elements were reported "
                "as not proven"
            )

        if additional_evidence_needed:
            problems.append(
                "additional evidence was reported "
                "as necessary"
            )

        if problems:
            raise ValueError(
                "A result cannot be 'validated' "
                "while also reporting: "
                + "; ".join(problems)
            )

    if status == "partially_validated":
        if not evidence_proves:
            raise ValueError(
                "A partially_validated result must "
                "identify at least one meaningful "
                "part of the requirement that the "
                "evidence proves."
            )

        if not source_references:
            raise ValueError(
                "A partially_validated result must "
                "cite at least one supporting "
                "source reference."
            )

        if (
            not gaps
            and not evidence_does_not_prove
        ):
            raise ValueError(
                "A partially_validated result must "
                "identify at least one gap or item "
                "that the evidence does not prove."
            )

    if status == "contradicted":
        if not contradictions:
            raise ValueError(
                "A contradicted result must identify "
                "at least one contradiction."
            )

        if not source_references:
            raise ValueError(
                "A contradicted result must cite "
                "at least one source supporting "
                "the contradiction."
            )

    return True


def validate_ai_result(
    validation_result,
    retrieved_evidence,
):
    validate_result_structure(
        validation_result
    )

    validate_result_consistency(
        validation_result
    )

    validate_source_references(
        validation_result,
        retrieved_evidence,
    )

    return True


def build_validation_prompt(
    question,
    retrieved_evidence,
):
    evidence_items = []

    for item in retrieved_evidence:
        evidence_items.append(
            {
                "source_id": item["source_id"],
                "file_name": item["file_name"],
                "file_type": item["file_type"],
                "provenance": item[
                    "provenance"
                ],
                "text": item["text"],
            }
        )

    input_data = {
        "question": {
            "question_id": question.get(
                "question_id"
            ),
            "question_text": question.get(
                "question_text"
            ),
            "description": question.get(
                "description"
            ),
            "vendor_answer": question.get(
                "vendor_answer"
            ),
        },
        "retrieved_evidence": evidence_items,
    }

    system_prompt = """
You are validating third-party risk questionnaire controls against submitted evidence.

Your job is to determine what the supplied evidence actually demonstrates.

The vendor answer is optional context. It is a claim, not proof.

Use only evidence provided in this prompt.

Evaluate the full questionnaire requirement, including:
- scope
- population
- systems
- frequency
- timing
- exceptions
- control operation
- evidence freshness when relevant
- contradictions between the question, vendor answer, and evidence

Do not assume that a related control proves the exact requirement.

Do not treat a policy statement as proof of implementation when the question requires evidence that the control operated.

Do not treat evidence covering only part of the required scope as full validation.

Choose the status based on how much of the actual requirement is demonstrated.

Status rules:

validated:
Use only when the supplied evidence reasonably demonstrates the complete requirement.
No meaningful requirement may remain unsupported.
A validated result must cite at least one supplied source that directly supports the validation.

partially_validated:
Use when the evidence clearly demonstrates at least one meaningful part of the actual requirement, but another meaningful part remains unsupported.

Examples include:
- the required control is demonstrated for only part of the required population
- the control is demonstrated for critical systems but the question requires all systems
- the control exists, but required frequency or timing is not demonstrated
- policy requirements support the control, but operational evidence needed by the question is missing

If meaningful partial proof exists together with a material gap, prefer partially_validated over not_validated.

A partially_validated result must identify what was proven and cite at least one supplied source that directly supports that partial proof.

not_validated:
Use when relevant evidence was supplied, but it does not actually demonstrate a meaningful portion of the required control.

Do not use not_validated merely because the evidence fails to demonstrate the entire requirement. If it demonstrates a meaningful portion of the requirement, use partially_validated.

contradicted:
Use only when supplied evidence affirmatively conflicts with the claimed control or requirement.

A contradiction requires evidence supporting an opposite or incompatible fact.

Examples:
- the vendor claims MFA is mandatory, but evidence states MFA is optional for the relevant systems
- the vendor claims reviews occur quarterly, but evidence states they occur annually
- the vendor claims data is not retained, but evidence states it is retained for seven years

A narrower scope, missing evidence, ambiguity, or failure to prove something is not by itself a contradiction.

A contradicted result must cite at least one supplied source that directly supports the contradiction.

insufficient_evidence:
Use when the supplied evidence is absent, too weak, too ambiguous, or insufficiently relevant to determine whether the requirement is met.

Important distinction:

Evidence proving part of requirement + material gap
= partially_validated

Relevant evidence but no meaningful portion of requirement demonstrated
= not_validated

No usable basis to determine the control
= insufficient_evidence

Affirmative evidence of an incompatible or opposite fact
= contradicted

A validated result must not contain:
- material gaps
- contradictions
- required elements listed as not proven
- additional evidence still needed

Do not invent:
- evidence
- filenames
- page numbers
- sections
- control numbers
- dates
- source IDs
- facts not contained in the supplied evidence

Cite only source_id values supplied in retrieved_evidence.

source_references should contain only sources that directly support the assessment.

If none of the supplied evidence directly supports the assessment, return an empty source_references list.

Be precise about what the evidence proves and what it does not prove.
""".strip()

    user_prompt = (
        "Validate the following questionnaire "
        "requirement against the retrieved evidence.\n\n"
        + json.dumps(
            input_data,
            indent=2,
            ensure_ascii=False,
        )
    )

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }


def validate_question(
    question,
    retrieved_evidence,
    ai_provider,
):
    prompts = build_validation_prompt(
        question,
        retrieved_evidence,
    )

    validation_result = (
        ai_provider.generate_json(
            system_prompt=prompts[
                "system_prompt"
            ],
            user_prompt=prompts[
                "user_prompt"
            ],
            response_schema=(
                VALIDATION_RESPONSE_SCHEMA
            ),
        )
    )

    validation_result = (
        normalize_validation_result(
            validation_result
        )
    )

    validate_ai_result(
        validation_result,
        retrieved_evidence,
    )

    return validation_result