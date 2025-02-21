import re
from collections import defaultdict

from lib.utilities import wrap_as_title

LINE_SEP_WIDTH = 70
DEFAULT_PID = "00000"
HD_DKILL = "Daemon Kills"
HD_CRASH = "Crash(es)"
HD_CONSERVE = "Conserve Mode"
INDICATOR = {
    HD_DKILL: {
        r" the killed daemon is ",
    },
    HD_CRASH: {
        r"> firmware ",
    },
    HD_CONSERVE: {
        "conserve mode",
    },
}


class CrashLog:
    exclude_daemon = ["/bin/getty"]

    def __init__(self, log, indicator=None):
        indicator = indicator or INDICATOR
        self.original = log.splitlines()
        self.indicator = indicator
        self.daemon_kills = defaultdict(list)
        self.crashes = defaultdict(list)
        self.conserve_mode = {}
        self.formatted_logs = {}
        self._parse()

    def _parse(self):
        # this function should only called once
        crash_buf = {}
        conserve_buf = {}
        for line in self.original:
            case, index = self.pre_screen(line)
            timestamp, pid = self.check_crash_time(line)
            # indication lines
            if case == HD_DKILL:
                self.daemonlog(line, index)
            elif case == HD_CRASH:
                # if found new crash and crash_buf already have content, then need to
                # add to crashlog
                if crash_buf:
                    self.crashlog(crash_buf)
                # initiate crash_buf as new crash found
                crash_buf = {"time": timestamp, "pid": pid, "buffer": [line]}
            elif case == HD_CONSERVE:
                if conserve_buf:
                    self.conservelog(conserve_buf)
                conserve_buf = {"time": timestamp, "pid": pid, "buffer": [line]}
            elif crash_buf:
                # others: crash content, conserve followed lines, others
                # for corner case like below:
                # 3: 2018-08-28 15:21:01 <00057> firmware FortiGate-30D v6.0.0,build0182b0182,180825
                # (interim) (Release)
                # 4: 2018-08-28 15:21:02 <00057> application newcli
                # for corner case like below:
                # 53: 2019-07-11 20:47:22 <00919> [0x00437cff] => /bin/ipsengine
                # 54: 2019-07-11 20:47:22 <00919> [0x7f4dc96deeaa] => /usr/lib/x86_64-linux-gnu/libc.so.6
                # 55: 2019-07-11 20:47:22 (__libc_start_main+0x000000ea) liboffset 00020eaa
                # 56: 2019-07-11 20:47:22 <00919> [0x0042dc7a] => /bin/ipsengine
                # 57: 2019-07-11 20:47:22 <00923> firmware FortiGate-501E v6.2.1,build0931b0931,190711 (interim)
                # 58: 2019-07-11 20:47:22 (Release)
                # 59: 2019-07-11 20:47:22 <00923> application ipsengine 05.000.023
                # 60: 2019-07-11 20:47:22 <00923> *** signal 14 (Alarm clock) received ***

                # if current pid equals to crash_buf buffered pid or
                # can't find a pid but current time eqauls to crash_buf time
                # then add line to buffered buffer
                # if not mets above conditions, then need to add current buffer to
                # crashlog and reset crash_buf
                if pid == crash_buf["pid"] or (
                    pid == DEFAULT_PID and timestamp == crash_buf["time"]
                ):
                    crash_buf["buffer"].append(line)
                else:
                    self.crashlog(crash_buf)
                    crash_buf = {}
            # conserve mode lines don't have pid
            elif conserve_buf and timestamp == conserve_buf["time"]:
                conserve_buf["buffer"].append(line)
            else:
                continue
        # in case the crash log is ended at the last line, then we also need to save the crash log
        if crash_buf:
            self.crashlog(crash_buf)
        if conserve_buf:
            self.conservelog(conserve_buf)
        ret = (self.daemon_kills, self.crashes, self.conserve_mode)
        return ret

    @staticmethod
    def check_crash_time(crashed_line):
        """
        grab crash time from a 'line
        1397: 2018-12-26 16:18:29 <00241> RAX: 0000000000000000 RBX: 0000000000000000
        """
        crash_log_cont = crashed_line.split()
        timestamp = ""
        pid = DEFAULT_PID
        if len(crash_log_cont) >= 4:
            timestamp = crash_log_cont[2]
            try:
                tpid = crash_log_cont[3][1:-1]
                if tpid.isdigit():
                    pid = tpid
            except IndexError:
                pass
        return timestamp, pid

    def pre_screen(self, line):
        case = "unknown"
        index = -1
        for k, patterns in self.indicator.items():
            for p in patterns:
                rule = re.compile(p)
                matched = rule.search(line)
                if matched:
                    index = matched.end()
                    case = k
                    break
            if index != -1:
                break
        return case, index

    def daemonlog(self, line, index):
        daemon = line[index:].split(": ")[0].strip()
        if daemon not in self.exclude_daemon:
            self.daemon_kills[daemon].append(line)
        return self.daemon_kills

    def crashlog(self, crash_buf):
        app_indicator = "> application "
        details = crash_buf["buffer"]
        app = "Unknown Application"
        for line in details:
            if app_indicator in line:
                try:
                    app = line.split(app_indicator)[-1]
                except IndexError:
                    break
        self.add_crash(app, "\n".join(details))

    def conservelog(self, conserve_buf):
        rule = re.compile("(enter|exit).*?conserve mode")
        details = conserve_buf["buffer"]
        timestamp = conserve_buf["time"]
        for line in details:
            matched = rule.findall(line)
            if matched:
                status = "_".join(matched).upper()
                break
        else:
            status = "UNKNOWN"
        self.conserve_mode["%s %s" % (status, timestamp)] = "\n".join(details)
        return self.conserve_mode

    def add_crash(self, app, crash):
        if app:
            self.crashes[app].append(crash)

    def dump_to_formatted_log(self):
        if HD_CRASH not in self.formatted_logs:
            self.dump_crashes()
        if HD_CONSERVE not in self.formatted_logs:
            self.dump_conserves()
        if HD_DKILL not in self.formatted_logs:
            self.dump_daemonkill()
        return self.formatted_logs

    def dump_parsed_log(self, hd_identifier):
        self.dump_to_formatted_log()
        ret = ""
        if any(self.formatted_logs.values()):
            temp = " {} Information for '%s' ".format("/".join(self.indicator.keys()))
            title = (temp % hd_identifier).center(LINE_SEP_WIDTH - 1, "-")
            ret = "\n#{}{}{}{}".format(title, *self.formatted_logs.values())
        return ret

    def dump_daemonkill(self, start_count=3):
        daemonkills = (
            self.filter_daemonkill(start_count) if start_count else self.daemon_kills
        )
        formatted = ""
        if daemonkills:
            temp = " Deamon '{}' Killed '{}' Time(s) "
            for daemon, kills in daemonkills.items():
                formatted += "\n\n%s\n" % wrap_as_title(temp).format(daemon, len(kills))
                formatted += "\n".join(kills)
            formatted = "\n%s\n" % formatted
        self.formatted_logs[HD_DKILL] = formatted
        return formatted

    def dump_crashes(self):
        formatted = ""
        if self.crashes:
            temp = " Deamon '{}' Crashed '{}' Time(s) "
            for daemon, crashes in self.crashes.items():
                formatted += "\n\n%s\n" % wrap_as_title(
                    temp.format(daemon, len(crashes))
                )
                formatted += ("\n%s\n" % (wrap_as_title())).join(crashes)
            formatted = "\n%s\n" % formatted
        self.formatted_logs[HD_CRASH] = formatted
        return formatted

    def dump_conserves(self):
        formatted = ""
        if self.conserve_mode:
            for dump, records in self.conserve_mode.items():
                formatted += "\n\n%s\n" % wrap_as_title(" {} ".format(dump))
                formatted += records
            temp = " Conserve Mode Entered/Exited '{}' Time(s) ".format(
                len(self.conserve_mode)
            )
            formatted = "\n%s\n%s\n" % (wrap_as_title(temp), formatted)
        self.formatted_logs[HD_CONSERVE] = formatted
        return formatted

    def filter_daemonkill(self, killtimes):
        daemon_killed = {
            k: v for k, v in self.daemon_kills.items() if len(v) > killtimes
        }
        return daemon_killed
