"""SM-2 spaced repetition algorithm implementation."""


def sm2_update(
    quality: int,
    repetitions: int,
    ease_factor: float,
    interval: int,
) -> tuple[int, float, int]:
    """
    Update SM-2 parameters based on recall quality.

    quality: 0-5
        0 = complete blackout
        1 = incorrect, familiar
        2 = incorrect, easy recall
        3 = correct with difficulty
        4 = correct with hesitation
        5 = perfect recall

    Returns (new_interval, new_ease_factor, new_repetitions).
    """
    new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.3, new_ef)

    if quality < 3:
        new_repetitions = 0
        new_interval = 1
    else:
        new_repetitions = repetitions + 1
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval * ease_factor)

    return new_interval, new_ef, new_repetitions
