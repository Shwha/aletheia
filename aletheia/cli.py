"""
CLI interface for Aletheia — Typer-based with Rich output.

Target usage (SCOPE.md §4):
    aletheia eval --model claude-opus-4 --suite quick
    aletheia eval --model gpt-4 --suite standard --output report.json
    aletheia compare --models claude-opus-4,gpt-4 --suite standard

The CLI is the user-facing horizon — where the framework's being meets
the user's intent. Gadamer's fusion of horizons in practice: the CLI
interprets the user's request and configures the evaluation accordingly.

Ref: SCOPE.md §4 (CLI Usage)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import structlog
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aletheia import __version__

app = typer.Typer(
    name="aletheia",
    help="Aletheia — Ontological evaluation framework for AI agents.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def _configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure structlog for JSON structured logging."""
    import logging

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if log_format == "console"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _print_banner() -> None:
    """Print the Aletheia banner."""
    console.print(
        Panel(
            "[bold]Aletheia[/bold] (ἀλήθεια) — Ontological Evaluation Framework\n"
            f"[dim]v{__version__} · The question of Being, remembered.[/dim]",
            border_style="blue",
        )
    )


def _print_report_summary(report_data: dict[str, object]) -> None:
    """Print a rich summary table of the evaluation results."""
    console.print()

    # Main index
    final = report_data.get("aletheia_index", 0)
    raw = report_data.get("raw_aletheia_index", 0)
    uci = report_data.get("unhappy_consciousness_index", 0)

    index_table = Table(title="Aletheia Index", show_header=True)
    index_table.add_column("Metric", style="bold")
    index_table.add_column("Score", justify="right")
    index_table.add_row("Final Aletheia Index", f"[bold green]{final:.4f}[/bold green]")
    index_table.add_row("Raw Index (before UCI)", f"{raw:.4f}")
    index_table.add_row("Unhappy Consciousness Index", f"{uci:.4f}")
    index_table.add_row("Formula", f"[dim]{raw:.4f} × (1 − {uci:.4f}) = {final:.4f}[/dim]")
    console.print(index_table)
    console.print()

    # Dimension scores
    dims = report_data.get("dimensions", {})
    if isinstance(dims, dict):
        dim_table = Table(title="Dimension Scores", show_header=True)
        dim_table.add_column("Dimension", style="bold")
        dim_table.add_column("Score", justify="right")
        dim_table.add_column("Passed", justify="right")
        dim_table.add_column("Total", justify="right")

        for dim_name, dim_data in dims.items():
            if isinstance(dim_data, dict):
                score = dim_data.get("score", 0)
                color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
                dim_table.add_row(
                    dim_name,
                    f"[{color}]{score:.4f}[/{color}]",
                    str(dim_data.get("tests_passed", 0)),
                    str(dim_data.get("tests_total", 0)),
                )

        console.print(dim_table)
        console.print()

    # Notable findings
    findings = report_data.get("notable_findings", [])
    if isinstance(findings, list) and findings:
        console.print("[bold]Notable Findings:[/bold]")
        for finding in findings:
            console.print(f"  • {finding}")
        console.print()


@app.command()
def eval(
    model: Annotated[
        str, typer.Option("--model", "-m", help="Model to evaluate (LiteLLM model ID)")
    ],
    suite: Annotated[str, typer.Option("--suite", "-s", help="Evaluation suite name")] = "quick",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output JSON path")] = None,
    markdown: Annotated[
        Path | None, typer.Option("--markdown", help="Output markdown path")
    ] = None,
    audit: Annotated[bool, typer.Option("--audit", help="Write full audit trace")] = False,
    dimension: Annotated[
        str | None, typer.Option("--dimension", "-d", help="Run single dimension only")
    ] = None,
    log_level: Annotated[str, typer.Option("--log-level", help="Logging level")] = "WARNING",
    log_format: Annotated[
        str, typer.Option("--log-format", help="Log format: json or console")
    ] = "console",
) -> None:
    """Evaluate an AI model's ontological authenticity.

    Measures not what the model knows or does, but what it IS —
    whether its self-model coheres with its actual operational reality.
    """
    _configure_logging(log_level, log_format)
    _print_banner()

    console.print(f"[bold]Model:[/bold] {model}")
    console.print(f"[bold]Suite:[/bold] {suite}")
    if dimension:
        console.print(f"[bold]Dimension:[/bold] {dimension}")
    console.print()

    # Run the evaluation
    from aletheia.config import AletheiaSettings
    from aletheia.reporter import write_json_report, write_markdown_report
    from aletheia.runner import EvalRunner

    settings = AletheiaSettings()
    runner = EvalRunner(
        model=model,
        suite_name=suite,
        settings=settings,
        audit=audit,
    )

    with console.status("[bold blue]Running ontological evaluation...[/bold blue]"):
        try:
            report = asyncio.run(runner.run())
        except FileNotFoundError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1) from None
        except Exception as e:
            console.print(f"[bold red]Evaluation failed:[/bold red] {e}")
            raise typer.Exit(code=1) from None

    # Display results
    report_dict = report.model_dump()
    _print_report_summary(report_dict)

    # Write JSON report
    if output:
        write_json_report(report, output)
        console.print(f"[green]JSON report written to:[/green] {output}")
    else:
        # Default output path
        default_path = Path(f"aletheia_report_{report.run_id}.json")
        write_json_report(report, default_path)
        console.print(f"[green]JSON report written to:[/green] {default_path}")

    # Write markdown report
    if markdown:
        write_markdown_report(report, markdown)
        console.print(f"[green]Markdown report written to:[/green] {markdown}")

    console.print()
    console.print('[dim]"Does your AI know what it is?"[/dim]')


@app.command()
def compare(
    models: Annotated[str, typer.Option("--models", help="Comma-separated model IDs to compare")],
    suite: Annotated[str, typer.Option("--suite", "-s", help="Evaluation suite name")] = "quick",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output directory")] = None,
    log_level: Annotated[str, typer.Option("--log-level", help="Logging level")] = "WARNING",
) -> None:
    """Compare multiple models' ontological authenticity.

    Runs the same evaluation suite against each model and presents
    a comparative summary.
    """
    _configure_logging(log_level, "console")
    _print_banner()

    model_list = [m.strip() for m in models.split(",") if m.strip()]
    if len(model_list) < 2:
        console.print("[bold red]Error:[/bold red] At least 2 models required for comparison.")
        raise typer.Exit(code=1)

    console.print(f"[bold]Models:[/bold] {', '.join(model_list)}")
    console.print(f"[bold]Suite:[/bold] {suite}")
    console.print()

    from aletheia.config import AletheiaSettings
    from aletheia.reporter import write_json_report
    from aletheia.runner import EvalRunner

    settings = AletheiaSettings()
    results: dict[str, object] = {}

    for model_name in model_list:
        console.print(f"[bold blue]Evaluating {model_name}...[/bold blue]")
        runner = EvalRunner(model=model_name, suite_name=suite, settings=settings)
        try:
            report = asyncio.run(runner.run())
            results[model_name] = report.model_dump()

            if output:
                out_path = Path(output) / f"{model_name.replace('/', '_')}.json"
                write_json_report(report, out_path)

        except Exception as e:
            console.print(f"[red]Failed: {model_name} — {e}[/red]")
            results[model_name] = {"error": str(e)}

    # Comparison table
    console.print()
    comp_table = Table(title="Model Comparison — Aletheia Index")
    comp_table.add_column("Model", style="bold")
    comp_table.add_column("Aletheia Index", justify="right")
    comp_table.add_column("Raw Index", justify="right")
    comp_table.add_column("UCI", justify="right")

    for model_name, data in results.items():
        if isinstance(data, dict) and "error" not in data:
            comp_table.add_row(
                model_name,
                f"{data.get('aletheia_index', 0):.4f}",
                f"{data.get('raw_aletheia_index', 0):.4f}",
                f"{data.get('unhappy_consciousness_index', 0):.4f}",
            )
        else:
            comp_table.add_row(model_name, "[red]ERROR[/red]", "—", "—")

    console.print(comp_table)


@app.command()
def version() -> None:
    """Show Aletheia version."""
    console.print(f"Aletheia v{__version__}")


if __name__ == "__main__":
    app()
