import itertools
import os
import re
import shlex
import textwrap
from collections import defaultdict
from collections.abc import Sequence
from functools import total_ordering

from ..typing import PathOrStr


def format_safe(template: str, **kwargs: str | os.PathLike[str]) -> str:
    """
    Works similarly to `template.format(**kwargs)`, except that unmatched
    fields in `template` are passed through untouched.

    >>> format_safe('{a} {b}', a='123')
    '123 {b}'
    >>> format_safe('{a} {b[4]:3f}', a='123')
    '123 {b[4]:3f}'

    To avoid variable expansion, precede with a single backslash e.g.
    >>> format_safe('\\{a} {b}', a='123')
    '{a} {b}'
    """

    result = template

    for key, value in kwargs.items():
        find_pattern = re.compile(
            rf"""
                (?<!\#)  # don't match if preceded by a hash
                {{  # literal open curly bracket
                {re.escape(key)}  # the field name
                }}  # literal close curly bracket
            """,
            re.VERBOSE,
        )

        result = re.sub(
            pattern=find_pattern,
            repl=str(value).replace("\\", r"\\"),
            string=result,
        )

        # transform escaped sequences into their literal equivalents
        result = result.replace(f"#{{{key}}}", f"{{{key}}}")

    return result


def prepare_command(command: str, **kwargs: PathOrStr) -> str:
    """
    Preprocesses a command by expanding variables like {project}.

    For example, used in the test_command option to specify the path to the
    project's root. Unmatched syntax will mostly be allowed through.
    """
    return format_safe(command, **kwargs)


def strtobool(val: str) -> bool:
    return val.lower() in {"y", "yes", "t", "true", "on", "1"}


def unwrap(text: str) -> str:
    """
    Unwraps multi-line text to a single line
    """
    # remove initial line indent
    text = textwrap.dedent(text)
    # remove leading/trailing whitespace
    text = text.strip()
    # remove consecutive whitespace
    return re.sub(r"\s+", " ", text)


def unwrap_preserving_paragraphs(text: str) -> str:
    """
    Unwraps multi-line text to a single line, but preserves paragraphs
    """
    # remove initial line indent
    text = textwrap.dedent(text)
    # remove leading/trailing whitespace
    text = text.strip()

    paragraphs = text.split("\n\n")
    # remove consecutive whitespace
    paragraphs = [re.sub(r"\s+", " ", paragraph) for paragraph in paragraphs]
    return "\n\n".join(paragraphs)


def parse_key_value_string(
    key_value_string: str,
    positional_arg_names: Sequence[str] | None = None,
    kw_arg_names: Sequence[str] | None = None,
) -> dict[str, list[str]]:
    """
    Parses a string like "docker; create_args: --some-option=value another-option"
    """
    if positional_arg_names is None:
        positional_arg_names = []
    if kw_arg_names is None:
        kw_arg_names = []

    all_field_names = [*positional_arg_names, *kw_arg_names]

    shlexer = shlex.shlex(key_value_string, posix=True, punctuation_chars=";")
    shlexer.commenters = ""
    shlexer.whitespace_split = True
    parts = list(shlexer)
    # parts now looks like
    # ['docker', ';', 'create_args:', '--some-option=value', 'another-option']

    # split by semicolon
    fields = [list(group) for k, group in itertools.groupby(parts, lambda x: x == ";") if not k]

    result: defaultdict[str, list[str]] = defaultdict(list)
    for field_i, field in enumerate(fields):
        # check to see if the option name is specified
        field_name, sep, first_value = field[0].partition(":")
        if sep:
            if field_name not in all_field_names:
                msg = f"Failed to parse {key_value_string!r}. Unknown field name {field_name!r}"
                raise ValueError(msg)

            values = ([first_value] if first_value else []) + field[1:]
        else:
            try:
                field_name = positional_arg_names[field_i]
            except IndexError:
                msg = f"Failed to parse {key_value_string!r}. Too many positional arguments - expected a maximum of {len(positional_arg_names)}"
                raise ValueError(msg) from None

            values = field

        result[field_name] += values

    return dict(result)


@total_ordering
class FlexibleVersion:
    version_str: str
    version_parts: tuple[int, ...]
    suffix: str

    def __init__(self, version_str: str) -> None:
        self.version_str = version_str

        # Split into numeric parts and the optional suffix
        match = re.match(r"^[v]?(\d+(\.\d+)*)(.*)$", version_str)
        if not match:
            msg = f"Invalid version string: {version_str}"
            raise ValueError(msg)

        version_part, _, suffix = match.groups()

        # Convert numeric version part into a tuple of integers
        self.version_parts = tuple(map(int, version_part.split(".")))
        self.suffix = suffix.strip() if suffix else ""

        # Normalize by removing trailing zeros
        self.version_parts = self._remove_trailing_zeros(self.version_parts)

    @staticmethod
    def _remove_trailing_zeros(parts: tuple[int, ...]) -> tuple[int, ...]:
        # Remove trailing zeros for accurate comparisons
        # without this, "3.0" would be considered greater than "3"
        while parts and parts[-1] == 0:
            parts = parts[:-1]
        return parts

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FlexibleVersion):
            raise NotImplementedError()
        return (self.version_parts, self.suffix) == (other.version_parts, other.suffix)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, FlexibleVersion):
            raise NotImplementedError()
        return (self.version_parts, self.suffix) < (other.version_parts, other.suffix)

    def __repr__(self) -> str:
        return f"FlexibleVersion('{self.version_str}')"

    def __str__(self) -> str:
        return self.version_str
