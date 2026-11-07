"""Move encoding.

A move is a single 16-bit integer::

    bits  0-5   origin square
    bits  6-11  target square
    bits 12-15  flags

The flag layout is chosen so that two bits carry meaning on their own: bit 14 marks a
capture and bit 15 marks a promotion. That makes ``is_capture`` and ``is_promotion``
single mask tests, and makes the promotion piece type ``KNIGHT + (flags & 3)``.

Castling is encoded as the king's own move (e1->g1, e1->c1); the rook's movement is
implied by the flag.
"""

from typing import Final

from .types import KNIGHT, Move, PieceType, Square, square_name

# --- Flags ----------------------------------------------------------------

QUIET: Final = 0
DOUBLE_PUSH: Final = 1
KING_CASTLE: Final = 2
QUEEN_CASTLE: Final = 3
CAPTURE: Final = 4
EP_CAPTURE: Final = 5
PROMO_KNIGHT: Final = 8
PROMO_BISHOP: Final = 9
PROMO_ROOK: Final = 10
PROMO_QUEEN: Final = 11
PROMO_CAPTURE_KNIGHT: Final = 12
PROMO_CAPTURE_BISHOP: Final = 13
PROMO_CAPTURE_ROOK: Final = 14
PROMO_CAPTURE_QUEEN: Final = 15

CAPTURE_BIT: Final = 4
PROMOTION_BIT: Final = 8

#: Not a legal encoding of any real move, since origin == target.
MOVE_NONE: Final[Move] = 0

PROMOTION_CHARS: Final = "nbrq"


def make_move(origin: Square, target: Square, flags: int = QUIET) -> Move:
    """Create a move from its components.

    Parameters
    ----------
    origin : Square
        The square the piece is moving from.
    target : Square
        The square the piece is moving to.
    flags : int, optional
        The flags for the move, by default QUIET

    Returns
    -------
    Move
        The created move.
    """
    return origin | (target << 6) | (flags << 12)


def move_origin(move: Move) -> Square:
    """Returns the origin square of the move."""
    return move & 0x3F


def move_target(move: Move) -> Square:
    """Returns the target square of the move."""
    return (move >> 6) & 0x3F


def move_flags(move: Move) -> int:
    """Returns the flags of the move."""
    return move >> 12


def is_capture(move: Move) -> bool:
    """Returns True if the move is a capture."""
    return (move >> 12) & CAPTURE_BIT != 0


def is_promotion(move: Move) -> bool:
    """Returns True if the move is a promotion."""
    return (move >> 12) & PROMOTION_BIT != 0


def is_castling(move: Move) -> bool:
    """Returns True if the move is a castling move."""
    flags = move >> 12
    return flags in (KING_CASTLE, QUEEN_CASTLE)


def is_en_passant(move: Move) -> bool:
    """Returns True if the move is an en passant capture."""
    return move >> 12 == EP_CAPTURE


def promotion_type(move: Move) -> PieceType:
    """Only meaningful when :func:`is_promotion` is true."""
    return KNIGHT + ((move >> 12) & 3)


def move_to_uci(move: Move) -> str:
    """Convert a move to UCI format.

    Parameters
    ----------
    move : Move
        The move to convert.

    Returns
    -------
    str
        The UCI string representation of the move, e.g. "e2e4" or "e7e8q".
    """
    if move == MOVE_NONE:
        return "0000"
    text = square_name(move & 0x3F) + square_name((move >> 6) & 0x3F)
    if (move >> 12) & PROMOTION_BIT:
        text += PROMOTION_CHARS[(move >> 12) & 3]
    return text
