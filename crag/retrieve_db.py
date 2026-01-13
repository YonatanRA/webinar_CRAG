"""
Deprecated module. Please use `rag.retrieve_db` instead.
This file remains for backward compatibility and re-exports ensemble_retriever.
"""

from rag.retrieve_db import ensemble_retriever  # re-export

if __name__ == '__main__':
    print("[DEPRECATED] Use `python rag/retrieve_db.py` instead.")

