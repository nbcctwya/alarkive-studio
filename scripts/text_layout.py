"""Pixel-based English wrapping, keeping words and their highlight spans intact."""
import re


def word_wrap(text, draw, font, max_width, flags=None, per_character=False,
              balance_two_lines=False):
    """Return (text, character flags, width) rows; never split a word to make it fit.

    Title rendering draws characters separately, while subtitle rendering draws
    whole lines with kerning. Measure with the matching method in each case.
    Oversized words remain intact so the caller can shrink or report overflow.
    """
    flags = flags if flags is not None else [False] * len(text)

    def width(value):
        if per_character:
            return sum(draw.textlength(ch, font=font) for ch in value)
        return draw.textlength(value, font=font)

    rows, current, current_flags = [], "", []
    for match in re.finditer(r"\S+", text):
        word = match.group()
        word_flags = flags[match.start():match.end()]
        candidate = f"{current} {word}" if current else word
        if current and width(candidate) > max_width:
            rows.append((current, current_flags, width(current)))
            current, current_flags = word, word_flags
        else:
            current_flags = (current_flags + [False] + word_flags
                             if current else word_flags)
            current = candidate
    if current:
        rows.append((current, current_flags, width(current)))
    if balance_two_lines and len(rows) == 2:
        # Avoid a nearly full first line followed by a single orphan word.
        joined = rows[0][0] + " " + rows[1][0]
        joined_flags = rows[0][1] + [False] + rows[1][1]
        best = abs(rows[0][2] - rows[1][2])
        for gap in re.finditer(r" ", joined):
            left, right = joined[:gap.start()], joined[gap.end():]
            left_w, right_w = width(left), width(right)
            difference = abs(left_w - right_w)
            if max(left_w, right_w) <= max_width and difference < best:
                rows = [(left, joined_flags[:gap.start()], left_w),
                        (right, joined_flags[gap.end():], right_w)]
                best = difference
    return rows
