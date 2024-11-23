"""CLI package."""

import typer

app = typer.Typer()


@app.command()
def hello(name: str):
    """_summary_.

    Args:
        name: _description_
    """
    print(f"Hello {name}")


@app.command()
def goodbye(name: str, formal: bool = False):
    """_summary_.

    Args:
        name: _description_
        formal: _description_. Defaults to False.
    """
    if formal:
        print(f"Goodbye Ms. {name}. Have a good day.")
    else:
        print(f"Bye {name}!")


def main():
    """_summary_."""
    app()
