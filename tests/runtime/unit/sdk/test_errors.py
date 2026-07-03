from crime_research_kit.sdk.errors import (
    DEPENDENCY_MISSING,
    INVALID_INPUT,
    PRIVACY_BLOCKED,
    CrkDependencyError,
    CrkError,
    CrkErrorCode,
    CrkInputError,
    CrkPrivacyError,
)


def test_crk_error_carries_code_and_operation_context():
    error = CrkError(
        "case_not_found",
        "Unknown case",
        operation="case.info",
        case_ref="demo_case",
        details={"slug": "demo_case"},
    )

    assert error.code == "case_not_found"
    assert error.message == "Unknown case"
    assert error.operation == "case.info"
    assert error.case_ref == "demo_case"
    assert error.to_dict() == {
        "code": "case_not_found",
        "message": "Unknown case",
        "operation": "case.info",
        "case_ref": "demo_case",
        "details": {"slug": "demo_case"},
    }


def test_crk_error_accepts_message_with_keyword_code():
    error = CrkError("Bad payload", code=CrkErrorCode.INVALID_INPUT)

    assert error.code == INVALID_INPUT
    assert error.message == "Bad payload"


def test_error_subclasses_provide_stable_codes():
    assert CrkInputError("Bad input").code == INVALID_INPUT
    assert CrkPrivacyError("Private data").code == PRIVACY_BLOCKED
    assert CrkDependencyError("Missing package").code == DEPENDENCY_MISSING
