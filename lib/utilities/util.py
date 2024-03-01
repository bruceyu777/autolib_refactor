from time import localtime, strftime


def current_time(ysep="", sep="", tsep=""):
    tformat = "%Y{0}%m{0}%d{1}%H{2}%M{2}%S".format(ysep, sep, tsep)
    return strftime(tformat, localtime())
