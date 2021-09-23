def convert_to_youtube_time_format(total_seconds: float) -> str:
    m, s = divmod(int(total_seconds), 60)
    h, m = divmod(m, 60)

    if h == 0 and m == 0:
        return "%02d" % (s)
    elif h == 0:
        return "%02d:%02d" % (m, s)
    return "%02d:%02d:%02d" % (h, m, s)

    # return ["%02d" % x for x in (h, m, s)]


def loading_bar(percent, length=10):
    pos = "█"
    neg = "▁"
    n_neg = round(percent * length)
    n_pos = length - n_neg
    return n_pos * pos + n_neg * neg


def get_closest(word, possibilities):
    from difflib import get_close_matches

    def clean(n):
        return "".join([c if ord(c) < 128 else "" for c in n]).lower()

    if word:
        cleaned_word = clean(word)
        cleaned_possibilities = [clean(p) for p in possibilities]

        closer_m = get_close_matches(cleaned_word, cleaned_possibilities, 1)  # list

        if closer_m:
            index = cleaned_possibilities.index(closer_m[0])
            return possibilities[index]

    return None


class Markdown:
    @staticmethod
    def bold(message):
        return "**" + message + "**"

