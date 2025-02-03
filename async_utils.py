import asyncio
from typing import AsyncGenerator, Sequence, TypeVar

T = TypeVar("T")


async def iterate_blocking(iterator: Sequence[T]) -> AsyncGenerator[T]:
    loop = asyncio.get_running_loop()
    done = object()
    while True:
        obj = await loop.run_in_executor(None, next, iterator, done)
        if obj is done:
            break
        yield obj
