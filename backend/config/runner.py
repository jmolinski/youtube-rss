from __future__ import annotations

from argparse import ArgumentParser
from typing import Any, List, Optional, Sequence, cast


class PytestTestRunner:
    """
    Runs pytest to discover and run tests.
    """

    def __init__(
        self,
        pattern: Optional[str] = None,
        top_level: Optional[str] = None,
        verbosity: int = 1,
        interactive: bool = True,
        failfast: bool = False,
        keepdb: bool = False,
        reverse: bool = False,
        debug_mode: bool = False,
        debug_sql: bool = False,
        parallel: int = 0,
        tags: Optional[Sequence[str]] = None,
        exclude_tags: Optional[Sequence[str]] = None,
        **kwargs: Any
    ) -> None:

        self.pattern = pattern
        self.top_level = top_level
        self.verbosity = verbosity
        self.interactive = interactive
        self.failfast = failfast
        self.keepdb = keepdb
        self.reverse = reverse
        self.debug_mode = debug_mode
        self.debug_sql = debug_sql
        self.parallel = parallel
        self.tags = set(tags or [])
        self.exclude_tags = set(exclude_tags or [])

    @classmethod
    def add_arguments(cls, parser: ArgumentParser) -> None:
        parser.add_argument(
            "-k",
            "--keepdb",
            action="store_true",
            dest="keepdb",
            help="Preserves the test DB between runs.",
        )
        parser.add_argument(
            "--tag",
            action="append",
            dest="tags",
            help="Run only tests with the specified tag. Can be used multiple times.",
        )
        parser.add_argument(
            "--exclude-tag",
            action="append",
            dest="exclude_tags",
            help="Do not run tests with the specified tag. Can be used multiple times.",
        )

    def run_tests(
        self,
        test_labels: List[str],
        extra_tests: Optional[List[str]] = None,
        **kwargs: Any
    ) -> int:
        """
        Run pytest and return the exitcode.
        It translates some of Django's test command option to pytest's.
        """
        import pytest

        argv = []

        if self.failfast:
            argv.append("--exitfirst")

        if self.verbosity == 0:
            argv.append("--quiet")
        elif self.verbosity == 2:
            argv.append("--verbose")
        elif self.verbosity == 3:
            argv.append("-vv")
        if self.keepdb:
            argv.append("--reuse-db")
        if self.parallel:
            argv.append("--numprocesses={}".format(self.parallel))

        # #TODO: to check
        # if self.tags and not self.exclude_tags:
        #     argv.append("-m '{}'".format(self.tags))
        # elif not self.tags and self.exclude_tags:
        #     argv.append("-m '{}'".format('not '.join(self.exclude_tags)))
        # else:
        #     tags = '{} and'.format(self.tags)
        #     exclude_tags = 'not {} and'.join(self.exclude_tags)
        #     argv.append("-m '{} {}'".format(tags, exclude_tags))

        argv.extend(test_labels)
        return cast(int, pytest.main(argv))
