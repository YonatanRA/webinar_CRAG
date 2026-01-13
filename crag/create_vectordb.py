"""
Deprecated module. Please use `rag.create_vectordb` instead.
This file remains for backward compatibility and re-exports VectorDB.
"""

from rag.create_vectordb import VectorDB  # re-export

if __name__ == '__main__':
    print("[DEPRECATED] Use `python rag/create_vectordb.py` instead.")

