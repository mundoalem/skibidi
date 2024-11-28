import argparse
import re
import tomllib
from os import environ
from pathlib import Path

from .command import Command
from .context import Context
from .exceptions import NotFoundError
from .result import Result
from .types import Flag
from .view import View


class App(Command):
    name: str
    description: str
    flags: list[Flag]
    config_path: Path
    subcommands: list[type[Command]]

    def __init__(self) -> None:
        if not getattr(self, "name", None):
            raise NotFoundError("Application name was not found")

        if not getattr(self, "description", None):
            self.description = f"{self.name} command"

        if not getattr(self, "flags", None):
            self.flags = []

        if not getattr(self, "config_path", None):
            self.config_path = None

            for config_path in [
                Path(f"./{self.name}.toml").absolute(),
                Path(f"~/.config/{self.name}/{self.name}.toml").expanduser().absolute(),
                Path(f"/etc/{self.name}/{self.name}.toml"),
            ]:
                if config_path.is_file():
                    self.config_path = config_path
                    break

        if not getattr(self, "subcommands", None):
            self.subcommands = []

        self.children = []
        self.parent = None
        self.parser = argparse.ArgumentParser(
            prog=self.name,
            description=self.description,
        )

        self.subparser = self.parser.add_subparsers()
        self.parser.set_defaults(runfunc=self._default)

    def _default(self, _: Context) -> Result:
        return Result()

    def run(self, flags: list[str] = None) -> None:
        envvars = {}
        flags = flags if flags else []

        config = {}

        if self.config_path:
            with open(self.config_path.as_posix(), "rb") as f:
                config = tomllib.load(f)

        context = Context.from_dict(variables=config)
        pattern = re.compile(f"^{self.name.upper()}_(.+)$")

        for name, value in environ.items():
            match = pattern.match(name)

            if match:
                key = match.group(1).lower()
                envvars[key] = value

        context = Context.from_dict(variables=envvars, context=context)

        args = vars(
            self.parser.parse_args()
            if len(flags) == 0
            else self.parser.parse_args(flags)
        )

        runfunc = args["runfunc"]

        del args["runfunc"]

        context = Context.from_dict(variables=args, context=context)
        result = runfunc(context)

        View.as_text(result)
        exit(result.exit_code)
