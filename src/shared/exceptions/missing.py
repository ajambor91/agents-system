class _Missing:
    """Internal placeholder: defer missing-field errors until validate()."""

    def __repr__(self) -> str:
        return "<MISSING>"


_MISSING = _Missing()