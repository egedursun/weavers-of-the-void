def keep(row: object, key: str, value: object) -> None:
    if key not in getattr(row, "locked", []):
        setattr(row, key, value)
