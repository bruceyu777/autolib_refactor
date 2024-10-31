import time

from tqdm import tqdm


def current_time(ysep="", sep="", tsep=""):
    tformat = "%Y{0}%m{0}%d{1}%H{2}%M{2}%S".format(ysep, sep, tsep)
    return time.strftime(tformat, time.localtime())


def wrap_as_title(to_wrap="", width=70, fill="-"):
    if not to_wrap or len(to_wrap) > width:
        return to_wrap
    return f" {to_wrap} ".center(width, fill)


def new_progress_bar(total_time, interval):
    with tqdm(
        total=total_time,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}",
        ascii=" =->",
        ncols=80,
    ) as pbar:
        for i in range(0, total_time, interval):
            pbar.set_description(f"Remaining {total_time - i}s: ")
            pbar.update(interval)
            time.sleep(interval)


def sleep_with_progress(total_time, interval=1, logger_func=print):
    logger_func(f"\nGoing to sleep '{total_time}' seconds ")
    if total_time < 10:
        time.sleep(total_time)
    else:
        new_progress_bar(total_time, interval)
    logger_func("\n")
