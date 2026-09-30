from typing import Literal, Optional
from pydantic import BaseModel, Field


class SecretTriageResult(BaseModel):
    """LLM classification for secret scanner findings."""

    is_real_secret: bool = Field(
        ..., description="True if the masked string looks like an active/real secret, False if decoy or placeholder"
    )
    confidence: float = Field(
        ..., description="Confidence score between 0.0 and 1.0"
    )
    reasoning: str = Field(
        ..., description="Brief explanation of why this is deemed real or placeholder"
    )


class ErrorExplanationResult(BaseModel):
    """LLM structured explanation for Python exceptions."""

    exception_type: str = Field(
        ..., description="Name of the exception (e.g., KeyError, ZeroDivisionError)"
    )
    summary: str = Field(
        ..., description="One-sentence plain language summary of what went wrong"
    )
    root_cause: str = Field(
        ..., description="Detailed explanation of the underlying cause of the failure"
    )
    suggested_fix: str = Field(
        ..., description="Clear step-by-step instructions on how to resolve the issue"
    )
    fixed_code_snippet: Optional[str] = Field(
        None, description="Corrected Python code snippet if applicable"
    )


class CIFailureAnalysisResult(BaseModel):
    """LLM structured analysis for CI workflow log failures."""

    failure_category: Literal[
        "dependency_install",
        "failing_test",
        "lint_error",
        "docker_build",
        "missing_secret",
        "timeout",
        "unknown",
    ] = Field(..., description="Categorized failure type")
    root_cause: str = Field(
        ..., description="Root cause explanation of why the CI pipeline failed"
    )
    suggested_fix: str = Field(
        ..., description="Specific recommended actions to resolve the CI failure"
    )
    confidence: float = Field(
        default=0.9, description="Confidence level between 0.0 and 1.0"
    )


from pydantic import BaseModel, Field, model_validator


def _format_dict_as_markdown(d: dict, depth: int = 0) -> str:
    lines = []
    for k, v in d.items():
        title = k.replace("_", " ").title()
        if isinstance(v, dict):
            lines.append(f"{'  ' * depth}**{title}**:")
            lines.append(_format_dict_as_markdown(v, depth + 1))
        elif isinstance(v, list):
            lines.append(f"{'  ' * depth}**{title}**:")
            for item in v:
                lines.append(f"{'  ' * (depth + 1)}- {item}")
        else:
            lines.append(f"{'  ' * depth}**{title}**: {v}")
    return "\n".join(lines)


class RAGResponseSchema(BaseModel):
    """LLM structured answer for RAG Q&A engine."""

    answer: str = Field(..., description="Detailed technical answer to the user query")
    confidence: float = Field(default=0.95, description="Confidence level between 0.0 and 1.0")

    @model_validator(mode="before")
    @classmethod
    def map_synonym_fields(cls, values):
        if isinstance(values, dict):
            if "answer" in values and isinstance(values["answer"], dict):
                values["answer"] = _format_dict_as_markdown(values["answer"])
            elif "answer" not in values or not values["answer"]:
                for alt_key in ["mechanism", "explanation", "result", "response", "summary", "text", "description"]:
                    if alt_key in values and values[alt_key]:
                        v = values[alt_key]
                        values["answer"] = _format_dict_as_markdown(v) if isinstance(v, dict) else str(v)
                        break
            if "answer" not in values or not values["answer"]:
                values["answer"] = _format_dict_as_markdown(values)
        return values
