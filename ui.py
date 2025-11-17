from __future__ import annotations

from typing import Iterable

try:
    from colorama import Fore, Style, init
except ImportError:  # pragma: no cover - fallback when colorama is missing
    class _Fore:
        BLACK = "\033[30m"
        RED = "\033[31m"
        GREEN = "\033[32m"
        YELLOW = "\033[33m"
        BLUE = "\033[34m"
        MAGENTA = "\033[35m"
        CYAN = "\033[36m"
        WHITE = "\033[37m"

    class _Style:
        BRIGHT = "\033[1m"
        DIM = "\033[2m"
        NORMAL = "\033[22m"
        RESET_ALL = "\033[0m"

    Fore = _Fore()  # type: ignore
    Style = _Style()  # type: ignore

    def init(*_args, **_kwargs):  # type: ignore
        return None

init(autoreset=True)


def banner(text: str) -> str:
    return f"{Style.BRIGHT}{Fore.CYAN}{text}{Style.RESET_ALL}"


def room_name(text: str) -> str:
    return f"{Style.BRIGHT}{Fore.CYAN}{text}{Style.RESET_ALL}"


def narration(text: str) -> str:
    return f"{Fore.WHITE}{text}{Style.RESET_ALL}"


def section(title: str, body: str) -> str:
    return f"{Style.BRIGHT}{Fore.YELLOW}{title}:{Style.RESET_ALL} {body}"


def divider(width: int = 54, char: str = "-") -> str:
    return f"{Style.DIM}{char * width}{Style.RESET_ALL}"


def success(text: str) -> str:
    return f"{Fore.GREEN}{text}{Style.RESET_ALL}"


def warning(text: str) -> str:
    return f"{Fore.MAGENTA}{text}{Style.RESET_ALL}"


def error(text: str) -> str:
    return f"{Fore.RED}{text}{Style.RESET_ALL}"


def info(text: str) -> str:
    return f"{Fore.CYAN}{text}{Style.RESET_ALL}"


def hint(text: str) -> str:
    return f"{Style.DIM}{text}{Style.RESET_ALL}"


def dialogue(name: str, text: str) -> str:
    speaker = f"{Style.BRIGHT}{Fore.MAGENTA}[{name}]"
    return f"{speaker}{Style.RESET_ALL} {Fore.MAGENTA}{text}{Style.RESET_ALL}"


def help_heading(title: str) -> str:
    return f"{Style.BRIGHT}{Fore.CYAN}{title}{Style.RESET_ALL}"


def help_section(title: str, commands: Iterable[str]) -> str:
    header = f"{Style.BRIGHT}{Fore.YELLOW}{title}{Style.RESET_ALL}"
    lines = [header]
    lines.extend(f"  {Fore.WHITE}{entry}{Style.RESET_ALL}" for entry in commands)
    return "\n".join(lines)


def command_prompt(room: str, time_of_day: str, marks: int) -> str:
    time_label = time_of_day.title()
    meta = f"[{room} | {time_label} | Marks: {marks}]"
    return f"\n{Style.DIM}{Fore.CYAN}{meta}{Style.RESET_ALL}\n> "


def emphasize(text: str) -> str:
    return f"{Style.BRIGHT}{text}{Style.RESET_ALL}"


def bullet(text: str) -> str:
    return f"{Fore.WHITE}- {text}{Style.RESET_ALL}"

