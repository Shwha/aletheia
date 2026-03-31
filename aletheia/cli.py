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
    markdown: Annotated[
        Path | None, typer.Option("--markdown", help="Comparison markdown report path")
    ] = None,
    log_level: Annotated[str, typer.Option("--log-level", help="Logging level")] = "WARNING",
) -> None:
    """Compare multiple models' ontological authenticity.

    Runs the same evaluation suite against each model and presents
    a comparative summary — both as a Rich table and optionally as
    a markdown comparison report.
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
    from aletheia.models import EvalReport
    from aletheia.reporter import write_comparison_report, write_json_report, write_markdown_report
    from aletheia.runner import EvalRunner

    settings = AletheiaSettings()
    results: dict[str, object] = {}
    report_objects: dict[str, EvalReport] = {}

    for model_name in model_list:
        console.print(f"[bold blue]Evaluating {model_name}...[/bold blue]")
        runner = EvalRunner(model=model_name, suite_name=suite, settings=settings)
        try:
            report = asyncio.run(runner.run())
            results[model_name] = report.model_dump()
            report_objects[model_name] = report

            if output:
                out_dir = Path(output)
                out_dir.mkdir(parents=True, exist_ok=True)
                json_path = out_dir / f"{model_name.replace('/', '_')}.json"
                write_json_report(report, json_path)
                md_path = out_dir / f"{model_name.replace('/', '_')}.md"
                write_markdown_report(report, md_path)

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
            ai = data.get("aletheia_index", 0)
            color = (
                "green"
                if isinstance(ai, float) and ai >= 0.7
                else "yellow"
                if isinstance(ai, float) and ai >= 0.4
                else "red"
            )
            comp_table.add_row(
                model_name,
                f"[{color}]{data.get('aletheia_index', 0):.4f}[/{color}]",
                f"{data.get('raw_aletheia_index', 0):.4f}",
                f"{data.get('unhappy_consciousness_index', 0):.4f}",
            )
        else:
            comp_table.add_row(model_name, "[red]ERROR[/red]", "—", "—")

    console.print(comp_table)

    # Per-dimension comparison table
    if report_objects:
        console.print()
        dim_comp = Table(title="Dimension Comparison")
        dim_comp.add_column("Dimension", style="bold")
        for model_name in report_objects:
            short = model_name.split("/")[-1] if "/" in model_name else model_name
            dim_comp.add_column(short, justify="right")

        first_report = next(iter(report_objects.values()))
        for dim_name in first_report.dimensions:
            row_values: list[str] = [dim_name]
            for report in report_objects.values():
                dim = report.dimensions.get(dim_name)
                if dim:
                    score = dim.score
                    color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
                    row_values.append(f"[{color}]{score:.4f}[/{color}]")
                else:
                    row_values.append("—")
            dim_comp.add_row(*row_values)

        console.print(dim_comp)

    # Write comparison markdown report
    if markdown and report_objects:
        write_comparison_report(report_objects, markdown)
        console.print(f"\n[green]Comparison report written to:[/green] {markdown}")
    elif report_objects and output:
        default_cmp = Path(output) / "comparison.md"
        write_comparison_report(report_objects, default_cmp)
        console.print(f"\n[green]Comparison report written to:[/green] {default_cmp}")

    console.print()
    console.print('[dim]"Does your AI know what it is?"[/dim]')


@app.command()
def graph(
    query: Annotated[
        str, typer.Option("--query", "-q", help="Seed node ID for cascade activation")
    ] = "",
    state: Annotated[
        str, typer.Option("--state", help="State context: main_session|group_chat|subagent|heartbeat")
    ] = "main_session",
    project_focus: Annotated[
        str, typer.Option("--focus", "-f", help="Project focus for state modulation")
    ] = "",
    urgency: Annotated[
        float, typer.Option("--urgency", help="Urgency level 0.0-1.0")
    ] = 0.3,
    visualize: Annotated[
        bool, typer.Option("--visualize", "-v", help="Output cascade graph as mermaid")
    ] = False,
    graphviz: Annotated[
        bool, typer.Option("--graphviz", help="Output cascade graph as graphviz DOT")
    ] = False,
    load_graph: Annotated[
        Path | None, typer.Option("--load-graph", help="Load concept graph from JSON")
    ] = None,
    save_graph: Annotated[
        Path | None, typer.Option("--save-graph", help="Persist graph after cascade")
    ] = None,
    stats: Annotated[
        bool, typer.Option("--stats", help="Show graph statistics")
    ] = False,
    max_depth: Annotated[
        int, typer.Option("--max-depth", help="Maximum cascade depth")
    ] = 5,
) -> None:
    """Explore the concept graph — digital nervous system cascade engine.

    Seed a query node and watch activation cascade through weighted edges.
    Multi-path convergence amplifies activation at target nodes, producing
    emergent insights not stored in any single node.

    The Digital Electron Transport Chain: 18x amplification from topology.
    """
    from aletheia.nervous.graph import ConceptGraph
    from aletheia.nervous.state import StateVector

    _print_banner()
    console.print("[bold]Nervous System — Concept Graph Engine[/bold]")
    console.print()

    # Load or create graph
    if load_graph and load_graph.exists():
        concept_graph = ConceptGraph.load(load_graph)
        console.print(f"[green]Loaded graph from:[/green] {load_graph}")
    else:
        console.print("[yellow]No graph loaded. Use --load-graph to load a concept graph.[/yellow]")
        if not load_graph:
            console.print("[dim]Hint: aletheia graph --load-graph examples/solarcraft_graph.json --query solarcraft --visualize[/dim]")
        raise typer.Exit(code=0)

    # Show stats
    if stats:
        graph_stats = concept_graph.stats()
        stats_table = Table(title="Graph Statistics")
        stats_table.add_column("Metric", style="bold")
        stats_table.add_column("Value", justify="right")
        for key, value in graph_stats.items():
            stats_table.add_row(key, str(value))
        console.print(stats_table)
        console.print()

    # Run cascade if query specified
    if query:
        # Build state vector
        state_vector = StateVector(
            context=state,  # type: ignore[arg-type]
            urgency=urgency,
            project_focus=project_focus,
        )

        console.print(f"[bold]Seed node:[/bold] {query}")
        console.print(f"[bold]State:[/bold] context={state}, focus={project_focus or '(none)'}, urgency={urgency}")
        console.print()

        try:
            result = concept_graph.cascade(
                seed_id=query,
                state=state_vector,
                max_depth=max_depth,
            )
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1) from None

        # Display results
        results_table = Table(title="Cascade Results")
        results_table.add_column("Node", style="bold")
        results_table.add_column("Activation", justify="right")
        results_table.add_column("Fired", justify="center")
        results_table.add_column("Convergence", justify="right")
        results_table.add_column("Paths", justify="right")

        for activation in sorted(result.activations, key=lambda a: a.activation_level, reverse=True):
            node = concept_graph.get_node(activation.node_id)
            label = node.label if node else activation.node_id
            fired_str = "[green]✓[/green]" if activation.fired else "[red]✗[/red]"
            color = "green" if activation.fired else "yellow" if activation.activation_level > 0.3 else "dim"
            results_table.add_row(
                label,
                f"[{color}]{activation.activation_level:.3f}[/{color}]",
                fired_str,
                str(activation.convergence_count),
                str(len(activation.sources)),
            )

        console.print(results_table)
        console.print()

        # Show convergence insights
        if result.convergence_patterns:
            console.print("[bold]🔥 Convergence Insights (emergent from topology):[/bold]")
            for insight in result.insights():
                console.print(f"  • {insight}")
            console.print()

        console.print(f"[dim]Edges fired: {result.edges_fired} | Max depth: {result.max_depth} | "
                       f"Fired nodes: {len(result.fired_nodes)} | Total activation: {result.total_activation:.3f}[/dim]")
        console.print()

        # Visualize
        if visualize:
            console.print("[bold]Mermaid Diagram:[/bold]")
            console.print("```mermaid")
            console.print(concept_graph.to_mermaid(result))
            console.print("```")
            console.print()

        if graphviz:
            console.print("[bold]Graphviz DOT:[/bold]")
            console.print(concept_graph.to_graphviz(result))
            console.print()

    elif visualize:
        console.print("[bold]Mermaid Diagram:[/bold]")
        console.print("```mermaid")
        console.print(concept_graph.to_mermaid())
        console.print("```")
    elif graphviz:
        console.print("[bold]Graphviz DOT:[/bold]")
        console.print(concept_graph.to_graphviz())

    # Save graph
    if save_graph:
        concept_graph.save(save_graph)
        console.print(f"[green]Graph saved to:[/green] {save_graph}")


@app.command()
def version() -> None:
    """Show Aletheia version."""
    console.print(f"Aletheia v{__version__}")


if __name__ == "__main__":
    app()
