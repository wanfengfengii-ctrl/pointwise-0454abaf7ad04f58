from collections import defaultdict, deque
from dataclasses import dataclass

from compare.witness import ordered_public_codes
from issue.evidence import PublicEvidence


@dataclass(frozen=True, slots=True)
class DirectionalDifferences:
    left_only: tuple[str, ...] | None
    right_only: tuple[str, ...] | None


StateSet = frozenset[int]


def _edge_index(evidence: PublicEvidence) -> dict[tuple[int, str], list[int]]:
    edges = defaultdict(list)
    for source, code, target in evidence.transitions:
        edges[source, code].append(target)
    return edges


def _advance(
    edges: dict[tuple[int, str], list[int]], states: StateSet, code: str
) -> StateSet:
    targets: set[int] = set()
    for state in states:
        targets.update(edges.get((state, code), ()))
    return frozenset(targets)


def _complete(states: StateSet, accepting: frozenset[int]) -> bool:
    return bool(states & accepting)


def find_distinctions(left: PublicEvidence, right: PublicEvidence) -> DirectionalDifferences:
    """Shortest record supported by exactly one frozen revision in each direction.

    A record is supported by a side only when some path from the start state
    consumes it and finishes in an accepting state.  Paths that merely remain
    alive are not support, so the search tracks the whole set of states a
    record can reach on each side.  Breadth-first traversal over equal-length
    records in action-code order yields the shortest witness, ties broken
    lexicographically by action code.  ``None`` means the direction has no
    exclusive record; ``()`` means the empty record is exclusive.
    """
    left_edges, right_edges = _edge_index(left), _edge_index(right)
    left_finals, right_finals = frozenset(left.accepting), frozenset(right.accepting)
    codes = ordered_public_codes(left.codes, right.codes)
    start = (frozenset({left.start}), frozenset({right.start}))
    pending = deque([(start, ())])
    seen = {start}
    left_only = right_only = None
    while pending:
        (left_states, right_states), record = pending.popleft()
        if left_only is None and _complete(left_states, left_finals) and not _complete(
            right_states, right_finals
        ):
            left_only = record
        if right_only is None and _complete(right_states, right_finals) and not _complete(
            left_states, left_finals
        ):
            right_only = record
        if left_only is not None and right_only is not None:
            break
        for code in codes:
            successor = (
                _advance(left_edges, left_states, code),
                _advance(right_edges, right_states, code),
            )
            if (successor[0] or successor[1]) and successor not in seen:
                seen.add(successor)
                pending.append((successor, record + (code,)))
    return DirectionalDifferences(left_only, right_only)
