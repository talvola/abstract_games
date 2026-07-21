# Sleeping Beauty Draughts (Dornröschendame)

Invented by **Ralf Gering** in Tübingen, 1986; the German name *Dornröschendame*
was coined by Jürgen Winkler. A Checkers (English draughts) variant whose motto is
*"the curse of the Checkers draw is vanquished"* — **it cannot end in a draw.**

Rules below are *as implemented*. The authoritative source is *Abstract Games*
magazine, **Issue 14 (Summer 2003), pp. 25–26**, by Ralf Gering; line references
point at that article's text.

## Board and setup
- Played on the **32 dark squares** of an 8×8 board, 12 men per side, standard
  Checkers starting position (three ranks each). **White moves first.**
- Here algebraic **a1 = bottom-left**, White (player 0) advances up the board,
  Black (player 1) down; playable squares are those with `(col+row)` even.

## Men
- Move **one square diagonally forward** into a vacant square.
- *"They capture adjacent enemy **men** by the short leap **forwards**, but
  adjacent enemy **ladies** by the short leap **backwards**."* A man may chain
  several leaps in one move; **majority applies** (*"one must take the greatest
  number, as in International Checkers"*).
- Reaching the opponent's back rank promotes — **to a lady if you have none,
  otherwise to a sleeping beauty**. *"Promotion always ends the move"*, so a
  capture chain stops the instant a man lands on the back rank.

## Ladies (kings)
- Move **one square** in any diagonal direction (like the English-draughts king —
  *not* a flying king).
- Capture in **two mutually exclusive ways**:
  - **Replacement** (Ferz-style): step onto an adjacent enemy square, taking
    exactly **one** piece. *"Capturing by replacement is not compulsory."*
  - **Jumping** (king short-leap, any direction, chainable). *"Capturing by
    jumping is [compulsory]."*
- **Jumping takes precedence over replacement**, *"unless a lady can capture the
  opponent's lady. Then the lady that captures has the choice between both ways of
  capturing, which is called **Royal Privilege**."* Among jumps you must still take
  the **greatest number possible** (majority; the types of pieces are irrelevant).

## The one-lady rule and the sleeping beauty
- *"A player can never have two or more ladies at the same time."*
- A **sleeping beauty** (a man that promoted while you already held a lady, turned
  upside-down onto its green felt) *"may not move or capture, nor may she be
  captured"* — she also may not be jumped over. A beauty can only ever sit on the
  promotion rank (**rank 8 = White's, rank 1 = Black's**), which fixes her owner.

## Waking and the jump of joy
- *"A player must wake a sleeping beauty (if he has one) when he has lost his lady
  in his opponent's last move. She then becomes the lady. This does not count as a
  move."* If several beauties exist the player chooses which to wake.
- *"If the player moves his new lady immediately after she has been woken up, she
  is permitted to make a **jump of joy**"* — move **two squares diagonally in a
  straight line**, provided the crossed square is **(1) vacant and (2) not guarded
  by the opponent**. No capture during a jump of joy; it is available only on the
  wake turn.

## Anti-loop rule
- *"In a continuous sequence of moves in which only ladies are moved, a particular
  lady is not permitted to move onto the same square twice after the full board
  position has been repeated once."* In practice: within a run of only-lady simple
  moves, once a full-board position recurs, **no later move may recreate a position
  already seen in the run**. This makes lady endgames finite — hence no draws.

## Winning and scoring
- *"The object of the game is to leave the opponent without a valid move, either by
  capturing all his pieces, or by blocking them completely. A draw is not
  possible."*
- The **winner scores one point per piece left on the board** — *"men, ladies, and
  sleeping beauties of both colours all counting equally"* — and *"the loser gets
  zero points, even if he has still pieces left (in the case of a blockade)."*

## Implementation notes / interpretations
- **Wake turns** are modelled as: the legal moves are exactly the moves of a woken
  beauty (you must wake *and move* her; choosing which beauty to wake = choosing
  which one you move). This matches every published solution.
- **"Guarded"** (for the jump of joy) means an opponent piece could capture a lady
  standing on the crossed square (an adjacent enemy lady, or an enemy man able to
  leap it backward onto an empty square).
- A hard **ply cap** yields an honest **draw** as a pure termination backstop; it is
  never reached in real play (the anti-loop rule already bounds lady endgames).

## Move notation
Moves are `>`-separated cell paths. A **one-square** step onto an enemy square is a
replacement capture; a **two-square** step is a leap — a jump capture, or (only on a
wake turn, over an empty square) a jump of joy.

## Correctness anchor
`selftest.py` replays all **five composed problems** published with the article
(their full solution move-lists) against the move generator: the three win studies
end terminal with the exact printed margins (5, 1, 1 points), and the two "Dungeon"
/ "Castle" studies reproduce the anti-loop lock. It also checks promotion-to-beauty,
forced waking, the backward man-captures-lady leap, the jump of joy, serialization
and termination.
