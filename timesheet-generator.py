#!/usr/bin/python

import sys
import argparse
import re

import random
from datetime import timedelta, datetime, time, date

class TimeOfDay(time):
    def __new__(cls, hour=0, minute=0, second=0, microsecond=0):
        self = time.__new__(cls, hour, minute, second,
                                                microsecond, None)
        return self

    def __add__(self, other):
        "Add TimeOfDay and timedelta"
        if not isinstance(other, timedelta):
            return NotImplemented

        delta = timedelta(hours=self.hour, minutes=self.minute,
                            seconds=self.second,
                            microseconds=self.microsecond)

        delta += other

        if delta.days != 0:
            raise OverflowError("result out of range")

        hour, rem = divmod(delta.seconds, 3600)
        minute, second = divmod(rem, 60)

        return TimeOfDay(hour, minute, second, delta.microseconds)

    __radd__ = __add__

    def __sub__(self, other):
        "Subtract two TimeOfDays or a TimeOfDay and a timedelta"
        if isinstance(other, timedelta):
            return self + -other

        if not isinstance(other, TimeOfDay):
            return NotImplemented

        if other > self:
            raise OverflowError("result out of range")

        delta_self = timedelta(hours=self.hour, minutes=self.minute,
                                seconds=self.second,
                                microseconds=self.microsecond)
        delta_other = timedelta(hours=other.hour, minutes=other.minute,
                                seconds=other.second,
                                microseconds=other.microsecond)
        return delta_self - delta_other


class Calendar:
    def __init__(self, firstday, days, holiday_list):
        self._firstday = firstday
        self._days = days
        self._holiday_list = holiday_list

    def is_weekend(self, day):
        return day.weekday() == 5 or day.weekday() == 6

    def is_holiday(self, day):
        return day in self._holiday_list

    def worked_days(self):
        total = 0
        day = self._firstday
        for i in range(self._days):
            if not self.is_weekend(day) and not self.is_holiday(day):
                total += 1
            day += timedelta(days=1)
        return total


MAX_CLOCK_OUT_TIME = TimeOfDay(hour=22)
MIN_WORKING_TIME_PER_DAY = timedelta(hours=6, minutes=48)
MAX_WORKING_TIME_PER_DAY = timedelta(hours=10, minutes=48)
DAILY_WORKTIME= timedelta(hours=8, minutes=48)

class Timesheet:
    _max_clockout = MAX_CLOCK_OUT_TIME
    _min_working_time = MIN_WORKING_TIME_PER_DAY
    _max_working_time = MAX_WORKING_TIME_PER_DAY
    _daily_worktime = DAILY_WORKTIME
    _table = []

    def __init__(self, lunch_break, lunch_duration, earlier_clockin,
                    later_clockin):
        self._lunch_break = lunch_break
        self._lunch_duration = lunch_duration
        self._earlier_clockin = earlier_clockin
        self._later_clockin = later_clockin

    def _generate_day(self, working_time):
        clockin = random_time(self._earlier_clockin, self._later_clockin)
        clockout = clockin + self._lunch_duration + working_time

        if clockout > self._max_clockout:
            delta = clockout - self._max_clockout
            clockin -= delta # No problem if clockin < _earlier_clockin
            clockout = self._max_clockout

        return [clockin, self._lunch_break, self._lunch_duration, clockout]

    def generate(self, worked_days, balance):
        worked_time = worked_days * self._daily_worktime + balance
        # In order to have an integer average_worked value, we have to remove
        # some minutes from worked_time variable. These are the remaining_min.
        # They will be added to working time progressively, one per day
        remaining_min = (worked_time.total_seconds() / 60) % worked_days
        average_worked = ((worked_time - timedelta(minutes=remaining_min)) /
                            worked_days)

        # Generate 2 days per iteraction
        for i in range(worked_days / 2):
            # The first day has a random working time
            worked_day1 = random_time(self._min_working_time,
                                        self._max_working_time)
            # The following day has the complement to keep the average
            worked_day2 = (2 * average_worked) - worked_day1

            if remaining_min:
                worked_day1 += timedelta(minutes=1)
                remaining_min -= 1
            self._table.append(self._generate_day(worked_day1))

            if remaining_min:
                worked_day2 += timedelta(minutes=1)
                remaining_min -= 1
            self._table.append(self._generate_day(worked_day2))

        # If odd number of days, the last day has the average working time
        if worked_days % 2 == 1:
            self._table.append(self._generate_day(average_worked))

    def pop(self):
        return tuple(self._table.pop())

def print_worked_day(clockin, lunch_break, lunch_break_duration, clockout):
    back_from_lunch = lunch_break + lunch_break_duration
    print("%s\t%s\t%s\t%s" % (clockin.strftime("%I:%M:%S %p"),
                                lunch_break.strftime("%I:%M:%S %p"),
                                back_from_lunch.strftime("%I:%M:%S %p"),
                                clockout.strftime("%I:%M:%S %p")))

def print_holiday():
    print("x\t\t\t")

def print_weekend_day():
    print("\t\t\t")

def trunc_to_interval(num, min_, max_):
    if num < min_:
        num = min_
    elif num > max_:
        num = max_
    return num

def random_time(min_, max_):
    delta_max = (max_ - min_).total_seconds() / 60
    mu = delta_max / 2
    sigma = delta_max / 10
    delta = trunc_to_interval(int(random.gauss(mu, sigma)), 0, delta_max)
    return min_ + timedelta(minutes=delta)

def parseSignedTimeArg(time):
    timeFormat = re.compile('^[pn]\d{1,2}:\d{2}$')
    if not timeFormat.match(time):
        raise argparse.ArgumentTypeError("Wrong time format!")
    return time

def parseTimeArg(time):
    timeFormat = re.compile('^\d{1,2}:\d{2}$')
    if not timeFormat.match(time):
        raise argparse.ArgumentTypeError("Wrong time format!")
    return time

def parseDateArg(date):
    dateFormat = re.compile('^\d{1,2}/\d{1,2}/\d{2}$')
    if not dateFormat.match(date):
        raise argparse.ArgumentTypeError("Wrong date format!")
    return date

def parseDateListArg(dateList):
    for date in dateList.split(','):
        parseDateArg(date)
    return dateList

def parse_args(args):
    parser = argparse.ArgumentParser(description="Generate timesheet table " +
                        "based on the worked days and the desired balance",
                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("firstday", metavar="DD/MM/YY", type=parseDateArg,
                        help="First day on the timesheet table")
    parser.add_argument("totaldays", metavar="NUM_DAYS", type=int,
                        help="Number of days on the timesheet table " +
                        "including weekends and holidays")
    parser.add_argument("--balance", metavar="(p|n)HH:MM",
                        type=parseSignedTimeArg, help="Desired timesheet " +
                        "balance. Use prefix 'p' for positive balance and " +
                        "'n' for negative balance")
    parser.add_argument("--holiday-list", metavar="DD/MM/YY[,DD/MM/YY[...]]",
                        type=parseDateListArg, help="List of holidays")
    parser.add_argument("--lunch-break", metavar="HH:MM", type=parseTimeArg,
                        default="12:30", help="Lunch time")
    parser.add_argument("--lunch-duration", metavar="N", type=int, default=60,
                        help="Lunch duration in minutes")
    parser.add_argument("--earlier-clockin-time", metavar="HH:MM",
                        type=parseTimeArg, default="9:00", help="Earlier " +
                        "time for clock-in")
    parser.add_argument("--later-clockin-time", metavar="HH:MM",
                        type=parseTimeArg, default="10:00", help="Later time " +
                        "for clock-in")

    return parser.parse_args(args)

def main():
    args = parse_args(sys.argv[1:])

    firstday = datetime.strptime(args.firstday, "%d/%m/%y")

    totaldays = int(args.totaldays)

    holiday_list = []
    if args.holiday_list:
        for holiday in args.holiday_list.split(','):
            holiday_list.append(datetime.strptime(holiday, "%d/%m/%y"))

    (h, m) = args.lunch_break.split(':')
    lunch_break = TimeOfDay(int(h), int(m))

    lunch_break_duration = timedelta(minutes=args.lunch_duration)

    (h, m) = args.earlier_clockin_time.split(':')
    earlier_clockin = TimeOfDay(int(h), int(m))

    (h, m) = args.later_clockin_time.split(':')
    later_clockin = TimeOfDay(int(h), int(m))

    balance = timedelta()
    if args.balance:
        signal = 1 if args.balance[0] == 'p' else -1
        (balance_hours, balance_minutes) = args.balance[1:].split(':')
        balance = signal * timedelta(hours=int(balance_hours),
                                        minutes=int(balance_minutes))

    calendar = Calendar(firstday, totaldays, holiday_list)

    timesheet = Timesheet(lunch_break, lunch_break_duration, earlier_clockin,
                            later_clockin)

    timesheet.generate(calendar.worked_days(), balance)

    day = firstday
    for i in range(totaldays):
        if calendar.is_holiday(day):
            print_holiday()
        elif calendar.is_weekend(day):
            print_weekend_day()
        else:
            (clockin, lunch, lunch_dur, clockout) = timesheet.pop()
            print_worked_day(clockin, lunch, lunch_dur, clockout)
        day += timedelta(days=1)

    print ("\nPaste this output on the spreadsheet. The rows marked with\n" +
            "'x' reference to holidays. You must mark the actual holiday\n" +
            "column manually.")

if __name__ == "__main__":
    main()
