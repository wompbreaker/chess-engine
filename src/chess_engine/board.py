"""The board: bitboards plus a redundant piece-on-square array, with FEN I/O.

``Position`` keeps two parallel representations of the same thing:

* ``pieces[color][piece_type]`` bitboards, for set-wise attack and move generation.
* ``piece_on[square]``, for O(1) "what is on this square" lookups.

They must never disagree. All mutation goes through :meth:`Position.put_piece`,
:meth:`Position.remove_piece` and :meth:`Position.move_piece`, which also maintain the
incremental Zobrist keys.
"""

from __future__ import annotations

from typing import NamedTuple

from . import zobrist
from .attacks import (
    KING_ATTACKS,
    KNIGHT_ATTACKS,
    PAWN_ATTACKS,
    bishop_attacks,
    rook_attacks,
)
from .bitboard import SQUARE_BB
from .move import (
    CAPTURE_BIT,
    DOUBLE_PUSH,
    EP_CAPTURE,
    KING_CASTLE,
    PROMOTION_BIT,
    QUEEN_CASTLE,
)
from .types import (
    ANY_CASTLING,
    BISHOP,
    BLACK,
    CASTLING_MASK,
    COLOR_NB,
    KING,
    KNIGHT,
    NO_PIECE,
    NO_SQUARE,
    PAWN,
    PIECE_TO_CHAR,
    PIECE_TYPE_NB,
    QUEEN,
    ROOK,
    SQUARE_NB,
    STARTING_FEN,
    WHITE,
    Bitboard,
    Color,
    Move,
    Piece,
    PieceType,
    Square,
    castling_rights_from_string,
    castling_rights_to_string,
    square_from_name,
    square_name,
)


class UndoInfo(NamedTuple):
    """Everything about a position that a move can destroy and unmake must restore."""

    move: Move
    captured: Piece
    castling_rights: int
    ep_square: Square
    halfmove_clock: int
    key: int
    pawn_key: int


class Position:
    """A chess position."""

    __slots__ = (
        "castling_rights",
        "ep_square",
        "fullmove_number",
        "halfmove_clock",
        "history",
        "key",
        "occupied",
        "occupied_all",
        "pawn_key",
        "piece_on",
        "pieces",
        "side_to_move",
    )

    pieces: list[list[Bitboard]]
    occupied: list[Bitboard]
    occupied_all: Bitboard
    piece_on: list[Piece]
    side_to_move: Color
    castling_rights: int
    ep_square: Square
    halfmove_clock: int
    fullmove_number: int
    key: int
    pawn_key: int
    history: list[UndoInfo]

    def __init__(self, fen: str = STARTING_FEN) -> None:
        self.set_fen(fen)

    # --- Construction -----------------------------------------------------

    @classmethod
    def starting(cls) -> Position:
        return cls(STARTING_FEN)

    def clear(self) -> None:
        self.pieces = [[0] * PIECE_TYPE_NB for _ in range(COLOR_NB)]
        self.occupied = [0, 0]
        self.occupied_all = 0
        self.piece_on = [NO_PIECE] * SQUARE_NB
        self.side_to_move = WHITE
        self.castling_rights = 0
        self.ep_square = NO_SQUARE
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.key = 0
        self.pawn_key = 0
        self.history = []

    def copy(self) -> Position:
        other = Position.__new__(Position)
        other.pieces = [side.copy() for side in self.pieces]
        other.occupied = self.occupied.copy()
        other.occupied_all = self.occupied_all
        other.piece_on = self.piece_on.copy()
        other.side_to_move = self.side_to_move
        other.castling_rights = self.castling_rights
        other.ep_square = self.ep_square
        other.halfmove_clock = self.halfmove_clock
        other.fullmove_number = self.fullmove_number
        other.key = self.key
        other.pawn_key = self.pawn_key
        other.history = self.history.copy()
        return other

    # --- Piece placement --------------------------------------------------

    def put_piece(self, piece: Piece, square: Square) -> None:
        color = piece // PIECE_TYPE_NB
        piece_type = piece % PIECE_TYPE_NB
        bb = SQUARE_BB[square]
        self.pieces[color][piece_type] |= bb
        self.occupied[color] |= bb
        self.occupied_all |= bb
        self.piece_on[square] = piece
        key = zobrist.PIECE_SQUARE[piece][square]
        self.key ^= key
        if piece_type == PAWN:
            self.pawn_key ^= key

    def remove_piece(self, square: Square) -> None:
        piece = self.piece_on[square]
        color = piece // PIECE_TYPE_NB
        piece_type = piece % PIECE_TYPE_NB
        bb = SQUARE_BB[square]
        self.pieces[color][piece_type] ^= bb
        self.occupied[color] ^= bb
        self.occupied_all ^= bb
        self.piece_on[square] = NO_PIECE
        key = zobrist.PIECE_SQUARE[piece][square]
        self.key ^= key
        if piece_type == PAWN:
            self.pawn_key ^= key

    def move_piece(self, origin: Square, target: Square) -> None:
        """Move a piece to an empty square. The caller must clear ``target`` first."""
        piece = self.piece_on[origin]
        color = piece // PIECE_TYPE_NB
        piece_type = piece % PIECE_TYPE_NB
        bb = SQUARE_BB[origin] | SQUARE_BB[target]
        self.pieces[color][piece_type] ^= bb
        self.occupied[color] ^= bb
        self.occupied_all ^= bb
        self.piece_on[origin] = NO_PIECE
        self.piece_on[target] = piece
        key = zobrist.PIECE_SQUARE[piece][origin] ^ zobrist.PIECE_SQUARE[piece][target]
        self.key ^= key
        if piece_type == PAWN:
            self.pawn_key ^= key

    # --- Queries ----------------------------------------------------------

    def piece_at(self, square: Square) -> Piece:
        return self.piece_on[square]

    def pieces_bb(self, color: Color, piece_type: PieceType) -> Bitboard:
        return self.pieces[color][piece_type]

    def piece_type_bb(self, piece_type: PieceType) -> Bitboard:
        return self.pieces[WHITE][piece_type] | self.pieces[BLACK][piece_type]

    def king_square(self, color: Color) -> Square:
        bb = self.pieces[color][KING]
        return (bb & -bb).bit_length() - 1

    def empty_bb(self) -> Bitboard:
        return ~self.occupied_all & 0xFFFF_FFFF_FFFF_FFFF

    # --- Attacks ----------------------------------------------------------

    def attackers_to(self, square: Square, occupied: Bitboard | None = None) -> Bitboard:
        """All pieces of either colour attacking ``square``.

        ``occupied`` can be overridden to ask hypothetical questions, which is how
        x-ray attacks are found during static exchange evaluation.
        """
        if occupied is None:
            occupied = self.occupied_all
        white = self.pieces[WHITE]
        black = self.pieces[BLACK]
        queens = white[QUEEN] | black[QUEEN]
        return (
            (PAWN_ATTACKS[WHITE][square] & black[PAWN])
            | (PAWN_ATTACKS[BLACK][square] & white[PAWN])
            | (KNIGHT_ATTACKS[square] & (white[KNIGHT] | black[KNIGHT]))
            | (KING_ATTACKS[square] & (white[KING] | black[KING]))
            | (bishop_attacks(square, occupied) & (white[BISHOP] | black[BISHOP] | queens))
            | (rook_attacks(square, occupied) & (white[ROOK] | black[ROOK] | queens))
        )

    def is_attacked_by(self, square: Square, color: Color) -> bool:
        """Whether ``color`` attacks ``square``. Ordered cheapest test first."""
        their = self.pieces[color]
        if PAWN_ATTACKS[color ^ 1][square] & their[PAWN]:
            return True
        if KNIGHT_ATTACKS[square] & their[KNIGHT]:
            return True
        if KING_ATTACKS[square] & their[KING]:
            return True
        occupied = self.occupied_all
        queens = their[QUEEN]
        if bishop_attacks(square, occupied) & (their[BISHOP] | queens):
            return True
        return bool(rook_attacks(square, occupied) & (their[ROOK] | queens))

    def checkers(self) -> Bitboard:
        """Enemy pieces giving check to the side to move."""
        us = self.side_to_move
        return self.attackers_to(self.king_square(us)) & self.occupied[us ^ 1]

    def in_check(self) -> bool:
        us = self.side_to_move
        return self.is_attacked_by(self.king_square(us), us ^ 1)

    def _en_passant_is_legal(self, ep: Square, victim: Square) -> bool:
        """Whether the side to move has a legal capture onto the en-passant square.

        Recording the square only when it is genuinely capturable keeps the Zobrist key
        from distinguishing positions that are in fact identical, and matches the FEN
        convention used by most tools.
        """
        us = self.side_to_move
        them = us ^ 1
        candidates = PAWN_ATTACKS[them][ep] & self.pieces[us][PAWN]
        if not candidates:
            return False

        king = self.king_square(us)
        their = self.pieces[them]
        their_queens = their[QUEEN]
        ep_bb = SQUARE_BB[ep]
        victim_bb = SQUARE_BB[victim]

        while candidates:
            low = candidates & -candidates
            candidates ^= low
            occupied = (self.occupied_all ^ low ^ victim_bb) | ep_bb
            if bishop_attacks(king, occupied) & (their[BISHOP] | their_queens):
                continue
            if rook_attacks(king, occupied) & (their[ROOK] | their_queens):
                continue
            if KNIGHT_ATTACKS[king] & their[KNIGHT]:
                continue
            # The captured pawn is gone, so it cannot be the checker.
            if PAWN_ATTACKS[us][king] & (their[PAWN] ^ victim_bb):
                continue
            if KING_ATTACKS[king] & their[KING]:
                continue
            return True
        return False

    # --- Make and unmake --------------------------------------------------

    def _get_capture_info(self, flags: int, us: Color, target: Square) -> tuple[Piece, Square]:
        if flags == EP_CAPTURE:
            captured_square = target - 8 if us == WHITE else target + 8
            return self.piece_on[captured_square], captured_square
        if flags & CAPTURE_BIT:
            return self.piece_on[target], target
        return NO_PIECE, NO_SQUARE

    def _apply_special_move_flags(self, flags: int, us: Color, target: Square) -> None:
        if flags & PROMOTION_BIT:
            self.remove_piece(target)
            self.put_piece(us * PIECE_TYPE_NB + KNIGHT + (flags & 3), target)
        elif flags == KING_CASTLE:
            self.move_piece(target + 1, target - 1)
        elif flags == QUEEN_CASTLE:
            self.move_piece(target - 2, target + 1)

    def make_move(self, move: Move) -> None:
        """Apply a pseudo-legal move. Legality is the caller's responsibility."""
        origin = move & 0x3F
        target = (move >> 6) & 0x3F
        flags = move >> 12
        us = self.side_to_move
        moving = self.piece_on[origin]

        captured, captured_square = self._get_capture_info(flags, us, target)

        self.history.append(
            UndoInfo(
                move,
                captured,
                self.castling_rights,
                self.ep_square,
                self.halfmove_clock,
                self.key,
                self.pawn_key,
            )
        )

        if self.ep_square != NO_SQUARE:
            self.key ^= zobrist.EN_PASSANT[self.ep_square & 7]
            self.ep_square = NO_SQUARE

        if captured != NO_PIECE:
            self.remove_piece(captured_square)

        self.move_piece(origin, target)
        self._apply_special_move_flags(flags, us, target)

        rights = self.castling_rights & CASTLING_MASK[origin] & CASTLING_MASK[target]
        if rights != self.castling_rights:
            self.key ^= zobrist.CASTLING[self.castling_rights] ^ zobrist.CASTLING[rights]
            self.castling_rights = rights

        if captured != NO_PIECE or moving % PIECE_TYPE_NB == PAWN:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if us == BLACK:
            self.fullmove_number += 1

        self.side_to_move = us ^ 1
        self.key ^= zobrist.SIDE_TO_MOVE

        # Checked after the side flip, since legality is judged for the capturing side.
        if flags == DOUBLE_PUSH:
            ep = (origin + target) >> 1
            if self._en_passant_is_legal(ep, target):
                self.ep_square = ep
                self.key ^= zobrist.EN_PASSANT[ep & 7]

    def unmake_move(self) -> None:
        undo = self.history.pop()
        move = undo.move
        origin = move & 0x3F
        target = (move >> 6) & 0x3F
        flags = move >> 12

        us = self.side_to_move ^ 1
        self.side_to_move = us
        if us == BLACK:
            self.fullmove_number -= 1

        if flags & PROMOTION_BIT:
            self.remove_piece(target)
            self.put_piece(us * PIECE_TYPE_NB + PAWN, target)
        elif flags == KING_CASTLE:
            self.move_piece(target - 1, target + 1)
        elif flags == QUEEN_CASTLE:
            self.move_piece(target + 1, target - 2)

        self.move_piece(target, origin)

        if undo.captured != NO_PIECE:
            if flags == EP_CAPTURE:
                self.put_piece(undo.captured, target - 8 if us == WHITE else target + 8)
            else:
                self.put_piece(undo.captured, target)

        self.castling_rights = undo.castling_rights
        self.ep_square = undo.ep_square
        self.halfmove_clock = undo.halfmove_clock
        # Restored wholesale, so the piece updates above need not be key-exact.
        self.key = undo.key
        self.pawn_key = undo.pawn_key

    def make_null_move(self) -> None:
        """Pass the turn. Only legal when not in check."""
        self.history.append(
            UndoInfo(
                0,
                NO_PIECE,
                self.castling_rights,
                self.ep_square,
                self.halfmove_clock,
                self.key,
                self.pawn_key,
            )
        )
        if self.ep_square != NO_SQUARE:
            self.key ^= zobrist.EN_PASSANT[self.ep_square & 7]
            self.ep_square = NO_SQUARE
        self.halfmove_clock += 1
        if self.side_to_move == BLACK:
            self.fullmove_number += 1
        self.side_to_move ^= 1
        self.key ^= zobrist.SIDE_TO_MOVE

    def unmake_null_move(self) -> None:
        undo = self.history.pop()
        self.side_to_move ^= 1
        if self.side_to_move == BLACK:
            self.fullmove_number -= 1
        self.castling_rights = undo.castling_rights
        self.ep_square = undo.ep_square
        self.halfmove_clock = undo.halfmove_clock
        self.key = undo.key
        self.pawn_key = undo.pawn_key

    # --- Zobrist ----------------------------------------------------------

    def compute_keys(self) -> tuple[int, int]:
        """Recompute both keys from scratch. Used to verify incremental updates."""
        key = 0
        pawn_key = 0
        for square in range(SQUARE_NB):
            piece = self.piece_on[square]
            if piece != NO_PIECE:
                piece_key = zobrist.PIECE_SQUARE[piece][square]
                key ^= piece_key
                if piece % PIECE_TYPE_NB == PAWN:
                    pawn_key ^= piece_key
        key ^= zobrist.CASTLING[self.castling_rights]
        if self.ep_square != NO_SQUARE:
            key ^= zobrist.EN_PASSANT[self.ep_square & 7]
        if self.side_to_move == BLACK:
            key ^= zobrist.SIDE_TO_MOVE
        return key, pawn_key

    # --- FEN --------------------------------------------------------------

    def _parse_fen_placement(self, placement: str, fen: str) -> None:
        rank = 7
        file = 0
        for char in placement:
            if char == "/":
                if file != 8:
                    raise ValueError(f"FEN rank {rank + 1} does not cover 8 files: {fen!r}")
                rank -= 1
                file = 0
                if rank < 0:
                    raise ValueError(f"FEN has too many ranks: {fen!r}")
            elif char.isdigit():
                file += int(char)
            else:
                index = PIECE_TO_CHAR.find(char)
                if index < 0 or index >= NO_PIECE:
                    raise ValueError(f"invalid piece {char!r} in FEN: {fen!r}")
                if file > 7:
                    raise ValueError(f"FEN rank {rank + 1} overflows: {fen!r}")
                self.put_piece(index, rank * 8 + file)
                file += 1
        if rank != 0 or file != 8:
            raise ValueError(f"FEN placement does not describe 64 squares: {fen!r}")

    def set_fen(self, fen: str) -> None:
        fields = fen.split()
        if len(fields) < 4:
            raise ValueError(f"FEN needs at least 4 fields, got {len(fields)}: {fen!r}")

        self.clear()
        placement, active, castling, ep = fields[:4]

        self._parse_fen_placement(placement, fen)

        if active not in ("w", "b"):
            raise ValueError(f"invalid side to move {active!r} in FEN: {fen!r}")
        self.side_to_move = WHITE if active == "w" else BLACK

        self.castling_rights = castling_rights_from_string(castling) & ANY_CASTLING
        self.ep_square = square_from_name(ep)
        if self.ep_square != NO_SQUARE:
            victim = self.ep_square - 8 if self.side_to_move == WHITE else self.ep_square + 8
            if not self._en_passant_is_legal(self.ep_square, victim):
                self.ep_square = NO_SQUARE

        self.halfmove_clock = int(fields[4]) if len(fields) > 4 else 0
        self.fullmove_number = int(fields[5]) if len(fields) > 5 else 1

        self.key ^= zobrist.CASTLING[self.castling_rights]
        if self.ep_square != NO_SQUARE:
            self.key ^= zobrist.EN_PASSANT[self.ep_square & 7]
        if self.side_to_move == BLACK:
            self.key ^= zobrist.SIDE_TO_MOVE

    def fen(self) -> str:
        rows = []
        for rank in range(7, -1, -1):
            row = []
            empty = 0
            for file in range(8):
                piece = self.piece_on[rank * 8 + file]
                if piece == NO_PIECE:
                    empty += 1
                    continue
                if empty:
                    row.append(str(empty))
                    empty = 0
                row.append(PIECE_TO_CHAR[piece])
            if empty:
                row.append(str(empty))
            rows.append("".join(row))
        return " ".join(
            (
                "/".join(rows),
                "w" if self.side_to_move == WHITE else "b",
                castling_rights_to_string(self.castling_rights),
                square_name(self.ep_square),
                str(self.halfmove_clock),
                str(self.fullmove_number),
            )
        )

    # --- Debugging --------------------------------------------------------

    def __str__(self) -> str:
        lines = []
        for rank in range(7, -1, -1):
            cells = [PIECE_TO_CHAR[self.piece_on[rank * 8 + file]] for file in range(8)]
            lines.append(f"{rank + 1} {' '.join(cells)}")
        lines.append("  a b c d e f g h")
        lines.append("")
        lines.append(f"fen: {self.fen()}")
        lines.append(f"key: {self.key:016x}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"Position({self.fen()!r})"
