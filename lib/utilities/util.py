import time


def current_time(ysep="", sep="", tsep=""):
    tformat = "%Y{0}%m{0}%d{1}%H{2}%M{2}%S".format(ysep, sep, tsep)
    return time.strftime(tformat, time.localtime())


def wrap_as_title(to_wrap="", width=70, fill="-"):
    if not to_wrap or len(to_wrap) > width:
        return to_wrap
    return f" {to_wrap} ".center(width, fill)


def sleep_with_print(total_time, char=".", interval=1, logger_func=print):
    logger_func(f"\nGoing to sleep '{total_time}' seconds ")
    start_time = time.time()
    while time.time() - start_time < total_time:
        logger_func(char)
        time.sleep(interval)
    logger_func("\n")
