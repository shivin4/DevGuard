from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.engines.errors import ErrorExplainer
from app.llm import get_llm_client
from app.models.domain import ErrorExplanation
from app.models.schemas import ErrorExplanationSchema, ExplainRequest, ExplainResponse

router = APIRouter(prefix="/api/v1/explain", tags=["Error Explainer"])


@router.post("", response_model=ExplainResponse)
async def explain_error_traceback(
    payload: ExplainRequest,
    db: Session = Depends(get_db),
):
    """Analyze a Python exception traceback and return LLM root cause & fix."""
    if not payload.traceback_text.strip():
        raise HTTPException(status_code=400, detail="traceback_text cannot be empty.")

    llm_client = get_llm_client()
    explainer = ErrorExplainer(llm_client=llm_client)

    try:
        res = await explainer.explain_error(
            traceback_text=payload.traceback_text,
            provided_source_code=payload.source_code,
            file_path_override=payload.file_path,
            line_number_override=payload.line_number,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to explain traceback: {e}")

    db_obj = ErrorExplanation(
        exception_type=res.exception_type,
        summary=res.summary,
        root_cause=res.root_cause,
        suggested_fix=res.suggested_fix,
        file_path=payload.file_path,
        line_number=payload.line_number,
        fixed_code_snippet=res.fixed_code_snippet,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    return ExplainResponse(explanation=ErrorExplanationSchema.model_validate(db_obj))
