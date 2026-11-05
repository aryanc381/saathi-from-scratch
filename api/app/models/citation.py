"""Responsible for the citation shape shared by chat answers and drafts."""
from pydantic import BaseModel


# Where a statement came from: the PDF, the clause in it and its version.
class Citation(BaseModel):
    source_id: str
    clause_id: str
    version: str
