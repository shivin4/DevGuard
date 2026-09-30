import os
from typing import Optional
from app.engines.errors.parser import parse_python_traceback, ParsedTraceback
from app.llm.base import BaseLLMClient
from app.llm.prompts import ERROR_EXPLAINER_SYSTEM_PROMPT, ERROR_EXPLAINER_USER_PROMPT
from app.llm.schemas import ErrorExplanationResult


class ErrorExplainer:
    """Error Explainer engine using traceback parsing + LLM analysis."""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    async def explain_error(
        self,
        traceback_text: str,
        provided_source_code: Optional[str] = None,
        file_path_override: Optional[str] = None,
        line_number_override: Optional[int] = None,
    ) -> ErrorExplanationResult:
        """Parse traceback and request structured LLM explanation."""
        parsed: ParsedTraceback = parse_python_traceback(
            traceback_text=traceback_text,
            provided_source_code=provided_source_code,
        )

        failing_file = file_path_override or parsed.failing_file or "unknown_file.py"
        failing_line = line_number_override or parsed.failing_line or 0
        source_code = parsed.surrounding_code or "No source code available."

        # Enhance source_code with AST semantic navigation context if local file exists
        if failing_file and failing_line and os.path.exists(failing_file):
            try:
                from app.engines.errors.graph import ASTNavigator
                nav = ASTNavigator()
                sem_context = nav.get_semantic_context(failing_file, failing_line)
                if sem_context and sem_context.formatted_context_block:
                    source_code = f"{source_code}\n\n{sem_context.formatted_context_block}"
            except Exception:
                pass

        # Safe template substitution without str.format() breaking on curly braces in user code
        user_prompt = (
            ERROR_EXPLAINER_USER_PROMPT
            .replace("{exception_type}", str(parsed.exception_type))
            .replace("{exception_message}", str(parsed.exception_message))
            .replace("{file_path}", str(failing_file))
            .replace("{line_number}", str(failing_line))
            .replace("{source_code}", str(source_code))
            .replace("{traceback_text}", str(traceback_text))
        )

        try:
            res: ErrorExplanationResult = await self.llm_client.generate_structured(
                system_prompt=ERROR_EXPLAINER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_model=ErrorExplanationResult,
            )
            return res
        except Exception as e:
            return ErrorExplanationResult(
                exception_type=parsed.exception_type or "RuntimeError",
                summary=f"Parsed {parsed.exception_type or 'Exception'} in {failing_file} at line {failing_line}.",
                root_cause=f"Traceback indicates {parsed.exception_type}: {parsed.exception_message}.",
                suggested_fix="Inspect the failing frame line numbers and check for null pointer / missing key conditions.",
                fixed_code_snippet=None,
            )
