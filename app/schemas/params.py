from typing import Annotated

from fastapi import Path, Query


PositivePathId = Annotated[int, Path(gt=0)]
PositiveQueryId = Annotated[int, Query(gt=0)]
PaginationSkip = Annotated[int, Query(ge=0)]
PaginationLimit = Annotated[int, Query(ge=1, le=100)]
IsbnPath = Annotated[str, Path(min_length=10, max_length=13, pattern=r"^\d+$")]
