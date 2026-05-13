from __future__ import annotations

import logging
from typing import Any

from app.agents.nodes.node_utils import context_block
from app.core.database import (
    get_paper,
    get_paper_chunks,
    get_qa_history,
    get_report,
    save_qa_message,
)
from app.schemas.chunks import ChunkMetadata, PaperChunk
from app.services.llm_client import LLMClient
from app.services.retrieval import retrieve_context

logger = logging.getLogger(__name__)

MAX_QA_HISTORY = 12
KEEP_RECENT = 6

_SUMMARIZE_PROMPT_ZH = "请将以下对话历史压缩为一段简洁的摘要，保留关键问题和结论，不超过200字。"
_SUMMARIZE_PROMPT_EN = "Summarize the following conversation history concisely, preserving key questions and conclusions. Max 200 words."

QA_SYSTEM_PROMPT_ZH = """你是一个论文分析助手。用户上传了一篇论文，系统已经完成了分析并生成了复现报告。
现在用户想就这篇论文提问。请根据论文内容和分析报告回答用户的问题。

回答要求：
- 基于论文内容回答，不要编造信息
- 如果论文中没有相关信息，诚实说明
- 引用具体的论文片段或页码来支持你的回答
- 回答简洁明了，使用中文"""

QA_SYSTEM_PROMPT_EN = """You are a paper analysis assistant. The user uploaded a paper, and the system has completed analysis and generated a reproduction report.
Now the user wants to ask questions about this paper. Please answer based on the paper content and analysis report.

Requirements:
- Answer based on paper content, do not fabricate information
- If the paper lacks relevant information, state this honestly
- Cite specific paper passages or page numbers to support your answers
- Keep answers concise and clear, use English"""


def _chunks_from_rows(rows: list[dict[str, Any]]) -> list[PaperChunk]:
    chunks: list[PaperChunk] = []
    for row in rows:
        meta = ChunkMetadata(
            chunk_index=row["chunk_index"],
            page_start=row["page_start"],
            page_end=row["page_end"],
            section_title=row.get("section_title"),
        )
        chunks.append(PaperChunk(content=row["content"], metadata=meta))
    return chunks


def build_qa_context(
    run_id: str,
    paper_id: str,
    question: str,
    *,
    top_k: int = 6,
    max_context_chars: int = 9000,
) -> tuple[str, list[PaperChunk]]:
    paper = get_paper(paper_id)
    paper_title = paper["title"] if paper and paper.get("title") else "Unknown Paper"

    report = get_report(run_id)
    report_summary = ""
    if report and report.get("content"):
        report_summary = report["content"][:2000]

    chunk_rows = get_paper_chunks(paper_id)
    chunks = _chunks_from_rows(chunk_rows)

    retrieved = retrieve_context(chunks, query=question, top_k=top_k)
    context = context_block(retrieved, max_chars=max_context_chars)

    system_prompt = (
        f"Paper: {paper_title}\n\n"
        f"Report summary:\n{report_summary}\n\n"
        f"Relevant paper excerpts:\n{context}"
    )
    return system_prompt, chunks


def build_messages_with_summary(
    history: list[dict[str, Any]],
    question: str,
    *,
    model_name: str | None = None,
    language: str = "zh",
) -> list[dict[str, str]]:
    prior = history[:-1]
    if len(prior) <= MAX_QA_HISTORY:
        messages: list[dict[str, str]] = []
        for msg in prior:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": question})
        return messages

    old_messages = prior[:-KEEP_RECENT]
    recent_messages = prior[-KEEP_RECENT:]

    summary = _summarize_history(old_messages, model_name=model_name, language=language)

    messages = [{"role": "system", "content": summary}]
    for msg in recent_messages:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})
    return messages


def _summarize_history(
    messages: list[dict[str, Any]],
    *,
    model_name: str | None = None,
    language: str = "zh",
) -> str:
    prompt = _SUMMARIZE_PROMPT_ZH if language == "zh" else _SUMMARIZE_PROMPT_EN
    lines = [f"{m['role']}: {m['content']}" for m in messages]
    conversation = "\n".join(lines)

    client = LLMClient(model_name=model_name)
    if not client.is_configured():
        return conversation[:500]

    try:
        return client.chat(
            system_prompt=prompt,
            messages=[{"role": "user", "content": conversation}],
            temperature=0.2,
        )
    except Exception:
        logger.warning("Failed to summarize Q&A history", exc_info=True)
        return conversation[:500]


def answer_question(
    run_id: str,
    paper_id: str,
    question: str,
    *,
    model_name: str | None = None,
    language: str = "zh",
) -> tuple[dict[str, Any], dict[str, Any]]:
    user_msg = save_qa_message(run_id, paper_id, "user", question)

    history = get_qa_history(run_id)

    system_prompt, _chunks = build_qa_context(run_id, paper_id, question)

    client = LLMClient(model_name=model_name)
    if not client.is_configured():
        fallback = (
            "LLM 未配置，无法生成回答。请在设置中配置 OpenAI API Key。"
            if language == "zh"
            else "LLM is not configured. Please set up the OpenAI API Key in settings."
        )
        assistant_msg = save_qa_message(run_id, paper_id, "assistant", fallback)
        return user_msg, assistant_msg

    system_header = QA_SYSTEM_PROMPT_ZH if language == "zh" else QA_SYSTEM_PROMPT_EN
    full_system = f"{system_header}\n\n{system_prompt}"

    messages = build_messages_with_summary(
        history, question, model_name=model_name, language=language,
    )

    try:
        answer = client.chat(system_prompt=full_system, messages=messages)
    except Exception:
        logger.warning("Q&A LLM call failed", exc_info=True)
        fallback = (
            "抱歉，回答生成失败，请稍后重试。"
            if language == "zh"
            else "Sorry, answer generation failed. Please try again later."
        )
        assistant_msg = save_qa_message(run_id, paper_id, "assistant", fallback)
        return user_msg, assistant_msg

    assistant_msg = save_qa_message(run_id, paper_id, "assistant", answer)
    return user_msg, assistant_msg
