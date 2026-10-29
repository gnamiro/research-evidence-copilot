def to_vector_literal(vector):
    """Convert a vector into pgvector's text representation."""

    if not isinstance(vector, (list, tuple)):
        raise TypeError("vector must be a list or tuple.")

    return "[" + ",".join(
        format(float(value), ".17g")
        for value in vector
    ) + "]"