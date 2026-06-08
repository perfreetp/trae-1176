from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./letter_platform.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def auto_migrate():
    with engine.connect() as conn:
        inspector = inspect(engine)
        for table_name, table_obj in Base.metadata.tables.items():
            if not inspector.has_table(table_name):
                continue
            existing_cols = {row["name"] for row in inspector.get_columns(table_name)}
            for column in table_obj.columns:
                if column.name not in existing_cols:
                    col_type = column.type.compile(dialect=engine.dialect)
                    default_val = ""
                    if column.default is not None:
                        arg = column.default.arg
                        if callable(arg):
                            pass
                        elif isinstance(arg, bool):
                            default_val = f" DEFAULT {1 if arg else 0}"
                        elif isinstance(arg, (int, float)):
                            default_val = f" DEFAULT {arg}"
                        elif isinstance(arg, str):
                            safe = arg.replace("'", "''")
                            default_val = f" DEFAULT '{safe}'"
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}{default_val}"
                    conn.execute(text(sql))
        conn.commit()
