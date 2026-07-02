# Caissa Britannia

Fergus Duniho's British-themed 10x10 chess variant (2003, originally *British
Chess*). The **Queen is the royal piece** — checkmate her to win. The Lion,
Unicorn and Dragon are the heraldic animals of England, Scotland and Wales.

## Board and setup

10x10 board. Each side has 1 Queen, 1 Prince Consort, 2 Rooks, 2 Anglican
Bishops, 2 Unicorns, 2 Lions, 2 Dragons and 10 Pawns.

- Rank 1 (White, files a–j): **Dragon, Rook, Unicorn, Bishop, Queen, Prince
  Consort, Bishop, Unicorn, Rook, Dragon**.
- Rank 2: Lions on b2 and i2.
- Rank 3: ten Pawns.
- Black mirrors this on ranks 10/9/8. White moves first.

## The royal Queen

- The Queen slides any number of squares orthogonally or diagonally, like the
  chess Queen, **but she may not pass over any square it would be illegal for
  her to move to** — any square where she would stand in check, including any
  square facing the enemy Queen.
- **The two Queens may never face each other** across an empty rank, file or
  diagonal (so a piece standing between facing Queens is pinned to the line,
  as in Xiangqi), and a Queen may never move adjacent to the enemy Queen.
- The Queen's *checking* power is a plain Queen slide — her movement
  restriction does not weaken her attack.
- Checkmate of the Queen wins. Stalemate is a draw.

## The other pieces

- **Prince Consort** (shown as a King; *not* royal): slides like a Queen
  **without capturing**, or captures by moving one square in any direction.
- **Lion** (Dawson's Leo): moves like a Queen without capturing; to capture it
  must **leap exactly one screen** (a piece of either colour) along a Queen
  line and take the first piece beyond it. It cannot capture an adjacent piece
  and cannot land on empty squares beyond the screen.
- **Unicorn**: Bishop + Nightrider (repeated Knight leaps in one direction;
  each landing square before the last must be empty).
- **Dragon**: any number of consecutive **two-square leaps** in one radial
  direction (Alfilrider + Dabbabarider). The jumped-over squares are ignored;
  each landing square before the last must be empty. Each Dragon is bound to
  one quarter of the board's squares.
- **Anglican Bishop**: slides diagonally, or steps one square orthogonally
  **without capturing** (so it can change square colour).
- **Rook**: as in chess. There is **no castling** for any piece.
- **Knight**: as in chess; appears only by promotion.
- **Pawn**: as in chess — one step forward, captures diagonally forward,
  double step from its starting (third) rank, **en passant** available.

## Promotion

A Pawn reaching the last rank **must** promote — to a **Knight** (always
available) or to any piece type its owner has fewer of on the board than at
the start ("liberating" a captured piece).

## Draws

Stalemate, threefold repetition, 50 moves without a capture or pawn move
(100 half-moves), bare Queen vs bare Queen (they can never capture each
other), and a hard 800-ply cap.

## Implementation notes

- The through-check rule is implemented exactly as the source's technical
  description: each square the Queen crosses must be free of enemy attack
  (origin square vacated), with the enemy Queen counted as a plain slider.
- The source lists the Queen among the promotion choices; since the royal
  Queen can never actually be captured, that choice can never become
  available. The Prince Consort is not a promotion option (per the source's
  published promotion list).
