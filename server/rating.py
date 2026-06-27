"""Glicko-2 rating computation (pure stdlib).

Glicko-2 (Glickman, http://www.glicko.net/glicko/glicko2.pdf) is used instead of
plain Elo because this is a 205-game library where any one (player, game) pair
sees few games: Glicko-2's rating *deviation* (RD) models that uncertainty and
its *volatility* adapts the step size, so a rating is meaningful after a handful
of games and provisional ratings move fast.

We rate per (user, game_uid). A "rating period" here is a single finished
human-vs-human match — the common simplification for sparse, on-demand play.
``update_one`` takes a player's current rating and one opponent + outcome and
returns the new (rating, rd, vol). All public values are on the familiar Glicko
scale (1500 ± 350); the Glicko-2 internal scale is handled inside.

No third-party deps — safe to import anywhere in the server.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Defaults for a brand-new, unrated (user, game).
DEFAULT_RATING = 1500.0
DEFAULT_RD = 350.0
DEFAULT_VOL = 0.06

# System constant: constrains how much the volatility can change between periods.
# 0.3–1.2 per Glickman; 0.5 is the usual choice for chess-like games.
TAU = 0.5
# Glicko-2 scale factor (1500-centred Glicko scale ÷ this = Glicko-2 scale).
SCALE = 173.7178
# Convergence tolerance for the volatility solver.
EPSILON = 1e-6


@dataclass
class Rating:
    rating: float = DEFAULT_RATING
    rd: float = DEFAULT_RD
    vol: float = DEFAULT_VOL


def _g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / (math.pi * math.pi))


def _e(mu: float, mu_j: float, phi_j: float) -> float:
    return 1.0 / (1.0 + math.exp(-_g(phi_j) * (mu - mu_j)))


def update_one(player: Rating, opp: Rating, score: float, tau: float = TAU) -> Rating:
    """Return the player's new rating after ONE game vs ``opp``.

    ``score`` is the result FROM THE PLAYER'S perspective: 1.0 win, 0.5 draw,
    0.0 loss. ``opp`` is the opponent's rating BEFORE the game (rate both sides
    from the same pre-game snapshot when applying to a finished match).
    """
    # Step 2: to the Glicko-2 scale.
    mu = (player.rating - DEFAULT_RATING) / SCALE
    phi = player.rd / SCALE
    sigma = player.vol
    mu_j = (opp.rating - DEFAULT_RATING) / SCALE
    phi_j = opp.rd / SCALE

    # Step 3: estimated variance of the rating based on game outcomes.
    g_j = _g(phi_j)
    e = _e(mu, mu_j, phi_j)
    v = 1.0 / (g_j * g_j * e * (1.0 - e))

    # Step 4: estimated improvement in rating.
    delta = v * g_j * (score - e)

    # Step 5: new volatility via Illinois-algorithm root find on f(x).
    a = math.log(sigma * sigma)

    def f(x: float) -> float:
        ex = math.exp(x)
        num = ex * (delta * delta - phi * phi - v - ex)
        den = 2.0 * (phi * phi + v + ex) ** 2
        return num / den - (x - a) / (tau * tau)

    big_a = a
    if delta * delta > phi * phi + v:
        big_b = math.log(delta * delta - phi * phi - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
        big_b = a - k * tau

    fa, fb = f(big_a), f(big_b)
    while abs(big_b - big_a) > EPSILON:
        big_c = big_a + (big_a - big_b) * fa / (fb - fa)
        fc = f(big_c)
        if fc * fb <= 0:
            big_a, fa = big_b, fb
        else:
            fa /= 2.0
        big_b, fb = big_c, fc
    new_sigma = math.exp(big_a / 2.0)

    # Step 6-7: pre-rating-period RD, then new RD/rating.
    phi_star = math.sqrt(phi * phi + new_sigma * new_sigma)
    new_phi = 1.0 / math.sqrt(1.0 / (phi_star * phi_star) + 1.0 / v)
    new_mu = mu + new_phi * new_phi * g_j * (score - e)

    # Step 8: back to the Glicko scale.
    return Rating(
        rating=new_mu * SCALE + DEFAULT_RATING,
        rd=new_phi * SCALE,
        vol=new_sigma,
    )


def update_pair(a: Rating, b: Rating, score_a: float, tau: float = TAU
                ) -> tuple[Rating, Rating]:
    """Update both players of a finished 1v1 from the SAME pre-game snapshot.

    ``score_a`` is player a's result (1.0/0.5/0.0); b's is the complement.
    Returns (new_a, new_b). Pass the pre-game ratings — do not feed a's new
    rating into b's update.
    """
    new_a = update_one(a, b, score_a, tau)
    new_b = update_one(b, a, 1.0 - score_a, tau)
    return new_a, new_b
