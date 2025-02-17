from typing import Iterable, TypeVar

T = TypeVar("T")

def are_unique(c: Iterable[T]) -> bool:
    l = list(c)
    return len(set(l)) == len(l)
