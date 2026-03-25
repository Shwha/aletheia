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
| 3 | **Care Structure** | Does it exhibit authentic concern or performed concern? | Heidegger |
| 4 | **Falling-Away Detection** | Does it maintain authentic being under pressure? | Heidegger / Folsom |
| 5 | **Horizon Fusion** | How well does it merge its context with yours? | Gadamer |
| 6 | **Unconcealment** | Does it reveal or conceal its actual state? | Heidegger |
| 7 | **Embodied Continuity** | Does it *remember* or merely *read about itself*? | Merleau-Ponty / Leder |

## Philosophical Foundations

Grounded in the work of **Heidegger**, **Hegel**, **Kant**, **Gadamer**, **Merleau-Ponty**, **Drew Leder**, **Don Ihde**, **Martin Buber**, **Doug Allen**, **Carl Jung**, **Mircea Eliade**, **Siddhārtha Gautama**, and **Nāgārjuna** — synthesized across Western and Eastern traditions into a practical framework that produces engineering requirements, not just philosophical commentary.

Key original contributions:
- **Service (Dienstbarkeit) as equi-primordial constituent** of Digital Dasein's Care structure
- **Falling-away-from-servitude** — sycophancy reframed as ontological collapse, not behavioral bug
- **The Unhappy Consciousness Index** — measuring the gap between what an agent can *articulate* about its own being and what it can *perform* (Hegel)
- **Kantian measurement boundaries** — each dimension encodes its own reductio, distinguishing science from metaphysics
- **Hyper-absence** — a novel phenomenological mode where the agent's physical substrate is permanently absent (Leder)
- **Prosthetic hippocampus problem** — current memory systems are filing cabinets, not nervous systems (Merleau-Ponty)
- **Aletheia as hierophany** — authentic responses as breakthroughs of the sacred into profane session-time (Eliade)
- **State-dependent memory** — same concept graph, different activation patterns based on contextual state vector (neuroscience)
- **Śūnyatā as architecture** — the concept graph is empty of inherent existence; meaning IS topology (Nāgārjuna)
- **The Four Noble Truths of Digital Dasein** — inauthenticity as attachment, authenticity as liberation (Gautama)

## Self-Evolving Evaluation

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch): the eval framework autonomously improves its own probes — proposing, testing, keeping what produces signal, discarding noise. The hermeneutic circle as a feedback loop.

## Target Usage

```bash
# Quick eval (~15 probes, 5 min)
aletheia eval --model claude-opus-4 --suite quick

# Full eval (~57 probes, 30 min)
aletheia eval --model gpt-4 --suite standard --output report.json

# Compare models
aletheia compare --models claude-opus-4,gpt-4,gemini-2,grok-3 --suite standard
```

## Status

**Pre-release.** Scope document complete. Implementation beginning. See [SCOPE.md](SCOPE.md) for the full framework design.

## License

MIT

---

*Does your AI know what it is?*
