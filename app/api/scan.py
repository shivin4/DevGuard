from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.engines.secrets import SecretScanner
from app.llm import get_llm_client
from app.models.domain import Finding
from app.models.schemas import FindingSchema, ScanRequest, ScanResponse

router = APIRouter(prefix="/api/v1/scan", tags=["Secret Scanner"])


@router.post("", response_model=ScanResponse)
async def run_secret_scan(
    payload: ScanRequest,
    db: Session = Depends(get_db),
):
    """Scan a target directory path for exposed secret keys and tokens."""
    llm_client = get_llm_client()
    scanner = SecretScanner(llm_client=llm_client)

    try:
        raw_findings = await scanner.scan_directory(
            directory_path=payload.path,
            use_llm_triage=payload.use_llm_triage,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to scan path '{payload.path}': {e}")

    saved_findings = []
    real_count = 0

    for rf in raw_findings:
        db_finding = Finding(
            file_path=rf.file_path,
            line_number=rf.line_number,
            rule_name=rf.rule_name,
            masked_value=rf.masked_value,
            entropy_score=rf.entropy_score,
            is_real_secret=rf.is_real_secret,
            is_false_positive=False,
            reasoning=rf.reasoning,
        )
        db.add(db_finding)
        db.flush()
        saved_findings.append(FindingSchema.model_validate(db_finding))
        if rf.is_real_secret:
            real_count += 1

    db.commit()

    return ScanResponse(
        total_findings=len(saved_findings),
        real_secrets_count=real_count,
        findings=saved_findings,
    )
