from collections import deque

from issue.evidence import PublicEvidence
from recipes.revisions import Revision
from recipes.topology import StepEdge


def _resume_step(
    step: str, outgoing: dict[str, list[StepEdge]], accepting: frozenset[str]
) -> str:
    visited = set()
    while step not in visited:
        visited.add(step)
        edges = outgoing[step]
        if step in accepting or any(edge.code is not None for edge in edges):
            return step
        handoff = next((edge.target for edge in edges if edge.code is None), None)
        if handoff is None:
            return step
        step = handoff
    return step


def build_public_evidence(revision: Revision) -> PublicEvidence:
    graph = revision.graph
    outgoing = graph.outgoing()
    order = {step: position for position, step in enumerate(graph.steps)}
    start = _resume_step(graph.start, outgoing, graph.accepting)
    public_id = {start: 0}
    pending = deque([start])
    accepting = []
    transitions = []
    while pending:
        step = pending.popleft()
        source_id = public_id[step]
        if step in graph.accepting:
            accepting.append(source_id)
        choices = {
            (edge.code, _resume_step(edge.target, outgoing, graph.accepting))
            for edge in outgoing[step]
            if edge.code is not None
        }
        for code, target in sorted(choices, key=lambda choice: (choice[0], order[choice[1]])):
            if target not in public_id:
                public_id[target] = len(public_id)
                pending.append(target)
            transitions.append((source_id, code, public_id[target]))
    return PublicEvidence(
        revision.catalog.codes, len(public_id), 0, tuple(accepting), tuple(transitions)
    )
