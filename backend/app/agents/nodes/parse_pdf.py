from app.agents.state import PaperAnalysisState
from app.services.pdf_parser import parse_pdf


def parse_pdf_node(state: PaperAnalysisState) -> PaperAnalysisState:
    parsed = parse_pdf(state["pdf_path"])
    return {"parsed_paper": parsed, "status": "parsed"}
