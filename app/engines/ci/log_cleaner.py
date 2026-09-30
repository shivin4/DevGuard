import re


def strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from terminal log output."""
    ansi_regex = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_regex.sub("", text)


def remove_timestamps(text: str) -> str:
    """Remove GitHub Actions ISO timestamp prefixes (e.g., 2024-03-30T12:00:00.1234567Z )."""
    timestamp_regex = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s*", re.MULTILINE)
    return timestamp_regex.sub("", text)


def clean_ci_log(raw_log: str, max_lines: int = 150) -> str:
    """Clean ANSI colors, timestamps, and return the relevant tail end of failure log."""
    cleaned = strip_ansi(raw_log)
    cleaned = remove_timestamps(cleaned)

    lines = cleaned.splitlines()
    if len(lines) > max_lines:
        # Keep initial context (first 20 lines) and trailing error window (last max_lines-20 lines)
        header = lines[:20]
        tail = lines[-(max_lines - 20) :]
        cleaned_lines = header + ["\n... [Truncated middle log lines] ...\n"] + tail
        return "\n".join(cleaned_lines)

    return "\n".join(lines)
