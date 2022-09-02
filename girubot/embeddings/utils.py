class Unicode:
    VOID = "\u200B"


def convert_to_youtube_time_format(total_seconds: float) -> str:
    m, s = divmod(int(total_seconds), 60)
    h, m = divmod(m, 60)
    # if h == 0 and m == 0:
    #    return "%02d" % (s)
    if h == 0:
        return "%d:%02d" % (m, s)
    return "%02d:%02d:%02d" % (h, m, s)
    # return ["%02d" % x for x in (h, m, s)]

