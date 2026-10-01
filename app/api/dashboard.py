from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.engines.errors import ErrorExplainer
from app.engines.secrets import SecretScanner
from app.llm import get_llm_client
from app.models.domain import ErrorExplanation, Finding, WorkflowAnalysis

router = APIRouter(tags=["Web Dashboard"])
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, db: Session = Depends(get_db)):
    """Render main web dashboard overview."""
    findings = db.query(Finding).order_by(Finding.id.desc()).all()
    ci_analyses = db.query(WorkflowAnalysis).order_by(WorkflowAnalysis.id.desc()).all()
    error_count = db.query(ErrorExplanation).count()

    real_secrets_count = sum(1 for f in findings if f.is_real_secret and not f.is_false_positive)
    false_positives_count = sum(1 for f in findings if f.is_false_positive)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "findings": findings,
            "ci_analyses": ci_analyses,
            "real_secrets_count": real_secrets_count,
            "false_positives_count": false_positives_count,
            "error_count": error_count,
            "ci_count": len(ci_analyses),
        },
    )


@router.post("/dashboard/scan", response_class=HTMLResponse)
async def dashboard_scan(
    request: Request,
    path: str = Form("."),
    db: Session = Depends(get_db),
):
    """HTMX endpoint for running interactive secret scan."""
    llm_client = get_llm_client()
    scanner = SecretScanner(llm_client=llm_client)

    try:
        raw_findings = await scanner.scan_directory(directory_path=path, use_llm_triage=True)
    except Exception as e:
        return HTMLResponse(f"<tr><td colspan='6' style='color: var(--accent-red);'>Scan Error: {e}</td></tr>")

    new_findings = []
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
        new_findings.append(db_finding)

    db.commit()

    all_findings = db.query(Finding).order_by(Finding.id.desc()).all()
    html_out = ""
    for f in all_findings:
        html_out += templates.TemplateResponse(
            request=request,
            name="partials/finding_row.html",
            context={"finding": f},
        ).body.decode("utf-8")

    return HTMLResponse(content=html_out or "<tr><td colspan='6'>No findings detected.</td></tr>")


@router.post("/dashboard/findings/{finding_id}/toggle-false-positive", response_class=HTMLResponse)
async def toggle_false_positive(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """HTMX endpoint for toggling false positive status on a finding."""
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    finding.is_false_positive = not finding.is_false_positive
    db.commit()
    db.refresh(finding)

    return templates.TemplateResponse(
        request=request,
        name="partials/finding_row.html",
        context={"finding": finding},
    )


@router.post("/dashboard/explain", response_class=HTMLResponse)
async def dashboard_explain_error(
    request: Request,
    traceback_text: str = Form(...),
    db: Session = Depends(get_db),
):
    """HTMX endpoint for diagnosing an error traceback in the UI."""
    if not traceback_text.strip():
        return HTMLResponse(
            "<div style='color: var(--accent-red); font-size: 0.9rem;'>Please paste a valid traceback.</div>"
        )

    llm_client = get_llm_client()
    explainer = ErrorExplainer(llm_client=llm_client)

    try:
        res = await explainer.explain_error(traceback_text=traceback_text)
    except Exception as e:
        return HTMLResponse(f"<div style='color: var(--accent-red);'>Error explaining traceback: {e}</div>")

    db_obj = ErrorExplanation(
        exception_type=res.exception_type,
        summary=res.summary,
        root_cause=res.root_cause,
        suggested_fix=res.suggested_fix,
        fixed_code_snippet=res.fixed_code_snippet,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    return templates.TemplateResponse(
        request=request,
        name="partials/error_result.html",
        context={"explanation": db_obj},
    )
