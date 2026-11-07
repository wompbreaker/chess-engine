"""Attack generation.

Leaper attacks (pawn, knight, king) are fully precomputed and depend only on the
square. Slider attacks depend on the occupancy, and are computed here with the
*classical* approach: walk the ray, find the first blocker, and mask off everything
beyond it.

This is slow but transparently correct, and it is what gets perft green. Magic
bitboards replace :func:`rook_attacks` and :func:`bishop_attacks` later behind exactly
these signatures, validated by diffing against this implementation.
"""

from typing import Final

from .bitboard import (
    BISHOP_DIRECTIONS,
    POSITIVE_DIRECTIONS,
    RAY_BB,
    ROOK_DIRECTIONS,
    SQUARE_BB,
    north_east,
    north_west,
    south_east,
    south_west,
)
from .types import (
    BISHOP,
    KING,
    KNIGHT,
    PAWN,
    QUEEN,
    ROOK,
    SQUARE_NB,
    WHITE,
    Bitboard,
    Color,
    PieceType,
    Square,
)

# --- Leapers --------------------------------------------------------------

_KNIGHT_STEPS: Final = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
_KING_STEPS: Final = ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))


def _step_table(steps: tuple[tuple[int, int], ...]) -> tuple[Bitboard, ...]:
    table = []
    for square in range(SQUARE_NB):
        bb = 0
        file, rank = square & 7, square >> 3
        for file_step, rank_step in steps:
            to_file, to_rank = file + file_step, rank + rank_step
            if 0 <= to_file < 8 and 0 <= to_rank < 8:
                bb |= 1 << (to_rank * 8 + to_file)
        table.append(bb)
    return tuple(table)


KNIGHT_ATTACKS: Final[tuple[Bitboard, ...]] = _step_table(_KNIGHT_STEPS)
KING_ATTACKS: Final[tuple[Bitboard, ...]] = _step_table(_KING_STEPS)

#: ``PAWN_ATTACKS[color][square]`` — squares a pawn of that colour attacks.
PAWN_ATTACKS: Final[tuple[tuple[Bitboard, ...], ...]] = (
    tuple(north_east(SQUARE_BB[sq]) | north_west(SQUARE_BB[sq]) for sq in range(SQUARE_NB)),
    tuple(south_east(SQUARE_BB[sq]) | south_west(SQUARE_BB[sq]) for sq in range(SQUARE_NB)),
)


def pawn_attacks_bb(color: Color, pawns: Bitboard) -> Bitboard:
    """Squares attacked by a whole set of pawns at once."""
    if color == WHITE:
        return north_east(pawns) | north_west(pawns)
    return south_east(pawns) | south_west(pawns)


# --- Sliders --------------------------------------------------------------


def _ray_attacks(direction: int, square: Square, occupied: Bitboard) -> Bitboard:
    attacks = RAY_BB[direction][square]
    blockers = attacks & occupied
    if blockers:
        # Towards higher indices the nearest blocker is the lowest set bit, and vice versa.
        if direction in POSITIVE_DIRECTIONS:
            nearest = (blockers & -blockers).bit_length() - 1
        else:
            nearest = blockers.bit_length() - 1
        attacks &= ~RAY_BB[direction][nearest]
    return attacks


def rook_attacks(square: Square, occupied: Bitboard) -> Bitboard:
    return (
        _ray_attacks(ROOK_DIRECTIONS[0], square, occupied)
        | _ray_attacks(ROOK_DIRECTIONS[1], square, occupied)
        | _ray_attacks(ROOK_DIRECTIONS[2], square, occupied)
        | _ray_attacks(ROOK_DIRECTIONS[3], square, occupied)
    )


def bishop_attacks(square: Square, occupied: Bitboard) -> Bitboard:
    return (
        _ray_attacks(BISHOP_DIRECTIONS[0], square, occupied)
        | _ray_attacks(BISHOP_DIRECTIONS[1], square, occupied)
        | _ray_attacks(BISHOP_DIRECTIONS[2], square, occupied)
        | _ray_attacks(BISHOP_DIRECTIONS[3], square, occupied)
    )


def queen_attacks(square: Square, occupied: Bitboard) -> Bitboard:
    return rook_attacks(square, occupied) | bishop_attacks(square, occupied)


def attacks_of(piece_type: PieceType, square: Square, occupied: Bitboard) -> Bitboard:
    """Attacks for any non-pawn piece type."""
    if piece_type == KNIGHT:
        return KNIGHT_ATTACKS[square]
    if piece_type == BISHOP:
        return bishop_attacks(square, occupied)
    if piece_type == ROOK:
        return rook_attacks(square, occupied)
    if piece_type == QUEEN:
        return queen_attacks(square, occupied)
    if piece_type == KING:
        return KING_ATTACKS[square]
    raise ValueError(f"attacks_of does not handle piece type {piece_type} (pawns are {PAWN})")
