"""Bitboard primitives and precomputed geometry tables.

A bitboard is a plain Python ``int`` used as a 64-bit set of squares, bit ``i``
standing for square ``i`` in LERF order.

Python integers are arbitrary-precision and signed, so there is no native uint64.
Every left shift must be masked with :data:`U64_MASK` or bits escape past bit 63 and
quietly corrupt later results. Use :func:`shl` rather than a bare ``<<``.
"""

from typing import Final

from .types import SQUARE_NB, Bitboard, Square

U64_MASK: Final = 0xFFFF_FFFF_FFFF_FFFF

EMPTY: Final[Bitboard] = 0
FULL: Final[Bitboard] = U64_MASK


def shl(bitboard: Bitboard, n: int) -> Bitboard:
    """Left shift, truncated to 64 bits."""
    return (bitboard << n) & U64_MASK


def shr(bitboard: Bitboard, n: int) -> Bitboard:
    """Right shift, truncated to 64 bits."""
    return bitboard >> n


def square_bb(square: Square) -> Bitboard:
    """Bitboard with only ``square`` set."""
    return 1 << square


def test_bit(bitboard: Bitboard, square: Square) -> bool:
    """True if ``square`` is set in ``bitboard``."""
    return bitboard & (1 << square) != 0


def popcount(bitboard: Bitboard) -> int:
    """Number of squares set in ``bitboard``."""
    return bitboard.bit_count()


def lsb(bitboard: Bitboard) -> Square:
    """Index of the least significant set bit. Undefined for an empty bitboard."""
    return (bitboard & -bitboard).bit_length() - 1


def msb(bitboard: Bitboard) -> Square:
    """Index of the most significant set bit. Undefined for an empty bitboard."""
    return bitboard.bit_length() - 1


def pop_lsb(bitboard: Bitboard) -> tuple[Square, Bitboard]:
    """Return the least significant square and the bitboard with that bit cleared."""
    low = bitboard & -bitboard
    return low.bit_length() - 1, bitboard ^ low


def scan_bits(bitboard: Bitboard) -> list[Square]:
    """Squares set in ``bitboard``, in ascending order."""
    squares = []
    while bitboard:
        low = bitboard & -bitboard
        squares.append(low.bit_length() - 1)
        bitboard ^= low
    return squares


def more_than_one(bitboard: Bitboard) -> bool:
    """True if more than one square is set in ``bitboard``."""
    return bitboard & (bitboard - 1) != 0


# --- File and rank masks --------------------------------------------------

FILE_BB: Final[tuple[Bitboard, ...]] = tuple(0x0101_0101_0101_0101 << file for file in range(8))
RANK_BB: Final[tuple[Bitboard, ...]] = tuple(0xFF << (8 * rank) for rank in range(8))

FILE_A_BB: Final[Bitboard] = FILE_BB[0]
FILE_B_BB: Final[Bitboard] = FILE_BB[1]
FILE_G_BB: Final[Bitboard] = FILE_BB[6]
FILE_H_BB: Final[Bitboard] = FILE_BB[7]

NOT_FILE_A: Final[Bitboard] = ~FILE_A_BB & U64_MASK
NOT_FILE_H: Final[Bitboard] = ~FILE_H_BB & U64_MASK
NOT_FILE_AB: Final[Bitboard] = ~(FILE_A_BB | FILE_B_BB) & U64_MASK
NOT_FILE_GH: Final[Bitboard] = ~(FILE_G_BB | FILE_H_BB) & U64_MASK

LIGHT_SQUARES: Final[Bitboard] = 0x55AA_55AA_55AA_55AA
DARK_SQUARES: Final[Bitboard] = 0xAA55_AA55_AA55_AA55

SQUARE_BB: Final[tuple[Bitboard, ...]] = tuple(1 << sq for sq in range(SQUARE_NB))


# --- Single-step shifts ---------------------------------------------------
# Each masks off the file that would otherwise wrap around the board edge.


def north(bitboard: Bitboard) -> Bitboard:
    """Shift bitboard one rank north.

    This truncates to 64 bits."""
    return (bitboard << 8) & U64_MASK


def south(bitboard: Bitboard) -> Bitboard:
    """Shift bitboard one rank south.

    This truncates to 64 bits."""
    return bitboard >> 8


def east(bitboard: Bitboard) -> Bitboard:
    """Shift bitboard one file east.

    This truncates to 64 bits and masks off the H file."""
    return (bitboard & NOT_FILE_H) << 1


def west(bitboard: Bitboard) -> Bitboard:
    """Shift bitboard one file west.

    This truncates to 64 bits and masks off the A file."""
    return (bitboard & NOT_FILE_A) >> 1


def north_east(bitboard: Bitboard) -> Bitboard:
    """Shift bitboard one rank north and one file east.

    This truncates to 64 bits and masks off the H file."""
    return ((bitboard & NOT_FILE_H) << 9) & U64_MASK


def north_west(bitboard: Bitboard) -> Bitboard:
    """Shift bitboard one rank north and one file west.

    This truncates to 64 bits and masks off the A file."""
    return ((bitboard & NOT_FILE_A) << 7) & U64_MASK


def south_east(bitboard: Bitboard) -> Bitboard:
    """Shift bitboard one rank south and one file east.

    This truncates to 64 bits and masks off the H file."""
    return (bitboard & NOT_FILE_H) >> 7


def south_west(bitboard: Bitboard) -> Bitboard:
    """Shift bitboard one rank south and one file west.

    This truncates to 64 bits and masks off the A file."""
    return (bitboard & NOT_FILE_A) >> 9


# --- Ray geometry ---------------------------------------------------------

NORTH: Final = 0
NORTH_EAST: Final = 1
EAST: Final = 2
SOUTH_EAST: Final = 3
SOUTH: Final = 4
SOUTH_WEST: Final = 5
WEST: Final = 6
NORTH_WEST: Final = 7

DIRECTION_NB: Final = 8

# (file step, rank step) per direction index.
_DIRECTION_STEPS: Final = (
    (0, 1),
    (1, 1),
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, -1),
    (-1, 0),
    (-1, 1),
)

ROOK_DIRECTIONS: Final = (NORTH, EAST, SOUTH, WEST)
BISHOP_DIRECTIONS: Final = (NORTH_EAST, SOUTH_EAST, SOUTH_WEST, NORTH_WEST)

# Directions whose rays run towards higher square indices. Needed by the classical
# slider attack code, which must pick msb vs lsb when finding the first blocker.
POSITIVE_DIRECTIONS: Final = frozenset({NORTH, NORTH_EAST, EAST, NORTH_WEST})


def _build_rays() -> tuple[tuple[Bitboard, ...], ...]:
    rays = []
    for direction in range(DIRECTION_NB):
        file_step, rank_step = _DIRECTION_STEPS[direction]
        per_square = []
        for square in range(SQUARE_NB):
            bitboard = EMPTY
            file = (square & 7) + file_step
            rank = (square >> 3) + rank_step
            while 0 <= file < 8 and 0 <= rank < 8:
                bitboard |= 1 << (rank * 8 + file)
                file += file_step
                rank += rank_step
            per_square.append(bitboard)
        rays.append(tuple(per_square))
    return tuple(rays)


RAY_BB: Final[tuple[tuple[Bitboard, ...], ...]] = _build_rays()


def _build_lines() -> tuple[tuple[tuple[Bitboard, ...], ...], tuple[tuple[Bitboard, ...], ...]]:
    between: list[tuple[Bitboard, ...]] = []
    line: list[tuple[Bitboard, ...]] = []
    for a in range(SQUARE_NB):
        between_row = [EMPTY] * SQUARE_NB
        line_row = [EMPTY] * SQUARE_NB
        for direction in range(DIRECTION_NB):
            ray = RAY_BB[direction][a]
            opposite_ray = RAY_BB[direction ^ 4][a]
            walk = ray
            while walk:
                b, walk = pop_lsb(walk)
                # Squares strictly between a and b: the part of a's ray that stops at b.
                between_row[b] = ray & ~RAY_BB[direction][b] & ~SQUARE_BB[b]
                line_row[b] = ray | opposite_ray | SQUARE_BB[a]
        between.append(tuple(between_row))
        line.append(tuple(line_row))
    return tuple(between), tuple(line)


_BETWEEN, _LINE = _build_lines()

#: Squares strictly between ``a`` and ``b`` when they share a rank, file or diagonal,
#: and empty otherwise.
BETWEEN_BB: Final[tuple[tuple[Bitboard, ...], ...]] = _BETWEEN
#: The whole line through ``a`` and ``b``, including both endpoints, or empty if they
#: are not aligned.
LINE_BB: Final[tuple[tuple[Bitboard, ...], ...]] = _LINE


def aligned(a: Square, b: Square, c: Square) -> bool:
    """True if all three squares lie on one rank, file or diagonal."""
    return LINE_BB[a][b] & SQUARE_BB[c] != 0


# --- Pawn structure and king zone masks -----------------------------------

ADJACENT_FILES_BB: Final[tuple[Bitboard, ...]] = tuple(
    (FILE_BB[file - 1] if file > 0 else EMPTY) | (FILE_BB[file + 1] if file < 7 else EMPTY)
    for file in range(8)
)


def _forward_ranks(color: int, rank: int) -> Bitboard:
    """All ranks strictly ahead of ``rank`` from ``color``'s point of view."""
    if color == 0:
        return sum(RANK_BB[r] for r in range(rank + 1, 8))
    return sum(RANK_BB[r] for r in range(0, rank))


FORWARD_RANKS_BB: Final[tuple[tuple[Bitboard, ...], ...]] = tuple(
    tuple(_forward_ranks(color, square >> 3) for square in range(SQUARE_NB)) for color in range(2)
)

#: Squares a pawn on this square must cross, plus the adjacent files, to be passed.
PASSED_PAWN_MASK: Final[tuple[tuple[Bitboard, ...], ...]] = tuple(
    tuple(
        FORWARD_RANKS_BB[color][square] & (FILE_BB[square & 7] | ADJACENT_FILES_BB[square & 7])
        for square in range(SQUARE_NB)
    )
    for color in range(2)
)

#: The file in front of a pawn, used for doubled-pawn and open-file detection.
FORWARD_FILE_BB: Final[tuple[tuple[Bitboard, ...], ...]] = tuple(
    tuple(FORWARD_RANKS_BB[color][square] & FILE_BB[square & 7] for square in range(SQUARE_NB))
    for color in range(2)
)

ISOLATED_PAWN_MASK: Final[tuple[Bitboard, ...]] = tuple(
    ADJACENT_FILES_BB[square & 7] for square in range(SQUARE_NB)
)


def _king_zone(square: Square) -> Bitboard:
    bitboard = SQUARE_BB[square]
    ring = north(bitboard) | south(bitboard) | east(bitboard) | west(bitboard)
    ring |= (
        north_east(bitboard) | north_west(bitboard) | south_east(bitboard) | south_west(bitboard)
    )
    return ring | bitboard


KING_ZONE_BB: Final[tuple[Bitboard, ...]] = tuple(_king_zone(square) for square in range(SQUARE_NB))


# --- Debugging ------------------------------------------------------------


def format_bb(bitboard: Bitboard) -> str:
    """Render a bitboard as an 8x8 grid with rank 8 at the top."""
    lines = []
    for rank in range(7, -1, -1):
        row = "".join("X" if bitboard & (1 << (rank * 8 + file)) else "." for file in range(8))
        lines.append(f"{rank + 1} {' '.join(row)}")
    lines.append("  a b c d e f g h")
    return "\n".join(lines)


def print_bb(bitboard: Bitboard) -> None:
    print(format_bb(bitboard))
