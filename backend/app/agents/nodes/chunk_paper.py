from app.agents.state import PaperAnalysisState
from app.services.chunker import chunk_parsed_paper


def chunk_paper_node(state: PaperAnalysisState) -> PaperAnalysisState:
    chunked = chunk_parsed_paper(state["parsed_paper"])
    return {"chunked_paper": chunked, "status": "chunked"}
