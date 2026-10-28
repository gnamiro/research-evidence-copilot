import argparse

from database.connection import engine
from pipeline.embedding.workflow import load_missing_chunk_embeddings


def _positive_integer(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("batch size must be at least 1")
    return parsed


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate embeddings for document chunks that need them."
    )
    parser.add_argument(
        "--batch-size",
        type=_positive_integer,
        default=32,
        help="Number of chunks encoded per batch (default: 32).",
    )
    args = parser.parse_args(argv)

    with engine.begin() as connection:
        result = load_missing_chunk_embeddings(
            connection,
            batch_size=args.batch_size,
        )

    print("Chunk embedding loading completed.")
    print(f"Chunks selected: {result['chunks_selected']}")
    print(f"Embeddings created: {result['embeddings_created']}")
    print(f"Embeddings inserted: {result['inserted_count']}")
    print(f"Embeddings skipped: {result['skipped_count']}")


if __name__ == "__main__":
    main()
