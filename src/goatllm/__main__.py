"""Side-effect-free CLI foundation; runtime wiring comes in milestone B."""

import argparse

from goatllm import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="goatllm",
        description="GoatLLM planning scaffold for a Discord + local Ollama application.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    parser.exit(
        status=2,
        message=(
            "GoatLLM runtime is not implemented yet. "
            "See docs/IMPLEMENTATION_PLAN.md for milestones A-D.\n"
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
