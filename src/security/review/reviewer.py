from src.security.models.contracts import (
    CodeReviewRequest,
    CodeReviewResult,
    SecurityScanRequest,
)
from src.security.models.enums import ReviewStatus, SecuritySeverity
from src.security.scanning.scanner import SecurityScanner


class CodeReviewer:
    def __init__(self, scanner: SecurityScanner | None = None) -> None:
        self.scanner = scanner or SecurityScanner()

    def review(self, request: CodeReviewRequest) -> CodeReviewResult:
        scan = self.scanner.scan(
            SecurityScanRequest(files=request.files)
        )

        blocking = [
            finding
            for finding in scan.findings
            if finding.severity
            in {
                SecuritySeverity.HIGH,
                SecuritySeverity.CRITICAL,
            }
        ]

        if blocking:
            return CodeReviewResult(
                status=ReviewStatus.CHANGES_REQUESTED,
                findings=scan.findings,
                summary="Security findings require changes before approval",
            )

        return CodeReviewResult(
            status=ReviewStatus.APPROVED,
            findings=scan.findings,
            summary=request.summary or "Review passed",
        )
