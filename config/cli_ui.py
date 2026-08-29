import shutil
import sys


class CLI:
    RESET = "\033[0m"
    BOLD = "\033[1m"

    PURPLE = "\033[38;5;111m"
    GREEN = "\033[38;5;78m"
    RED = "\033[38;5;203m"
    YELLOW = "\033[38;5;221m"
    CYAN = "\033[38;5;81m"
    MUTED = "\033[38;5;245m"

    def __init__(self, stdout=None):
        self.stdout = stdout or sys.stdout
        self.color = bool(
            hasattr(self.stdout, "isatty")
            and self.stdout.isatty()
        )

    def paint(self, text, color):
        if not self.color:
            return str(text)

        return f"{color}{text}{self.RESET}"

    def width(self):
        return min(
            max(shutil.get_terminal_size((80, 24)).columns, 54),
            86,
        )

    def line(self, char="─"):
        self.write(
            self.paint(
                char * self.width(),
                self.MUTED,
            )
        )

    def write(self, text=""):
        self.stdout.write(str(text) + "\n")
        self.stdout.flush()

    def header(self, section):
        width = self.width()

        self.write()
        self.write(
            self.paint(
                "━" * width,
                self.PURPLE,
            )
        )

        title = "COWO D'LA VAL"

        self.write(
            self.paint(
                f"  {title}",
                self.BOLD + self.PURPLE,
            )
        )

        self.write(
            self.paint(
                f"  {section}",
                self.BOLD,
            )
        )

        self.write(
            self.paint(
                "━" * width,
                self.PURPLE,
            )
        )
        self.write()

    def section(self, text):
        self.write()
        self.write(
            self.paint(
                text.upper(),
                self.BOLD + self.CYAN,
            )
        )
        self.line()

    def option(self, number, text, kind="normal"):
        colors = {
            "normal": self.CYAN,
            "primary": self.PURPLE,
            "success": self.GREEN,
            "danger": self.RED,
            "warning": self.YELLOW,
        }

        color = colors.get(
            kind,
            self.CYAN,
        )

        prefix = self.paint(
            f"[{number}]",
            self.BOLD + color,
        )

        self.write(
            f"  {prefix}  {text}"
        )

    def info(self, text):
        self.write(
            self.paint(
                f"ℹ  {text}",
                self.CYAN,
            )
        )

    def success(self, text):
        self.write(
            self.paint(
                f"✓  {text}",
                self.GREEN,
            )
        )

    def warning(self, text):
        self.write(
            self.paint(
                f"!  {text}",
                self.YELLOW,
            )
        )

    def error(self, text):
        self.write(
            self.paint(
                f"✗  {text}",
                self.RED,
            )
        )

    def empty(self, text):
        self.write()
        self.write(
            self.paint(
                f"  {text}",
                self.MUTED,
            )
        )
        self.write()

    def prompt(self, text):
        try:
            return input(
                self.paint(
                    f"› {text}: ",
                    self.BOLD + self.PURPLE,
                )
            ).strip()
        except (EOFError, KeyboardInterrupt):
            self.write()
            return ""

    def confirm(self, text):
        answer = self.prompt(
            f"{text} [y/N]"
        ).lower()

        return answer in {
            "y",
            "yes",
            "s",
            "si",
            "sì",
        }

    def pause(self):
        try:
            input(
                self.paint(
                    "\nPress Enter to continue...",
                    self.MUTED,
                )
            )
        except (EOFError, KeyboardInterrupt):
            pass
