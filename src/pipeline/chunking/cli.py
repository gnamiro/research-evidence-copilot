from database.connection import engine
from pipeline.chunking.workflow import load_abstract_chunks


def main():
    with engine.begin() as connection:
        result = load_abstract_chunks(connection)

    print("Abstract chunk loading completed.")
    print(f"Chunks created: {result['chunks_created']}")
    print(f"Chunks inserted: {result['inserted_count']}")
    print(f"Chunks skipped: {result['skipped_count']}")


if __name__ == "__main__":
    main()