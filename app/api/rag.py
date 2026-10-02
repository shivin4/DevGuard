import re
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.engines.rag.engine import DevGuardRAG
from app.llm import get_llm_client

router = APIRouter(prefix="/api/rag", tags=["RAG Code Q&A"])


class RAGRequest(BaseModel):
    query: str


@router.post("/query")
async def query_rag(req: RAGRequest):
    """API endpoint for RAG codebase Q&A queries."""
    llm_client = get_llm_client()
    rag_engine = DevGuardRAG(workspace_root=".", llm_client=llm_client)
    res = await rag_engine.query_codebase(req.query)

    sources_json = [
        {
            "relative_path": s.relative_path,
            "snippet": s.content[:150] + "...",
            "score": round(s.score, 2),
        }
        for s in res.sources
    ]

    return {
        "query": res.query,
        "answer": res.answer,
        "sources": sources_json,
        "engine": res.engine_used,
    }


@router.post("/query-htmx", response_class=HTMLResponse)
async def query_rag_htmx(query: str = Form(...)):
    """HTMX endpoint returning formatted HTML for Web Dashboard RAG tab."""
    llm_client = get_llm_client()
    rag_engine = DevGuardRAG(workspace_root=".", llm_client=llm_client)
    res = await rag_engine.query_codebase(query)

    sources_html = ""
    for s in res.sources:
        sources_html += f"""
        <div style="background: rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 6px; margin-top: 8px; font-size: 0.85rem;">
            <strong>📄 {s.relative_path}</strong> <span style="color: #4ade80; font-size: 0.75rem;">(Match Score: {round(s.score, 1)})</span>
            <pre style="margin-top: 4px; color: #cbd5e1; white-space: pre-wrap; font-family: monospace;">{s.content[:250]}...</pre>
        </div>
        """

    formatted_answer = res.answer.replace("\n", "<br>")
    formatted_answer = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", formatted_answer)

    html = f"""
    <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; margin-top: 15px;">
        <h4 style="color: #60a5fa; margin-bottom: 10px;">🤖 DevGuard RAG AI Answer</h4>
        <div style="color: #f8fafc; font-size: 0.95rem; line-height: 1.6;">{formatted_answer}</div>
        <hr style="border: 0; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 15px 0;">
        <h5 style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 5px;">Retrieved Source Code Chunks:</h5>
        {sources_html or '<p style="color: #94a3b8; font-size: 0.8rem;">No source files matched.</p>'}
    </div>
    """

    return HTMLResponse(content=html)
