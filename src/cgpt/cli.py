import sys
import click


@click.command()
@click.option("--name", "-n", default="World", help="Who to greet")
def main(name: str) -> None:
    """Entry point for the cgpt CLI."""
    click.echo(f"Hello, {name}! from cgpt")
    sys.exit(0)


if __name__ == "__main__":
    main()
