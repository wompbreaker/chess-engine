"""Core types, constants and square helpers.

Square indexing is LERF (little-endian rank-file): A1 = 0, B1 = 1, ... H8 = 63.
So ``rank = square >> 3`` and ``file = square & 7``.

Colors, piece types and squares are plain ``int`` aliases rather than enums: these
values sit in the hottest loops in the engine, and they map one-to-one onto the C++
enums this code will eventually be ported to.

8   56  57  58  59  60  61  62  63

7   48  49  50  51  52  53  54  55

6   40  41  42  43  44  45  46  47

5   32  33  34  35  36  37  38  39

4   24  25  26  27  28  29  30  31

3   16  17  18  19  20  21  22  23

2   8   9   10  11  12  13  14  15

1   0   1   2   3   4   5   6   7

    A   B   C   D   E   F   G   H
"""

from typing import Final

Color = int  # Color of a piece
PieceType = int  # Type of a piece
Piece = int
Square = int
Bitboard = int  # Represents the whole bitboard
Move = int
File = int  # File of a board
Rank = int  # Rank of a board
Rights = int  # Castling rights

# --- Colors ---------------------------------------------------------------------------------------

WHITE: Final[Color] = 0
BLACK: Final[Color] = 1
COLOR_NB: Final = 2


def opposite(color: Color) -> Color:
    """Opposite color: WHITE -> BLACK, BLACK -> WHITE."""
    return color ^ 1


# --- Piece types ----------------------------------------------------------------------------------

PAWN: Final[PieceType] = 0
KNIGHT: Final[PieceType] = 1
BISHOP: Final[PieceType] = 2
ROOK: Final[PieceType] = 3
QUEEN: Final[PieceType] = 4
KING: Final[PieceType] = 5

PIECE_TYPE_NB: Final = 6  # Number of piece types (not counting empty squares)

# --- Pieces (colour + type packed into one value) -------------------------------------------------

WHITE_PAWN: Final[Piece] = 0
WHITE_KNIGHT: Final[Piece] = 1
WHITE_BISHOP: Final[Piece] = 2
WHITE_ROOK: Final[Piece] = 3
WHITE_QUEEN: Final[Piece] = 4
WHITE_KING: Final[Piece] = 5

BLACK_PAWN: Final[Piece] = 6
BLACK_KNIGHT: Final[Piece] = 7
BLACK_BISHOP: Final[Piece] = 8
BLACK_ROOK: Final[Piece] = 9
BLACK_QUEEN: Final[Piece] = 10
BLACK_KING: Final[Piece] = 11

NO_PIECE: Final[Piece] = 12

PIECE_NB: Final = 13  # Number of pieces (including empty squares)


def make_piece(color: Color, piece_type: PieceType) -> Piece:
    """Make piece from color and type."""
    return color * PIECE_TYPE_NB + piece_type


def piece_color(piece: Piece) -> Color:
    """Get the color of a piece."""
    return piece // PIECE_TYPE_NB


def piece_type_of(piece: Piece) -> PieceType:
    """Get the type of the piece."""
    return piece % PIECE_TYPE_NB


PIECE_TO_CHAR: Final[str] = "PNBRQKpnbrqk."
CHAR_TO_PIECE: Final[dict[str, Piece]] = {char: idx for idx, char in enumerate(PIECE_TO_CHAR[:12])}

# --- Squares --------------------------------------------------------------------------------------

SQUARE_NB: Final = 64
NO_SQUARE: Final[Square] = 64

FILE_NB: Final = 8
RANK_NB: Final = 8

FILE_A: Final[File] = 0
FILE_B: Final[File] = 1
FILE_C: Final[File] = 2
FILE_D: Final[File] = 3
FILE_E: Final[File] = 4
FILE_F: Final[File] = 5
FILE_G: Final[File] = 6
FILE_H: Final[File] = 7

RANK_1: Final[Rank] = 0
RANK_2: Final[Rank] = 1
RANK_3: Final[Rank] = 2
RANK_4: Final[Rank] = 3
RANK_5: Final[Rank] = 4
RANK_6: Final[Rank] = 5
RANK_7: Final[Rank] = 6
RANK_8: Final[Rank] = 7


def make_square(file: File, rank: Rank) -> Square:
    """Make square from file and rank."""
    return rank * 8 + file


def file_of(square: Square) -> File:
    """Get the file of the square."""
    return square & 7


def rank_of(square: Square) -> Rank:
    """Get the rank of the square."""
    return square >> 3


def flip_rank(square: Square) -> Square:
    """Mirror a square vertically (A1 <-> A8). Used to reuse white tables for black."""
    return square ^ 56


def flip_file(square: Square) -> Square:
    """Mirror a square horizontally (A1 <-> H1)."""
    return square ^ 7


def relative_rank(color: Color, square: Square) -> int:
    """Rank as seen from ``color``'s side: rank 0 is that colour's back rank."""
    return (square >> 3) ^ (color * 7)


def relative_square(color: Color, square: Square) -> Square:
    return square ^ (color * 56)


def square_name(square: Square) -> str:
    """Name of the square."""
    if square == NO_SQUARE:
        return "-"
    return "abcdefgh"[square & 7] + "12345678"[square >> 3]


def square_from_name(name: str) -> Square:
    """Get a square from name."""
    if name == "-":
        return NO_SQUARE
    if len(name) != 2 or name[0] not in "abcdefgh" or name[1] not in "12345678":
        raise ValueError(f"invalid square name: {name!r}")
    return make_square(ord(name[0]) - ord("a"), ord(name[1]) - ord("1"))


# Named squares: A1, B1, ... H8 as module-level constants.
A1: Final[Square] = 0
B1: Final[Square] = 1
C1: Final[Square] = 2
D1: Final[Square] = 3
E1: Final[Square] = 4
F1: Final[Square] = 5
G1: Final[Square] = 6
H1: Final[Square] = 7

A2: Final[Square] = 8
B2: Final[Square] = 9
C2: Final[Square] = 10
D2: Final[Square] = 11
E2: Final[Square] = 12
F2: Final[Square] = 13
G2: Final[Square] = 14
H2: Final[Square] = 15

A3: Final[Square] = 16
B3: Final[Square] = 17
C3: Final[Square] = 18
D3: Final[Square] = 19
E3: Final[Square] = 20
F3: Final[Square] = 21
G3: Final[Square] = 22
H3: Final[Square] = 23

A4: Final[Square] = 24
B4: Final[Square] = 25
C4: Final[Square] = 26
D4: Final[Square] = 27
E4: Final[Square] = 28
F4: Final[Square] = 29
G4: Final[Square] = 30
H4: Final[Square] = 31

A5: Final[Square] = 32
B5: Final[Square] = 33
C5: Final[Square] = 34
D5: Final[Square] = 35
E5: Final[Square] = 36
F5: Final[Square] = 37
G5: Final[Square] = 38
H5: Final[Square] = 39

A6: Final[Square] = 40
B6: Final[Square] = 41
C6: Final[Square] = 42
D6: Final[Square] = 43
E6: Final[Square] = 44
F6: Final[Square] = 45
G6: Final[Square] = 46
H6: Final[Square] = 47

A7: Final[Square] = 48
B7: Final[Square] = 49
C7: Final[Square] = 50
D7: Final[Square] = 51
E7: Final[Square] = 52
F7: Final[Square] = 53
G7: Final[Square] = 54
H7: Final[Square] = 55

A8: Final[Square] = 56
B8: Final[Square] = 57
C8: Final[Square] = 58
D8: Final[Square] = 59
E8: Final[Square] = 60
F8: Final[Square] = 61
G8: Final[Square] = 62
H8: Final[Square] = 63

# --- Castling -------------------------------------------------------------

NO_CASTLING: Final[Rights] = 0
WHITE_OO: Final[Rights] = 1
WHITE_OOO: Final[Rights] = 2
BLACK_OO: Final[Rights] = 4
BLACK_OOO: Final[Rights] = 8
ANY_CASTLING: Final[Rights] = 15
CASTLING_NB: Final[Rights] = 16

CASTLING_TO_CHAR: Final = "KQkq"


def castling_rights_to_string(rights: Rights) -> str:
    if rights == NO_CASTLING:
        return "-"
    return "".join(c for i, c in enumerate(CASTLING_TO_CHAR) if rights & (1 << i))


def castling_rights_from_string(text: str) -> Rights:
    if text == "-":
        return NO_CASTLING
    rights = NO_CASTLING
    for char in text:
        index = CASTLING_TO_CHAR.find(char)
        if index < 0:
            raise ValueError(f"Invalid castling rights: {text!r}")
        rights |= 1 << index
    return rights


# Squares of the rooks that participate in each castling right, and the squares the
# king and rook end up on. Standard chess only, so these are fixed.
CASTLING_ROOK_FROM: Final[dict[Rights, Square]] = {
    WHITE_OO: H1,
    WHITE_OOO: A1,
    BLACK_OO: H8,
    BLACK_OOO: A8,
}
CASTLING_ROOK_TO: Final[dict[Rights, Square]] = {
    WHITE_OO: F1,
    WHITE_OOO: D1,
    BLACK_OO: F8,
    BLACK_OOO: D8,
}
CASTLING_KING_FROM: Final[dict[Rights, Square]] = {
    WHITE_OO: E1,
    WHITE_OOO: E1,
    BLACK_OO: E8,
    BLACK_OOO: E8,
}
CASTLING_KING_TO: Final[dict[Rights, Square]] = {
    WHITE_OO: G1,
    WHITE_OOO: C1,
    BLACK_OO: G8,
    BLACK_OOO: C8,
}


def _build_castling_mask() -> tuple[Rights, ...]:
    """Rights surviving a move that touches each square, as an AND mask."""
    mask = [ANY_CASTLING] * SQUARE_NB
    mask[E1] &= ~(WHITE_OO | WHITE_OOO)
    mask[E8] &= ~(BLACK_OO | BLACK_OOO)
    mask[H1] &= ~WHITE_OO
    mask[A1] &= ~WHITE_OOO
    mask[H8] &= ~BLACK_OO
    mask[A8] &= ~BLACK_OOO
    return tuple(mask)


#: ``rights & CASTLING_MASK[origin] & CASTLING_MASK[target]`` applies every way a single
#: move can destroy castling rights: king moves, rook moves, and rook captures.
CASTLING_MASK: Final[tuple[Rights, ...]] = _build_castling_mask()

STARTING_FEN: Final = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
