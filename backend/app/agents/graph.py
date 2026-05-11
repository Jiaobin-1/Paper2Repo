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


def build_graph():
    graph = StateGraph(PaperAnalysisState)
    graph.add_node("parse_pdf_node", parse_pdf_node)
    graph.add_node("chunk_paper_node", chunk_paper_node)
    graph.add_node("extract_metadata_node", extract_metadata_node)
    graph.add_node("classify_paper_type_node", classify_paper_type_node)
    graph.add_node("understand_paper_node", understand_paper_node)
    graph.add_node("analyze_method_node", analyze_method_node)
    graph.add_node("analyze_experiments_node", analyze_experiments_node)
    graph.add_node("plan_reproduction_node", plan_reproduction_node)
    graph.add_node("generate_report_node", generate_report_node)
    graph.add_node("persist_result_node", persist_result_node)

    graph.set_entry_point(NODE_ORDER[0])
    for current, next_node in zip(NODE_ORDER, NODE_ORDER[1:]):
        graph.add_edge(current, next_node)
    graph.add_edge(NODE_ORDER[-1], END)
    return graph.compile()


workflow = build_graph()


def run_analysis(paper_id: str, run_id: str, pdf_path: str) -> PaperAnalysisState:
    initial_state: PaperAnalysisState = {
        "paper_id": paper_id,
        "run_id": run_id,
        "pdf_path": pdf_path,
        "status": "pending",
        "error_message": None,
    }
    return workflow.invoke(initial_state)
