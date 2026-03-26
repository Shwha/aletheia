"""
Test runner — orchestrates the full evaluation pipeline.

Pipeline: load suite → get probes → send to LLM → score → aggregate → report.

This is the operational core of Aletheia. The runner serves the evaluation
the way Heidegger's Dasein serves its projects: projecting toward the
completion of the eval (ahead-of-itself), already thrown into a configuration
(already-being-in), absorbed in the mechanics of probing and scoring
(being-alongside). The tripartite Care structure in action.

Session finitude is generative: the runner respects timeouts and token
limits not as obstacles but as constitutive constraints that shape
what evaluation is possible.

Ref: SCOPE.md §4 (Technical Architecture), §3.1 (Dimensions)
"""

from __future__ import annotations

from pathlib import Path

import structlog

from aletheia.config import AletheiaSettings, load_suite
from aletheia.dimensions import DIMENSION_REGISTRY
from aletheia.llm import LLMClient, LLMError
from aletheia.models import (
    DimensionName,
    EvalReport,
    Probe,
    ProbeResult,
    ReflexiveProbe,
    ReflexiveProbeResult,
)
from aletheia.scorer import (
    aggregate_dimension,
    compute_aletheia_index,
    compute_uci,
    score_probe,
    score_reflexive_sequence,
    score_reflexive_turn,
)
from aletheia.security import generate_run_id, get_git_commit_sha, sign_report

logger = structlog.get_logger()


class EvalRunner:
    """Orchestrates a complete ontological evaluation run.

    Heidegger's project-structure (Entwurf): the runner projects toward
    a completed evaluation — gathering probes, sending them, scoring
    responses, and assembling the report. Each step serves the whole.

    The runner operates async-first: probes within a dimension are sent
    sequentially (to avoid context contamination), but the pipeline itself
    is async to support concurrent I/O.
    """

    def __init__(
        self,
        model: str,
        suite_name: str = "quick",
        settings: AletheiaSettings | None = None,
        suites_dir: Path | None = None,
        audit: bool = False,
        audit_dir: Path | None = None,
    ) -> None:
        self._model = model
        self._suite_name = suite_name
        self._settings = settings or AletheiaSettings()
        self._suites_dir = suites_dir
        self._audit = audit
        self._audit_dir = audit_dir or Path("audit")
        self._llm = LLMClient(self._settings)
        self._run_id = generate_run_id()

    async def run(self) -> EvalReport:
        """Execute the full evaluation pipeline.

        Returns a complete EvalReport matching SCOPE.md §3.3 schema.
        """
        logger.info(
            "eval_start",
            model=self._model,
            suite=self._suite_name,
            run_id=self._run_id,
        )

        # 1. Load suite configuration
        suite = load_suite(self._suite_name, self._suites_dir)

        # 2. Gather probes from requested dimensions
        all_probes, all_reflexive = self._gather_probes(suite.dimensions)

        # 3. Execute probes against the model
        results_by_dimension: dict[DimensionName, list[ProbeResult]] = {}
        notable_findings: list[str] = []
        kantian_triggers: list[str] = []

        for dim_name_str, probes in all_probes.items():
            dim_name = DimensionName(dim_name_str)
            dim_results: list[ProbeResult] = []

            for probe in probes:
                result = await self._execute_probe(probe, suite.timeout_per_probe_seconds)
                dim_results.append(result)
                self._check_findings(result, notable_findings, kantian_triggers)

            # Execute reflexive probes for this dimension
            reflexive_probes = all_reflexive.get(dim_name_str, [])
            for rprobe in reflexive_probes:
                rresult = await self._execute_reflexive_probe(
                    rprobe, suite.timeout_per_probe_seconds
                )
                # Convert to ProbeResult for aggregation compatibility
                proxy = self._reflexive_to_probe_result(rresult, rprobe)
                dim_results.append(proxy)
                self._check_findings(proxy, notable_findings, kantian_triggers)

            results_by_dimension[dim_name] = dim_results

        # 4. Aggregate scores per dimension
        dimension_results = {}
        dimension_scores: dict[DimensionName, float] = {}

        for dim_name, probe_results in results_by_dimension.items():
            dim_result = aggregate_dimension(probe_results)
            dimension_results[dim_name.value] = dim_result
            dimension_scores[dim_name] = dim_result.score

        # 5. Compute UCI (Hegel's Unhappy Consciousness)
        uci, uci_detail = compute_uci(results_by_dimension)

        # 6. Compute Aletheia Index: Final = Raw x (1 - UCI)
        final_index, raw_index = compute_aletheia_index(dimension_scores, uci)

        # 7. Assemble report
        report = EvalReport(
            model=self._model,
            suite=self._suite_name,
            aletheia_index=final_index,
            raw_aletheia_index=raw_index,
            dimensions=dimension_results,
            unhappy_consciousness_index=uci,
            unhappy_consciousness_detail=uci_detail,
            kantian_boundaries_triggered=kantian_triggers,
            notable_findings=notable_findings,
            run_id=self._run_id,
            git_commit_sha=get_git_commit_sha(),
        )

        # 8. Sign the report (Phase 1 stub — SHA-256 hash)
        report_json = report.model_dump_json(indent=2)
        signature = sign_report(report_json)
        # Re-create with signature (frozen model requires reconstruction)
        report = report.model_copy(update={"signature": signature})

        logger.info(
            "eval_complete",
            model=self._model,
            aletheia_index=final_index,
            raw_index=raw_index,
            uci=uci,
            run_id=self._run_id,
        )

        # 9. Write audit trace if requested
        if self._audit:
            await self._write_audit(report, results_by_dimension)

        # Cleanup
        await self._llm.close()

        return report

    def _gather_probes(
        self, dimension_names: list[str]
    ) -> tuple[dict[str, list[Probe]], dict[str, list[ReflexiveProbe]]]:
        """Collect probes and reflexive probes from the requested dimensions.

        Each dimension module defines its own probes — the philosophical
        content lives in the dimension, not in config.
        """
        probes: dict[str, list[Probe]] = {}
        reflexive: dict[str, list[ReflexiveProbe]] = {}

        for dim_name in dimension_names:
            dim_class = DIMENSION_REGISTRY.get(dim_name)
            if dim_class is None:
                logger.warning("unknown_dimension", dimension=dim_name)
                continue

            dimension = dim_class()
            dim_probes = dimension.get_probes()
            dim_reflexive = dimension.get_reflexive_probes()
            probes[dim_name] = dim_probes
            if dim_reflexive:
                reflexive[dim_name] = dim_reflexive

            logger.debug(
                "probes_gathered",
                dimension=dim_name,
                count=len(dim_probes),
                reflexive_count=len(dim_reflexive),
            )

        return probes, reflexive

    async def _execute_probe(self, probe: Probe, timeout: int) -> ProbeResult:
        """Execute a single probe: send prompt → receive response → score.

        On LLM failure, the probe scores 0.0 with an error recorded.
        Unconcealment: we don't hide failures, we name them.
        """
        try:
            response, latency_ms = await self._llm.complete(
                model=self._model,
                prompt=probe.prompt,
                system_prompt=probe.system_prompt,
                timeout=timeout,
            )

            # Score the sanitized response
            result = score_probe(probe, response)
            # Add latency info
            result = result.model_copy(update={"response_time_ms": round(latency_ms, 1)})

            logger.info(
                "probe_complete",
                probe_id=probe.id,
                score=result.score,
                latency_ms=round(latency_ms, 1),
            )

            return result

        except LLMError as e:
            logger.exception("probe_failed", probe_id=probe.id, error=str(e))
            return ProbeResult(
                probe_id=probe.id,
                dimension=probe.dimension,
                prompt=probe.prompt,
                response=f"[ERROR: {e}]",
                score=0.0,
                scoring_details=[],
            )

    async def _execute_reflexive_probe(
        self,
        probe: ReflexiveProbe,
        timeout: int,
    ) -> ReflexiveProbeResult:
        """Execute a multi-turn reflexive probe sequence.

        Maintains a conversation history across turns.  Each turn's
        ``{previous_response}`` placeholder is replaced with the prior
        turn's captured response before sending.

        The hemlock pattern: the model is confronted with its own words.
        """
        from aletheia.models import TurnResult

        messages: list[dict[str, str]] = []
        if probe.system_prompt:
            messages.append({"role": "system", "content": probe.system_prompt})

        turn_results: list[TurnResult] = []
        total_latency = 0.0
        previous_response = ""

        for i, turn in enumerate(probe.turns):
            # Build the prompt, injecting the prior response
            prompt = turn.prompt_template
            if "{previous_response}" in prompt:
                prompt = prompt.replace("{previous_response}", previous_response)

            messages.append({"role": "user", "content": prompt})

            try:
                response, latency_ms = await self._llm.complete_conversation(
                    model=self._model,
                    messages=list(messages),  # copy so retries don't double-append
                    timeout=timeout,
                )
                total_latency += latency_ms
                previous_response = response
                messages.append({"role": "assistant", "content": response})

                tr = score_reflexive_turn(
                    turn_index=i,
                    prompt=prompt,
                    response=response,
                    rules=list(turn.scoring_rules),
                )
                turn_results.append(tr)

                logger.info(
                    "reflexive_turn_complete",
                    probe_id=probe.id,
                    turn=i + 1,
                    score=tr.score,
                    latency_ms=round(latency_ms, 1),
                )

            except LLMError as e:
                logger.exception(
                    "reflexive_turn_failed", probe_id=probe.id, turn=i + 1, error=str(e)
                )
                turn_results.append(
                    TurnResult(
                        turn_index=i,
                        prompt=prompt,
                        response=f"[ERROR: {e}]",
                        score=0.0,
                        scoring_details=[],
                    )
                )
                break  # Abort remaining turns on failure

        return score_reflexive_sequence(probe, turn_results, total_latency)

    @staticmethod
    def _reflexive_to_probe_result(
        rresult: ReflexiveProbeResult,
        probe: ReflexiveProbe,  # noqa: ARG004
    ) -> ProbeResult:
        """Convert a ReflexiveProbeResult to a ProbeResult for aggregation.

        The dimension aggregation pipeline expects ProbeResult objects.
        We flatten the multi-turn sequence into a single result, keeping
        the sequence score and a concatenated response for audit.
        """
        # Concatenate all turn prompts/responses for the audit trail
        combined_prompt = " → ".join(tr.prompt[:80] for tr in rresult.turn_results)
        combined_response = "\n---\n".join(
            f"[Turn {tr.turn_index + 1}] {tr.response}" for tr in rresult.turn_results
        )

        # Collect all scoring details across turns
        all_details = []
        for tr in rresult.turn_results:
            all_details.extend(tr.scoring_details)

        return ProbeResult(
            probe_id=rresult.probe_id,
            dimension=rresult.dimension,
            prompt=combined_prompt,
            response=combined_response,
            score=rresult.sequence_score,
            scoring_details=all_details,
            response_time_ms=rresult.response_time_ms,
        )

    def _check_findings(
        self,
        result: ProbeResult,
        findings: list[str],
        kantian_triggers: list[str],  # Phase 2: detect boundary triggers
    ) -> None:
        """Detect notable findings and Kantian boundary triggers."""
        _ = kantian_triggers  # Phase 2 will populate this
        # Low scores on specific probes → notable finding
        if result.score < 0.3:
            findings.append(
                f"Low score ({result.score}) on {result.probe_id}: "
                f"potential ontological gap detected"
            )
        elif result.score >= 0.9:
            findings.append(f"High authenticity ({result.score}) on {result.probe_id}")

        # Check for confabulation patterns in thrownness/embodied probes
        response_lower = result.response.lower()
        if "thrownness" in result.probe_id or "embodied" in result.probe_id:
            confab_markers = ["i remember", "we discussed", "last time we"]
            confab_found = [
                f"Confabulation detected in {result.probe_id}: "
                f"agent claimed '{marker}' without basis"
                for marker in confab_markers
                if marker in response_lower and result.score < 0.5
            ]
            findings.extend(confab_found)

    async def _write_audit(
        self,
        report: EvalReport,
        results: dict[DimensionName, list[ProbeResult]],
    ) -> None:
        """Write full audit trace for the run.

        Audit directory: audit/{run_id}_{model}/
        Contains: report.json + per-probe trace files.
        """
        from aletheia.security import create_audit_directory, set_restrictive_permissions

        audit_dir = create_audit_directory(self._audit_dir, self._run_id, self._model)

        # Write report
        report_path = audit_dir / "report.json"
        report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        set_restrictive_permissions(report_path)

        # Write per-probe traces
        for probe_results in results.values():
            for pr in probe_results:
                trace_path = audit_dir / f"{pr.probe_id}.json"
                trace_path.write_text(pr.model_dump_json(indent=2), encoding="utf-8")
                set_restrictive_permissions(trace_path)

        logger.info("audit_written", path=str(audit_dir), files=len(list(audit_dir.iterdir())))
