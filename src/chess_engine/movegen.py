"""Pseudo-legal move generation, plus a legality filter.

Generation is pseudo-legal: everything here obeys the movement rules but may leave the
moving side's own king in check. :func:`generate_legal` filters those out by making
each move and testing the king square.

That is slower than generating only legal moves with pin detection, but it is far
easier to get right, and perft is the thing that matters first. The faster scheme can
replace it later with this version kept as a test oracle.
"""

from .attacks import (
    KING_ATTACKS,
    KNIGHT_ATTACKS,
    PAWN_ATTACKS,
    bishop_attacks,
    queen_attacks,
    rook_attacks,
)
from .bitboard import (
    BETWEEN_BB,
    RANK_BB,
    SQUARE_BB,
    north,
    north_east,
    north_west,
    south,
    south_east,
    south_west,
)
from .board import Position
from .move import (
    CAPTURE,
    DOUBLE_PUSH,
    EP_CAPTURE,
    KING_CASTLE,
    PROMO_CAPTURE_KNIGHT,
    PROMO_KNIGHT,
    QUEEN_CASTLE,
    QUIET,
    move_to_uci,
)
from .types import (
    BISHOP,
    BLACK_OO,
    BLACK_OOO,
    CASTLING_KING_TO,
    CASTLING_ROOK_FROM,
    KNIGHT,
    NO_SQUARE,
    PAWN,
    QUEEN,
    ROOK,
    WHITE,
    WHITE_OO,
    WHITE_OOO,
    Bitboard,
    Color,
    Move,
    Square,
)

_PROMOTION_RANK = (RANK_BB[7], RANK_BB[0])
# Rank a pawn stands on after a single push from its starting rank.
_DOUBLE_PUSH_RANK = (RANK_BB[2], RANK_BB[5])

# Castling rights in (short, long) order per colour.
_CASTLING_RIGHTS = ((WHITE_OO, WHITE_OOO), (BLACK_OO, BLACK_OOO))


def _add_promotions(moves: list[Move], origin: Square, target: Square, capture: bool) -> None:
    """Helper to append all 4 promotion piece options for a pawn move.

    Four promotion piece options are Knight, Bishop, Rook and Queen.
    """
    base = PROMO_CAPTURE_KNIGHT if capture else PROMO_KNIGHT
    moves.append(origin | (target << 6) | (base << 12))
    moves.append(origin | (target << 6) | ((base + 1) << 12))
    moves.append(origin | (target << 6) | ((base + 2) << 12))
    moves.append(origin | (target << 6) | ((base + 3) << 12))


def _generate_pawn_captures_and_promotions(
    pos: Position, moves: list[Move], us: Color, pawns: Bitboard, them_bb: Bitboard
) -> None:
    """Generates diagonal pawn captures, en passant captures, and promotion captures/pushes."""
    # Set directional vectors and bit shifts depending on whether White or Black is moving
    if us == WHITE:
        # -7 and -9 are used for calculating the origin square of a pawn capture for White
        back_left, back_right = -7, -9
        # Look for all opponent pieces that can be captured by pawns on the left and right diagonals
        left_caps = north_west(pawns) & them_bb
        right_caps = north_east(pawns) & them_bb
        # Look for all empty squares that can be pushed to by pawns
        pushed = north(pawns) & (~pos.occupied_all & 0xFFFF_FFFF_FFFF_FFFF)
    else:
        # 7 and 9 are used for calculating the origin square of a pawn capture for Black
        back_left, back_right = 9, 7
        left_caps = south_west(pawns) & them_bb
        right_caps = south_east(pawns) & them_bb
        pushed = south(pawns) & (~pos.occupied_all & 0xFFFF_FFFF_FFFF_FFFF)

    promotion_rank = _PROMOTION_RANK[us]

    # Process diagonal captures (splitting regular vs. promoting captures)
    for targets, delta in ((left_caps, back_left), (right_caps, back_right)):
        promos = targets & promotion_rank
        plain = targets & ~promotion_rank

        # Handle diagonal captures resulting in promotion
        while promos:
            low = promos & -promos
            target = low.bit_length() - 1
            _add_promotions(moves, target + delta, target, True)
            promos ^= low

        # Handle standard diagonal captures
        while plain:
            low = plain & -plain
            target = low.bit_length() - 1
            moves.append((target + delta) | (target << 6) | (CAPTURE << 12))
            plain ^= low

    # Handle en passant captures if an ep square is active
    if pos.ep_square != NO_SQUARE:
        ep = pos.ep_square
        attackers = PAWN_ATTACKS[us ^ 1][ep] & pawns
        while attackers:
            low = attackers & -attackers
            moves.append((low.bit_length() - 1) | (ep << 6) | (EP_CAPTURE << 12))
            attackers ^= low

    # Handle straight pushes that land on the promotion rank
    promotions = pushed & promotion_rank
    while promotions:
        low = promotions & -promotions
        target = low.bit_length() - 1
        _add_promotions(moves, target + (-8 if us == WHITE else 8), target, False)
        promotions ^= low


def _generate_pawn_quiet_moves(
    pos: Position,
    moves: list[Move],
    us: Color,
    pawns: Bitboard,
) -> None:
    """Generates non-capturing single pushes and double-step pawn advances."""
    empty = ~pos.occupied_all & 0xFFFF_FFFF_FFFF_FFFF
    pushed = (north(pawns) if us == WHITE else south(pawns)) & empty
    promotion_rank = _PROMOTION_RANK[us]
    back = -8 if us == WHITE else 8

    # Single pushes that do not result in promotion
    quiet_pushes = pushed & ~promotion_rank

    # Double-step pushes from the starting rank
    # Only pawns that stopped on the intermediate rank can have come from the start rank.
    stepped = pushed & _DOUBLE_PUSH_RANK[us]
    doubles = (north(stepped) if us == WHITE else south(stepped)) & empty

    # Record single quiet pushes
    while quiet_pushes:
        low = quiet_pushes & -quiet_pushes
        target = low.bit_length() - 1
        moves.append((target + back) | (target << 6))
        quiet_pushes ^= low

    # Record double pushes
    while doubles:
        low = doubles & -doubles
        target = low.bit_length() - 1
        moves.append((target + 2 * back) | (target << 6) | (DOUBLE_PUSH << 12))
        doubles ^= low


def _generate_pawn_moves(pos: Position, moves: list[Move], captures_only: bool) -> None:
    """Master dispatcher for generating all legal or pseudo-legal pawn moves."""
    us = pos.side_to_move
    pawns = pos.pieces[us][PAWN]
    if not pawns:
        return
    them_bb = pos.occupied[us ^ 1]

    # Always generate captures, promotions, and en-passants
    _generate_pawn_captures_and_promotions(pos, moves, us, pawns, them_bb)

    # Generate non-capturing quiet/double pushes unless restricted to captures only
    if not captures_only:
        _generate_pawn_quiet_moves(pos, moves, us, pawns)


def _add_piece_moves(
    moves: list[Move], origin: Square, targets: Bitboard, them_bb: Bitboard
) -> None:
    """Helper to encode and append calculated moves for non-pawn pieces."""
    while targets:
        low = targets & -targets
        target = low.bit_length() - 1
        flag = CAPTURE if low & them_bb else QUIET
        moves.append(origin | (target << 6) | (flag << 12))
        targets ^= low


def _generate_piece_moves(pos: Position, moves: list[Move], allowed: Bitboard) -> None:
    """Generates pseudo-legal moves for all pieces except pawns."""
    us = pos.side_to_move
    occupied = pos.occupied_all
    them_bb = pos.occupied[us ^ 1]
    ours = pos.pieces[us]

    # Generate Knight moves
    knights = ours[KNIGHT]
    while knights:
        low = knights & -knights
        origin = low.bit_length() - 1
        _add_piece_moves(moves, origin, KNIGHT_ATTACKS[origin] & allowed, them_bb)
        knights ^= low

    # Generate Bishop moves
    bishops = ours[BISHOP]
    while bishops:
        low = bishops & -bishops
        origin = low.bit_length() - 1
        _add_piece_moves(moves, origin, bishop_attacks(origin, occupied) & allowed, them_bb)
        bishops ^= low

    # Generate Rook moves
    rooks = ours[ROOK]
    while rooks:
        low = rooks & -rooks
        origin = low.bit_length() - 1
        _add_piece_moves(moves, origin, rook_attacks(origin, occupied) & allowed, them_bb)
        rooks ^= low

    # Generate Queen moves
    queens = ours[QUEEN]
    while queens:
        low = queens & -queens
        origin = low.bit_length() - 1
        _add_piece_moves(moves, origin, queen_attacks(origin, occupied) & allowed, them_bb)
        queens ^= low

    # Generate King moves (non-castling)
    king = pos.king_square(us)
    _add_piece_moves(moves, king, KING_ATTACKS[king] & allowed, them_bb)


def _generate_castling(pos: Position, moves: list[Move]) -> None:
    """Generates short and long castling moves if conditions and safety rules allow."""
    us = pos.side_to_move
    them = us ^ 1
    # Check if any castling rights remain for the current player
    if not pos.castling_rights & (_CASTLING_RIGHTS[us][0] | _CASTLING_RIGHTS[us][1]):
        return
    king = pos.king_square(us)
    # King cannot castle out of check
    if pos.is_attacked_by(king, them):
        return

    for index, right in enumerate(_CASTLING_RIGHTS[us]):
        if not pos.castling_rights & right:
            continue
        rook = CASTLING_ROOK_FROM[right]
        # Every square between king and rook must be empty: this covers b1/b8, which the
        # king never visits but the rook must pass through.
        if BETWEEN_BB[king][rook] & pos.occupied_all:
            continue
        king_to = CASTLING_KING_TO[right]

        # The king must not be attacked on the square it crosses or the one it lands on.
        transit = BETWEEN_BB[king][king_to] | SQUARE_BB[king_to]
        attacked = False
        while transit:
            low = transit & -transit
            if pos.is_attacked_by(low.bit_length() - 1, them):
                attacked = True
                break
            transit ^= low
        if attacked:
            continue

        # Determine flag (Kingside vs Queenside) and record the move
        flag = KING_CASTLE if index == 0 else QUEEN_CASTLE
        moves.append(king | (king_to << 6) | (flag << 12))


def generate_pseudo_legal(pos: Position) -> list[Move]:
    """All moves obeying the movement rules, possibly leaving the own king in check."""
    moves: list[Move] = []
    allowed = ~pos.occupied[pos.side_to_move] & 0xFFFF_FFFF_FFFF_FFFF
    _generate_pawn_moves(pos, moves, captures_only=False)
    _generate_piece_moves(pos, moves, allowed)
    _generate_castling(pos, moves)
    return moves


def generate_pseudo_legal_captures(pos: Position) -> list[Move]:
    """Captures and promotions only, for quiescence search."""
    moves: list[Move] = []
    _generate_pawn_moves(pos, moves, captures_only=True)
    _generate_piece_moves(pos, moves, pos.occupied[pos.side_to_move ^ 1])
    return moves


def is_legal(pos: Position, move: Move) -> bool:
    """Whether a pseudo-legal move leaves the mover's own king safe.

    Must be called before the move is made; it makes and unmakes internally.
    """
    us = pos.side_to_move
    pos.make_move(move)
    safe = not pos.is_attacked_by(pos.king_square(us), us ^ 1)
    pos.unmake_move()
    return safe


def generate_legal(pos: Position) -> list[Move]:
    """Filters pseudo-legal moves down to strictly legal ones (king must not be in check.)

    Parameters
    ----------
    pos : Position
        Position to generate legal moves for.

    Returns
    -------
    list[Move]
        List of legal moves in the position, in no particular order.
    """
    us = pos.side_to_move
    legal = []
    for move in generate_pseudo_legal(pos):
        pos.make_move(move)
        if not pos.is_attacked_by(pos.king_square(us), us ^ 1):
            legal.append(move)
        pos.unmake_move()
    return legal


def generate_legal_captures(pos: Position) -> list[Move]:
    """Filters pseudo-legal captures down to strictly legal ones.

    Parameters
    ----------
    pos : Position
        Position to generate legal captures for.

    Returns
    -------
    list[Move]
        List of legal captures in the position, in no particular order.
    """
    us = pos.side_to_move
    legal = []
    for move in generate_pseudo_legal_captures(pos):
        pos.make_move(move)
        if not pos.is_attacked_by(pos.king_square(us), us ^ 1):
            legal.append(move)
        pos.unmake_move()
    return legal


def has_legal_moves(pos: Position) -> bool:
    """Fast check to see if the side to move has at least one legal move available.

    Parameters
    ----------
    pos : Position
        Position to check for legal moves.

    Returns
    -------
    bool
        True if there is at least one legal move, False otherwise.
    """
    us = pos.side_to_move
    for move in generate_pseudo_legal(pos):
        pos.make_move(move)
        safe = not pos.is_attacked_by(pos.king_square(us), us ^ 1)
        pos.unmake_move()
        if safe:
            return True
    return False


def is_checkmate(pos: Position) -> bool:
    """Returns True if the current side is in check and has no legal responses."""
    return pos.in_check() and not has_legal_moves(pos)


def is_stalemate(pos: Position) -> bool:
    """Returns True if the current side is NOT in check but has no legal moves."""
    return not pos.in_check() and not has_legal_moves(pos)


def move_from_uci(pos: Position, text: str) -> Move:
    """Resolve a UCI move string against the legal moves of ``pos``."""
    for move in generate_legal(pos):
        if move_to_uci(move) == text:
            return move
    raise ValueError(f"illegal or malformed move {text!r} in position {pos.fen()!r}")
