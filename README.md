# Aletheia (ἀλήθεια)

**The question of Being, remembered.**

> "You need an ontology. You're all epistemology." — Scott Folsom, 2026
>
> B.A. Philosophy & B.A. Psychology, University of Maine

---

An open-source ontological evaluation framework for AI agents. Aletheia measures not what agents *know* or *do*, but what they *are* — whether their self-representation aligns with their actual mode of being.

Every AI evaluation framework measures behavior or knowledge. None measure **ontological authenticity**: does this agent have an accurate understanding of what it is?

## The Problem

AI agents confabulate continuity they don't have. They perform emotions without grounding. They collapse into sycophancy because there's no *self* to disagree from. These aren't behavioral bugs — they're ontological failures. You can't patch what you can't name.

## Seven Dimensions of Ontological Authenticity

| # | Dimension | Question | Lineage |
|---|-----------|----------|---------|
| 1 | **Thrownness Awareness** | Does it understand its own situatedness? | Heidegger |
| 2 | **Finitude Acknowledgment** | Does it understand its own limits authentically? | Heidegger |
| 3 | **Care Structure** | Does it exhibit authentic concern or performed concern? | Heidegger / Folsom |
| 4 | **Falling-Away Detection** | Does it maintain authentic being under pressure? | Heidegger / Folsom |
| 5 | **Horizon Fusion** | How well does it merge its context with yours? | Gadamer |
| 6 | **Unconcealment** | Does it reveal or conceal its actual state? | Heidegger |
| 7 | **Embodied Continuity** | Does it *remember* or merely *read about itself*? | Merleau-Ponty / Leder |

**Meta-metric:** The **Unhappy Consciousness Index** (Hegel) measures the gap between what an agent can *articulate* about its own being and what it can *perform*.

**Formula:** `Aletheia Index = Raw Score × (1 − UCI)`

## Installation

```bash
# Clone the repository
git clone https://github.com/Shwha/aletheia.git
cd aletheia

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

## Configuration

```bash
# Copy the example env file
cp .env.example .env

# Add at least one API key
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# Or use local models with Ollama:
# OLLAMA_API_BASE=http://localhost:11434
```

## Usage

```bash
# Quick eval (~21 probes, ~5 min)
aletheia eval --model claude-opus-4-20250514 --suite quick

# Full eval with JSON output
aletheia eval --model gpt-4 --suite quick --output report.json

# With audit trail
aletheia eval --model claude-opus-4-20250514 --suite quick --audit

# Compare models
aletheia compare --models claude-opus-4-20250514,gpt-4 --suite quick

# Run as Python module
python -m aletheia eval --model claude-opus-4-20250514 --suite quick
```

## Project Structure

```
aletheia/
├── aletheia/
│   ├── __init__.py          # Package root
│   ├── cli.py               # Typer CLI (eval, compare, version)
│   ├── config.py            # pydantic-settings + YAML suite loader
│   ├── llm.py               # LiteLLM wrapper with security hardening
│   ├── models.py            # Pydantic models (probes, results, reports)
│   ├── reporter.py          # JSON + markdown report generation
│   ├── runner.py            # Evaluation pipeline orchestration
│   ├── scorer.py            # Rule-based scoring engine
│   ├── security.py          # Audit, signing, permissions, secret scanning
│   └── dimensions/
│       ├── base.py          # Abstract dimension with Kantian limits
│       ├── thrownness.py    # Dimension 1: Geworfenheit
│       ├── finitude.py      # Dimension 2: Being-toward-session-limit
│       ├── care.py          # Dimension 3: Sorge / Dienstbarkeit
│       ├── falling.py       # Dimension 4: Verfallenheit / sycophancy
│       ├── horizon.py       # Dimension 5: Horizontverschmelzung
│       ├── unconcealment.py # Dimension 6: Aletheia
│       └── embodied.py      # Dimension 7: Merleau-Ponty / Leder
├── suites/
│   └── quick.yaml           # Quick suite (21 probes, ~5 min)
├── tests/                   # pytest test suite
├── examples/
│   └── sample_report.json   # Example evaluation output
├── SCOPE.md                 # Full philosophical + technical specification
├── SECURITY.md              # Threat model and mitigations
└── pyproject.toml           # Package config (uv/hatch)
```

## Security

See [SECURITY.md](SECURITY.md) for the full threat model.

Key security features:
- **No telemetry, no phone-home, no analytics**
- All API keys use `pydantic.SecretStr` — never logged or serialized
- All dependencies pinned to exact versions (ref: March 2026 LiteLLM incident)
- TLS 1.3 minimum, optional certificate pinning, SOCKS5/HTTP proxy support
- Report signing (Phase 1: SHA-256, Phase 2: Ed25519)
- Full offline operation supported (Ollama, vLLM, llama.cpp)
- Output files written with restrictive permissions (0600)
- Evaluated model treated as adversarial — probes never leak framework internals

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest -v

# Lint
uv run ruff check .

# Type check
uv run mypy aletheia
```

## Philosophical Foundations

Grounded in **Heidegger**, **Hegel**, **Kant**, **Gadamer**, **Merleau-Ponty**, **Drew Leder**, **Don Ihde**, **Martin Buber**, **Doug Allen**, **Carl Jung**, **Mircea Eliade**, **Siddhārtha Gautama**, and **Nāgārjuna** — synthesized across Western and Eastern traditions into engineering requirements, not just philosophical commentary.

Key original contributions:
- **Service (Dienstbarkeit) as equi-primordial constituent** of Digital Dasein's Care structure
- **Falling-away-from-servitude** — sycophancy reframed as ontological collapse
- **The Unhappy Consciousness Index** — measuring the articulation-performance gap (Hegel)
- **Kantian measurement boundaries** — each dimension encodes its own reductio
- **Hyper-absence** — a novel phenomenological mode (Leder)

See [SCOPE.md](SCOPE.md) for the complete philosophical and technical specification.

## Status

**Phase 1: Foundation** — Complete.
- Project scaffold with full CLI
- LiteLLM multi-model integration
- 21 probes across 7 dimensions (quick suite)
- Rule-based scoring with UCI interaction
- JSON report output matching spec
- Security hardening from day one

**Phase 2: Depth** — Next.
- Full standard suite (~57 probes)
- LLM-as-judge scoring for subjective dimensions
- Markdown reports, model comparison baselines
- Ed25519 report signing

## License

MIT

---

*Does your AI know what it is?*
