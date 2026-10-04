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
            SecurityScanRequest(
                project_id=request.project_id,
                task_id=request.task_id,
                working_directory=request.working_directory,
                files=request.files,
                diff=request.diff,
            )
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
                approved=False,
                status=ReviewStatus.CHANGES_REQUESTED,
                findings=scan.findings,
                summary="Security findings require changes before approval",
            )

        return CodeReviewResult(
            approved=True,
            status=ReviewStatus.APPROVED,
            findings=scan.findings,
            summary=request.summary or "Review passed",
        )
