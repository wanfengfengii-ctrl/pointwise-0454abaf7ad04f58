from collections import defaultdict, deque
from dataclasses import dataclass
from itertools import product

from compare.witness import ordered_public_codes
from issue.evidence import PublicEvidence


@dataclass(frozen=True, slots=True)
class DirectionalDifferences:
    left_only: tuple[str, ...] | None
    right_only: tuple[str, ...] | None


def _edge_index(evidence: PublicEvidence) -> dict[tuple[int | None, str], list[int]]:
    edges = defaultdict(list)
    for source, code, target in evidence.transitions:
        edges[source, code].append(target)
    return edges


def find_distinctions(left: PublicEvidence, right: PublicEvidence) -> DirectionalDifferences:
    left_edges, right_edges = _edge_index(left), _edge_index(right)
    left_finals, right_finals = set(left.accepting), set(right.accepting)
    codes = ordered_public_codes(left.codes, right.codes)
    start = (left.start, right.start)
    pending = deque([(start, ())])
    seen = {start}
    left_only = right_only = None
    while pending:
        (left_state, right_state), record = pending.popleft()
        if left_only is None and left_state in left_finals and right_state is None:
            left_only = record
        if right_only is None and right_state in right_finals and left_state is None:
            right_only = record
        if left_only is not None and right_only is not None:
            break
        for code in codes:
            left_targets = left_edges.get((left_state, code)) or (None,)
            right_targets = right_edges.get((right_state, code)) or (None,)
            for successor in product(left_targets, right_targets):
                if successor != (None, None) and successor not in seen:
                    seen.add(successor)
                    pending.append((successor, record + (code,)))
    return DirectionalDifferences(left_only, right_only)
