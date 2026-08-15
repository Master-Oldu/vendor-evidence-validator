import unittest

from services.evidence_validator import validate_question


SOURCE_ID = "E-001-P001-C01"


RETRIEVED_EVIDENCE = [
    {
        "source_id": SOURCE_ID,
        "evidence_id": "E-001",
        "file_name": "sample-policy.pdf",
        "file_type": ".pdf",
        "provenance": {
            "pdf_page_number": 1,
            "section_heading": "Access Control",
        },
        "text": (
            "Multifactor authentication is required "
            "for all privileged administrative access."
        ),
        "hybrid_score": 0.95,
    }
]


QUESTION = {
    "question_text": (
        "Is multifactor authentication required "
        "for privileged administrative access?"
    ),
    "description": None,
    "vendor_answer": None,
}


class FakeProvider:
    def __init__(self, response):
        self.response = response

    def generate_json(
        self,
        system_prompt,
        user_prompt,
        response_schema=None,
    ):
        return self.response


class ValidationGoldenTests(unittest.TestCase):

    def test_validated_result(self):
        provider = FakeProvider(
            {
                "status": "validated",
                "evidence_strength": "strong",
                "confidence": "high",
                "explanation": (
                    "The evidence directly states that "
                    "multifactor authentication is required "
                    "for privileged administrative access."
                ),
                "evidence_proves": [
                    (
                        "MFA is required for privileged "
                        "administrative access."
                    )
                ],
                "evidence_does_not_prove": [],
                "gaps": [],
                "contradictions": [],
                "additional_evidence_needed": [],
                "reviewer_action": (
                    "Accept the control as validated."
                ),
                "human_review_required": True,
                "source_references": [
                    SOURCE_ID
                ],
            }
        )

        result = validate_question(
            question=QUESTION,
            retrieved_evidence=RETRIEVED_EVIDENCE,
            ai_provider=provider,
        )

        self.assertEqual(
            result["status"],
            "validated",
        )

        self.assertEqual(
            result["evidence_strength"],
            "strong",
        )

        self.assertEqual(
            result["confidence"],
            "high",
        )

        self.assertEqual(
            result["source_references"],
            [SOURCE_ID],
        )

        self.assertTrue(
            result["evidence_proves"]
        )

        self.assertFalse(
            result["gaps"]
        )

        self.assertFalse(
            result["contradictions"]
        )


    def test_partially_validated_result(self):
        provider = FakeProvider(
            {
                "status": "partially_validated",
                "evidence_strength": "moderate",
                "confidence": "high",
                "explanation": (
                    "The evidence supports MFA for "
                    "privileged administrative access, "
                    "but does not demonstrate broader "
                    "MFA coverage."
                ),
                "evidence_proves": [
                    (
                        "MFA is required for privileged "
                        "administrative access."
                    )
                ],
                "evidence_does_not_prove": [
                    (
                        "The evidence does not establish "
                        "MFA requirements for all users."
                    )
                ],
                "gaps": [
                    (
                        "Broader MFA scope remains "
                        "unsupported."
                    )
                ],
                "contradictions": [],
                "additional_evidence_needed": [
                    (
                        "Evidence showing MFA requirements "
                        "for the remaining applicable users."
                    )
                ],
                "reviewer_action": (
                    "Request evidence covering the "
                    "remaining MFA scope."
                ),
                "human_review_required": True,
                "source_references": [
                    SOURCE_ID
                ],
            }
        )

        result = validate_question(
            question=QUESTION,
            retrieved_evidence=RETRIEVED_EVIDENCE,
            ai_provider=provider,
        )

        self.assertEqual(
            result["status"],
            "partially_validated",
        )

        self.assertTrue(
            result["evidence_proves"]
        )

        self.assertTrue(
            result["gaps"]
        )

        self.assertEqual(
            result["source_references"],
            [SOURCE_ID],
        )


    def test_contradicted_result(self):
        provider = FakeProvider(
            {
                "status": "contradicted",
                "evidence_strength": "strong",
                "confidence": "high",
                "explanation": (
                    "The submitted evidence affirmatively "
                    "conflicts with the claimed control."
                ),
                "evidence_proves": [],
                "evidence_does_not_prove": [],
                "gaps": [],
                "contradictions": [
                    (
                        "The evidence states that MFA is "
                        "not required for privileged access."
                    )
                ],
                "additional_evidence_needed": [
                    (
                        "Clarification and updated evidence "
                        "showing the actual MFA requirement."
                    )
                ],
                "reviewer_action": (
                    "Escalate the contradiction for review."
                ),
                "human_review_required": True,
                "source_references": [
                    SOURCE_ID
                ],
            }
        )

        result = validate_question(
            question=QUESTION,
            retrieved_evidence=RETRIEVED_EVIDENCE,
            ai_provider=provider,
        )

        self.assertEqual(
            result["status"],
            "contradicted",
        )

        self.assertTrue(
            result["contradictions"]
        )

        self.assertEqual(
            result["source_references"],
            [SOURCE_ID],
        )


    def test_not_validated_normalizes_to_insufficient_evidence(
        self,
    ):
        provider = FakeProvider(
            {
                "status": "not_validated",
                "evidence_strength": "weak",
                "confidence": "low",
                "explanation": (
                    "The retrieved material does not "
                    "provide a usable basis for validating "
                    "the requested control."
                ),
                "evidence_proves": [],
                "evidence_does_not_prove": [
                    (
                        "The evidence does not establish "
                        "the requested MFA control."
                    )
                ],
                "gaps": [
                    (
                        "No usable supporting evidence "
                        "was identified."
                    )
                ],
                "contradictions": [],
                "additional_evidence_needed": [
                    (
                        "Evidence demonstrating the "
                        "applicable MFA requirement."
                    )
                ],
                "reviewer_action": (
                    "Request additional evidence."
                ),
                "human_review_required": True,
                "source_references": [],
            }
        )

        result = validate_question(
            question=QUESTION,
            retrieved_evidence=RETRIEVED_EVIDENCE,
            ai_provider=provider,
        )

        self.assertEqual(
            result["status"],
            "insufficient_evidence",
        )

        self.assertFalse(
            result["evidence_proves"]
        )

        self.assertFalse(
            result["contradictions"]
        )

        self.assertFalse(
            result["source_references"]
        )


    def test_validated_without_source_reference_is_rejected(
        self,
    ):
        provider = FakeProvider(
            {
                "status": "validated",
                "evidence_strength": "strong",
                "confidence": "high",
                "explanation": (
                    "The evidence directly supports "
                    "the requested control."
                ),
                "evidence_proves": [
                    (
                        "MFA is required for privileged "
                        "administrative access."
                    )
                ],
                "evidence_does_not_prove": [],
                "gaps": [],
                "contradictions": [],
                "additional_evidence_needed": [],
                "reviewer_action": (
                    "Accept the control as validated."
                ),
                "human_review_required": True,
                "source_references": [],
            }
        )

        with self.assertRaises(ValueError):
            validate_question(
                question=QUESTION,
                retrieved_evidence=RETRIEVED_EVIDENCE,
                ai_provider=provider,
            )


    def test_contradicted_without_contradiction_is_rejected(
        self,
    ):
        provider = FakeProvider(
            {
                "status": "contradicted",
                "evidence_strength": "strong",
                "confidence": "high",
                "explanation": (
                    "The result claims a contradiction "
                    "but does not identify one."
                ),
                "evidence_proves": [],
                "evidence_does_not_prove": [],
                "gaps": [],
                "contradictions": [],
                "additional_evidence_needed": [],
                "reviewer_action": (
                    "Review the result."
                ),
                "human_review_required": True,
                "source_references": [
                    SOURCE_ID
                ],
            }
        )

        with self.assertRaises(ValueError):
            validate_question(
                question=QUESTION,
                retrieved_evidence=RETRIEVED_EVIDENCE,
                ai_provider=provider,
            )


    def test_unknown_source_reference_is_rejected(
        self,
    ):
        provider = FakeProvider(
            {
                "status": "validated",
                "evidence_strength": "strong",
                "confidence": "high",
                "explanation": (
                    "The evidence directly supports "
                    "the requested control."
                ),
                "evidence_proves": [
                    (
                        "MFA is required for privileged "
                        "administrative access."
                    )
                ],
                "evidence_does_not_prove": [],
                "gaps": [],
                "contradictions": [],
                "additional_evidence_needed": [],
                "reviewer_action": (
                    "Accept the control as validated."
                ),
                "human_review_required": True,
                "source_references": [
                    "E-999-P999-C99"
                ],
            }
        )

        with self.assertRaises(ValueError):
            validate_question(
                question=QUESTION,
                retrieved_evidence=RETRIEVED_EVIDENCE,
                ai_provider=provider,
            )


if __name__ == "__main__":
    unittest.main()