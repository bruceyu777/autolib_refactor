from time import localtime, strftime


def current_time(ysep="", sep="", tsep=""):
    tformat = "%Y{0}%m{0}%d{1}%H{2}%M{2}%S".format(ysep, sep, tsep)
    return strftime(tformat, localtime())


def wrap_as_title(to_wrap="", width=70, fill="-"):
    if not to_wrap or len(to_wrap) > width:
        return to_wrap
    return f" {to_wrap} ".center(width, fill)
