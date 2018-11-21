from sqlalchemy import create_engine as create_mem_engine

memory = 'sqlite://'


try:
    import sqlite3

    def _test_engine():
        sqlite3  # mark used
        return create_mem_engine(memory)
except ImportError:
    from jdbc_test import SqliteJDBC

    def _test_engine():
        return create_mem_engine(memory, module=SqliteJDBC)
