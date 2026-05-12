from collections.abc import Callable

from langgraph.graph import END, StateGraph

from app.agents.nodes.analyze_experiments import analyze_experiments_node
from app.agents.nodes.analyze_method import analyze_method_node
from app.agents.nodes.chunk_paper import chunk_paper_node
from app.agents.nodes.classify_paper_type import classify_paper_type_node
from app.agents.nodes.extract_metadata import extract_metadata_node
from app.agents.nodes.generate_report import generate_report_node
from app.agents.nodes.parse_pdf import parse_pdf_node
from app.agents.nodes.persist_result import persist_result_node
from app.agents.nodes.plan_reproduction import plan_reproduction_node
from app.agents.nodes.understand_paper import understand_paper_node
from app.agents.state import PaperAnalysisState


NODE_ORDER = [
    "parse_pdf_node",
    "chunk_paper_node",
    "extract_metadata_node",
    "classify_paper_type_node",
    "understand_paper_node",
    "analyze_method_node",
    "analyze_experiments_node",
    "plan_reproduction_node",
    "generate_report_node",
    "persist_result_node",
]


ProgressCallback = Callable[[str, int], None]


def _wrap_node(node_name: str, node_index: int, node_fn, progress_callback: ProgressCallback | None):
    def wrapped_node(state: PaperAnalysisState) -> PaperAnalysisState:
        total = len(NODE_ORDER)
        if progress_callback:
            progress_callback(node_name, int(node_index / total * 100))
        result = node_fn(state)
        if progress_callback:
            progress_callback(node_name, int((node_index + 1) / total * 100))
        return result

    return wrapped_node


def build_graph(progress_callback: ProgressCallback | None = None):
    graph = StateGraph(PaperAnalysisState)
    node_fns = {
        "parse_pdf_node": parse_pdf_node,
        "chunk_paper_node": chunk_paper_node,
        "extract_metadata_node": extract_metadata_node,
        "classify_paper_type_node": classify_paper_type_node,
        "understand_paper_node": understand_paper_node,
        "analyze_method_node": analyze_method_node,
        "analyze_experiments_node": analyze_experiments_node,
        "plan_reproduction_node": plan_reproduction_node,
        "generate_report_node": generate_report_node,
        "persist_result_node": persist_result_node,
    }
    for index, node_name in enumerate(NODE_ORDER):
        graph.add_node(node_name, _wrap_node(node_name, index, node_fns[node_name], progress_callback))

    graph.set_entry_point(NODE_ORDER[0])
    for current, next_node in zip(NODE_ORDER, NODE_ORDER[1:]):
        graph.add_edge(current, next_node)
    graph.add_edge(NODE_ORDER[-1], END)
    return graph.compile()


_default_workflow = None


def _get_default_workflow():
    global _default_workflow
    if _default_workflow is None:
        _default_workflow = build_graph()
    return _default_workflow


def run_analysis(
    paper_id: str,
    run_id: str,
    pdf_path: str,
    model_name: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> PaperAnalysisState:
    initial_state: PaperAnalysisState = {
        "paper_id": paper_id,
        "run_id": run_id,
        "pdf_path": pdf_path,
        "model_name": model_name or "",
        "status": "pending",
        "error_message": None,
    }
    active_workflow = build_graph(progress_callback) if progress_callback else _get_default_workflow()
    return active_workflow.invoke(initial_state)
