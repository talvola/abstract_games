# Entropy

**Designer:** Eric Solomon (1977). A two-player abstract about the eternal tension
between **Order** and **Chaos**. (Rules as implemented; see the BGG link for the
published edition.)

## Board and pieces

- A **7×7** square board (49 cells).
- A bag of **49 chips** in **7 colours**, **7 of each colour**.
- **Two roles:** **Chaos** (seat 0) and **Order** (seat 1).

## Turn structure

Play alternates, starting with Chaos, until the board is full:

1. **Chaos** draws one chip **at random** from the bag and places it on **any empty
   cell**. Chaos tries to *prevent* patterns.
2. **Order** may then **slide any one chip** horizontally or vertically, any
   distance, through empty cells, to rest in an empty cell (**no jumping** over
   other chips) — **or pass**. Order tries to *make* patterns.

When the 49th chip is placed the board is full and the game ends.

## Scoring (Order's score *S*)

For **every horizontal and vertical line**, look at every contiguous run of chips
of **length ≥ 2** that reads the **same forwards and backwards** (a *palindrome* of
colours). Each such palindrome scores points equal to **its length**. Overlapping
and nested palindromes **all count independently**. A lone chip (length 1) never
scores.

Examples (from Solomon's rulebook):

- `red–green–blue–green–red` → `green-blue-green` (3) + the whole line (5) = **8**
- `red–red–red` → `red-red` (2) + `red-red` (2) + `red-red-red` (3) = **7**

Order **maximises** *S*; Chaos **minimises** it.

## Randomness modelling (no chance node)

This platform models randomness by **rolling/drawing inside the move and storing the
outcome in state**, with no separate CHANCE node (the EinStein pattern). The chip
Chaos must place next is **drawn from the bag the moment it becomes Chaos's turn and
stored in state as `next_tile`**, so the colour is already known when Chaos chooses
where to place it (and the generic UI/bot need no chance handling). The manifest sets
`has_randomness: true`. The remaining bag composition is part of the serialized
state.

## Single-game winner (adaptation)

The published game is a **two-round match**: each player plays Order once and Chaos
once, the two Order scores are summed, and the higher total wins (draws possible). A
single round has no inherent winner — only Order's score *S*.

For this **single-package adaptation** we decide the winner against a fixed **par
threshold PAR = 30** (a roughly average Order score on a full 7×7 board against
random Chaos placement):

- Order scores **S > 30** → **Order wins**.
- Order scores **S < 30** → **Chaos wins**.
- Order scores **S = 30** → **draw**.

This preserves the game's incentives exactly — Order still maximises *S*, Chaos still
minimises it — while yielding a single-game decision. (For the authentic two-round
experience, play two games with roles swapped and compare summed Order scores.)
