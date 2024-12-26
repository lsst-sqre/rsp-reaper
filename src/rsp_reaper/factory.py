"""Component factory."""

from collections.abc import AsyncIterator
from contextlib import aclosing, asynccontextmanager
from typing import Self

import structlog
from structlog.stdlib import BoundLogger

from .config import Config


class Factory:
    """Build reaper components.

    Parameters
    ----------
    config: Config
        Reaper configuration.

    logger
        Logger to use for messages.
    """

    @classmethod
    @asynccontextmanager
    async def standalone(cls, config: Config) -> AsyncIterator[Self]:
        """Async context manager for reaper components.

        Intended for the test suite.

        Parameters
        ----------
        config
            Lab controller configuration

        Yields
        ------
        Factory
            Newly-created factory. Must be used as a context manager.
        """
        logger = structlog.get_logger(__name__)
        factory = cls(logger)
        async with aclosing(factory):
            yield factory

    def __init__(self, logger: BoundLogger) -> None:
        self._logger = logger
