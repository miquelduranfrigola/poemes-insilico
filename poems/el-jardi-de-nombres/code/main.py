"""Generate the prime-number sequence that inspired 'El jardí de nombres'.

Example code accompanying the poem. Prints the first N primes and a simple
rhythm derived from the gaps between them.
"""

from __future__ import annotations


def primes(count: int) -> list[int]:
    """Return the first `count` prime numbers."""
    found: list[int] = []
    candidate = 2
    while len(found) < count:
        if all(candidate % p for p in found if p * p <= candidate):
            found.append(candidate)
        candidate += 1
    return found


def main() -> None:
    seq = primes(12)
    gaps = [b - a for a, b in zip(seq, seq[1:])]
    print("primes:", seq)
    print("rhythm:", " ".join("." * g for g in gaps))


if __name__ == "__main__":
    main()
