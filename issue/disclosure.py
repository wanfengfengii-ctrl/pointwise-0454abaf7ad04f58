from collections import deque

from issue.evidence import PublicEvidence
from recipes.revisions import Revision
from recipes.topology import StepEdge


def _hidden_closure(step: str, outgoing: dict[str, list[StepEdge]]) -> frozenset[str]:
    """Every step reachable from ``step`` by zero or more hidden transitions."""
    closure = set()
    pending = [step]
    while pending:
        current = pending.pop()
        if current in closure:
            continue
        closure.add(current)
        for edge in outgoing[current]:
            if edge.code is None and edge.target not in closure:
                pending.append(edge.target)
    return frozenset(closure)


def build_public_evidence(revision: Revision) -> PublicEvidence:
    """Determinize the non-hidden behaviour of ``revision`` exactly.

    Hidden transitions are collapsed into their closure.  A public state is a
    set of internal steps that can be reached without consuming a public
    action, so branches through hidden steps, repeated action codes and
    hidden cycles are all preserved.  The resulting automaton accepts exactly
    the records that have a complete path in the revision.
    """
    graph = revision.graph
    outgoing = graph.outgoing()
    accepting = graph.accepting
    closures = {step: _hidden_closure(step, outgoing) for step in graph.steps}

    def close(subset: frozenset[str]) -> frozenset[str]:
        result: set[str] = set()
        for step in subset:
            result.update(closures[step])
        return frozenset(result)

    def advance(states: frozenset[str], code: str) -> frozenset[str]:
        targets: set[str] = set()
        for step in states:
            for edge in outgoing[step]:
                if edge.code == code:
                    targets.update(closures[edge.target])
        return frozenset(targets)

    codes = revision.catalog.codes
    start = close(frozenset({graph.start}))
    public_id = {start: 0}
    pending = deque([start])
    accepting_ids: list[int] = []
    transitions: list[tuple[int, str, int]] = []
    while pending:
        states = pending.popleft()
        source_id = public_id[states]
        if states & accepting:
            accepting_ids.append(source_id)
        for code in codes:
            target = advance(states, code)
            if not target:
                continue
            if target not in public_id:
                public_id[target] = len(public_id)
                pending.append(target)
            transitions.append((source_id, code, public_id[target]))
    return PublicEvidence(
        codes, len(public_id), 0, tuple(accepting_ids), tuple(transitions)
    )
