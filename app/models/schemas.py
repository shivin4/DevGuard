from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class FindingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: Optional[int] = None
    file_path: str
    line_number: int
    rule_name: str
    masked_value: str
    entropy_score: float
    is_real_secret: bool
    is_false_positive: bool
    reasoning: Optional[str] = None
    created_at: datetime


class WorkflowAnalysisSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: Optional[int] = None
    workflow_name: str
    job_name: str
    pr_number: Optional[int] = None
    failure_category: str
    root_cause: str
    suggested_fix: str
    confidence: float
    created_at: datetime


class ErrorExplanationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exception_type: str
    summary: str
    root_cause: str
    suggested_fix: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    fixed_code_snippet: Optional[str] = None
    created_at: datetime



class ScanRequest(BaseModel):
    path: str = "."
    use_llm_triage: bool = True


class ScanResponse(BaseModel):
    total_findings: int
    real_secrets_count: int
    findings: List[FindingSchema]


class ExplainRequest(BaseModel):
    traceback_text: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    source_code: Optional[str] = None


class ExplainResponse(BaseModel):
    explanation: ErrorExplanationSchema
