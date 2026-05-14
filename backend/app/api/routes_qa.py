from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.database import get_qa_history, get_report_language, get_run, save_qa_message
from app.schemas.qa import QaMessageResponse, QaRequest
from app.services.llm_client import LLMClient
from app.services.qa_service import (
    QA_SYSTEM_PROMPT_EN,
    QA_SYSTEM_PROMPT_ZH,
    answer_question,
    build_messages_with_summary,
    build_qa_context,
)

router = APIRouter(
    prefix="/runs",
    tags=["qa"],
    responses={404: {"description": "Run not found"}},
)


@router.get(
    "/{run_id}/qa",
    response_model=list[QaMessageResponse],
    summary="Get Q&A history",
    description="Retrieve the conversation history for a completed analysis run.",
)
def get_qa_messages(run_id: str) -> list[QaMessageResponse]:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    history = get_qa_history(run_id)
    return [QaMessageResponse(**msg) for msg in history]


@router.post(
    "/{run_id}/qa",
    response_model=list[QaMessageResponse],
    summary="Ask a question",
    description="Ask a follow-up question about the paper. Returns the user message and assistant reply. Requires the run to be completed.",
)
def ask_question(run_id: str, payload: QaRequest) -> list[QaMessageResponse]:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="分析任务不存在。")
    if run["status"] == "failed":
        raise HTTPException(status_code=400, detail="分析任务已失败，无法提问。请重新运行分析。")
    if run["status"] != "completed":
        raise HTTPException(status_code=400, detail="分析任务尚未完成，请等待分析结束后再提问。")

    paper_id = run["paper_id"]
    model_name = run.get("model_name")
    language = get_report_language()

    user_msg, assistant_msg = answer_question(
        run_id=run_id,
        paper_id=paper_id,
        question=payload.question,
        model_name=model_name,
        language=language,
    )
    return [QaMessageResponse(**user_msg), QaMessageResponse(**assistant_msg)]


@router.post(
    "/{run_id}/qa/stream",
    summary="Ask a question (streaming)",
    description="Ask a follow-up question with streaming response via Server-Sent Events (SSE).",
)
def ask_question_stream(run_id: str, payload: QaRequest):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="分析任务不存在。")
    if run["status"] == "failed":
        raise HTTPException(status_code=400, detail="分析任务已失败，无法提问。请重新运行分析。")
    if run["status"] != "completed":
        raise HTTPException(status_code=400, detail="分析任务尚未完成，请等待分析结束后再提问。")

    paper_id = run["paper_id"]
    model_name = run.get("model_name")
    language = get_report_language()

    save_qa_message(run_id, paper_id, "user", payload.question)

    system_prompt, _chunks = build_qa_context(run_id, paper_id, payload.question)
    history = get_qa_history(run_id)
    messages = build_messages_with_summary(
        history, payload.question, model_name=model_name, language=language,
    )

    system_header = QA_SYSTEM_PROMPT_ZH if language == "zh" else QA_SYSTEM_PROMPT_EN
    full_system = f"{system_header}\n\n{system_prompt}"

    client = LLMClient(model_name=model_name)
    if not client.is_configured():
        fallback = "LLM 未配置，无法生成回答。请在设置中配置 OpenAI API Key。" if language == "zh" else "LLM is not configured. Please set up the OpenAI API Key in settings."
        assistant_msg = save_qa_message(run_id, paper_id, "assistant", fallback)

        def _fallback_stream():
            yield f"data: {json.dumps({'type': 'token', 'content': fallback}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg['id']}, ensure_ascii=False)}\n\n"

        return StreamingResponse(_fallback_stream(), media_type="text/event-stream")

    def _generate():
        full_response = ""
        saved_msg = None

        def save_once():
            nonlocal saved_msg
            if saved_msg is None and full_response:
                saved_msg = save_qa_message(run_id, paper_id, "assistant", full_response)
            return saved_msg

        try:
            for token in client.chat_stream(system_prompt=full_system, messages=messages):
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
        except GeneratorExit:
            save_once()
            raise
        except Exception:
            error_msg = "回答生成失败，请稍后重试。" if language == "zh" else "Failed to generate answer. Please try again."
            if not full_response:
                full_response = error_msg
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg}, ensure_ascii=False)}\n\n"

        assistant_msg = save_once()
        if assistant_msg is None:
            assistant_msg = save_qa_message(run_id, paper_id, "assistant", "")
        yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg['id']}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
