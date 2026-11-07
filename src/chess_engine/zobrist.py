"""Zobrist hashing keys.

The seed is fixed so that keys are identical across runs, which keeps perft, bench and
transposition-table behaviour reproducible.
"""

import random
from typing import Final

from .types import CASTLING_NB, FILE_NB, PIECE_NB, SQUARE_NB

_SEED: Final = 0x5EED_C4E5_5B0A_12D3

_rng = random.Random(_SEED)


def _random_key() -> int:
    return _rng.getrandbits(64)


#: ``PIECE_SQUARE[piece][square]``. The NO_PIECE row is never used but keeps indexing simple.
PIECE_SQUARE: Final[tuple[tuple[int, ...], ...]] = tuple(
    tuple(_random_key() for _ in range(SQUARE_NB)) for _ in range(PIECE_NB)
)

#: Indexed by the full 4-bit castling rights mask, so updates are a single xor.
CASTLING: Final[tuple[int, ...]] = tuple(_random_key() for _ in range(CASTLING_NB))

#: Keyed by file only: the rank is implied by the side to move.
EN_PASSANT: Final[tuple[int, ...]] = tuple(_random_key() for _ in range(FILE_NB))

SIDE_TO_MOVE: Final[int] = _random_key()
