import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, get_db
from app.engines.ci import CIFailureAnalyzer
from app.github import download_workflow_log, post_pr_comment, verify_github_signature
from app.llm import get_llm_client
from app.models.domain import Repository, WorkflowAnalysis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["GitHub Webhook"])


async def process_failed_workflow_run(
    owner: str,
    repo_name: str,
    run_id: int,
    workflow_name: str,
    job_name: str,
    pr_number: Optional[int],
):
    """Background worker to download log, analyze failure, save to DB, and post PR comment."""
    db: Session = SessionLocal()
    try:
        # Get or create repository record
        full_repo = f"{owner}/{repo_name}"
        repo_obj = db.query(Repository).filter(Repository.name == full_repo).first()
        if not repo_obj:
            repo_obj = Repository(name=full_repo, url=f"https://github.com/{full_repo}")
            db.add(repo_obj)
            db.commit()
            db.refresh(repo_obj)

        # Download raw logs
        raw_log = await download_workflow_log(owner=owner, repo=repo_name, run_id=run_id)

        # Analyze failure with CI engine + LLM
        llm_client = get_llm_client()
        analyzer = CIFailureAnalyzer(llm_client=llm_client)
        analysis = await analyzer.analyze_log(
            raw_log=raw_log,
            workflow_name=workflow_name,
            job_name=job_name,
        )

        # Save to database
        wf_analysis = WorkflowAnalysis(
            repository_id=repo_obj.id,
            workflow_name=workflow_name,
            job_name=job_name,
            pr_number=pr_number,
            failure_category=analysis.failure_category,
            root_cause=analysis.root_cause,
            suggested_fix=analysis.suggested_fix,
            confidence=analysis.confidence,
        )
        db.add(wf_analysis)
        db.commit()

        # Post PR comment if associated with a PR
        if pr_number:
            await post_pr_comment(
                owner=owner,
                repo=repo_name,
                pr_number=pr_number,
                analysis=analysis,
            )
    except Exception as e:
        logger.error(f"Error processing background CI failure task for {owner}/{repo_name} run {run_id}: {e}")
    finally:
        db.close()


@router.post("/github")
async def github_webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):
    """Handle incoming GitHub webhooks with instant 200 response and async background execution."""
    settings = get_settings()
    body_bytes = await request.body()

    # Verify signature if webhook secret is configured
    if settings.GITHUB_WEBHOOK_SECRET and settings.APP_ENV != "testing":
        if not x_hub_signature_256 or not verify_github_signature(
            body_bytes=body_bytes,
            signature_header=x_hub_signature_256,
            secret=settings.GITHUB_WEBHOOK_SECRET,
        ):
            raise HTTPException(status_code=401, detail="Invalid X-Hub-Signature-256 header signature.")

    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    # Process workflow_run events
    if x_github_event == "workflow_run" or "workflow_run" in payload:
        wf_run = payload.get("workflow_run", {})
        action = payload.get("action", "")
        conclusion = wf_run.get("conclusion", "")

        if action == "completed" and conclusion == "failure":
            repo_info = payload.get("repository", {})
            owner = repo_info.get("owner", {}).get("login", "owner")
            repo_name = repo_info.get("name", "repo")
            run_id = wf_run.get("id", 0)
            workflow_name = wf_run.get("name", "CI Workflow")
            job_name = wf_run.get("display_title", "build")

            pr_number = None
            prs = wf_run.get("pull_requests", [])
            if prs and len(prs) > 0:
                pr_number = prs[0].get("number")

            # Dispatch async background task
            background_tasks.add_task(
                process_failed_workflow_run,
                owner=owner,
                repo_name=repo_name,
                run_id=run_id,
                workflow_name=workflow_name,
                job_name=job_name,
                pr_number=pr_number,
            )

            return {
                "status": "accepted",
                "message": f"Queued background analysis for failed workflow run {run_id}",
            }

    return {"status": "ignored", "message": f"Event '{x_github_event}' does not require action"}
