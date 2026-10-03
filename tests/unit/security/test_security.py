
from src.security.models.contracts import CodeReviewRequest, SecurityScanRequest
from src.security.models.enums import ReviewStatus, SecurityStatus
from src.security.review.reviewer import CodeReviewer
from src.security.scanning.scanner import SecurityScanner


def test_security_scan_passes_clean_code():
    result = SecurityScanner().scan(
        SecurityScanRequest(
            files={"app.py": "print('hello')"}
        )
    )

    assert result.status == SecurityStatus.PASSED
    assert result.findings == []


def test_security_scan_detects_secret():
    result = SecurityScanner().scan(
        SecurityScanRequest(
            files={"config.py": 'api_key = "super-secret-value"'}
        )
    )

    assert result.status == SecurityStatus.FAILED
    assert result.findings[0].severity.value == "critical"


def test_security_scan_detects_dangerous_command():
    result = SecurityScanner().scan(
        SecurityScanRequest(
            files={"app.py": "import os\nos.system('rm -rf /')"}
        )
    )

    assert result.status == SecurityStatus.FAILED


def test_code_review_requests_changes_for_high_risk_finding():
    result = CodeReviewer().review(
        CodeReviewRequest(
            files={"app.py": "import os\nos.system('danger')"}
        )
    )

    assert result.status == ReviewStatus.CHANGES_REQUESTED


def test_code_review_approves_clean_code():
    result = CodeReviewer().review(
        CodeReviewRequest(
            files={"app.py": "print('safe')"},
            summary="Clean implementation",
        )
    )

    assert result.status == ReviewStatus.APPROVED
