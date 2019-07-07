
from math import log
from functools import reduce
import dateutil
import arrow

def print_table(rows, column_names=None):
    """Taken a list of columns and prints a table where column are spaced automatically"""

    # calculates the max width for every column
    widths = list(reduce(lambda a, b: [max(ac, bc) for ac, bc in zip(a, b)],
                         map(lambda row: map(len, row), rows)))

    justify_right = [False] * len(widths)

    if column_names:
        # allows for justifying column to right, or left, by prepending > or < to column name
        cleaned_columns = []
        for i, name in enumerate(column_names):
            if name[0:1] in ('<', '>'):
                if name[0:1] == '>':
                    justify_right[i] = True
                cleaned_columns.append(name[1:])
            else:
                cleaned_columns.append(name)

        column_names = cleaned_columns

        # recalcualte width including column names (could be longer than column values)
        widths = [max(a, b) for a, b in zip(widths, map(len, column_names))]

        print(' | '.join((column.ljust(widths[i]) for i, column in enumerate(column_names))).rstrip(' '))

        sep = '-' * (widths[0] + 1)

        for width in widths[1:-1]:
            sep += '|' + ('-' * (width+2))

        if len(widths) > 1:
            sep += '|' + ('-' * (min(widths[-1]+2, 50)))  # limit last column seperator width

        print(sep.rstrip(' '))

    for row in rows:
        print(' | '.join((getattr(column, 'rjust' if justify_right[i] else 'ljust')(widths[i])
                          for i, column in enumerate(row))).rstrip(' '))

def fmt_size(size, decimal_places=0):
    """Format size in bytes into friendly format"""

    suffixes = 'B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'
    power = 0

    if size > 0:
        power = int(log(size, 1000))

        if power:
            size = size / (1000 ** power)

    return ("{:."+str(decimal_places)+"f} {}").format(size, suffixes[power])

def fmt_duration(seconds):
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if hours and minutes:
        return "{:.0f}h {:.0f}m {:.0f}s".format(hours, minutes, seconds)
    elif minutes:
        return "{:.0f}m {:.0f}s".format(minutes, seconds)
    else:
        return "{:.0f}s".format(seconds)

def fmt_datetime(timestamp, utc=False):
    if utc:
        return arrow.get(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
    else:
        return arrow.get(timestamp).to(dateutil.tz.gettz()).strftime('%Y-%m-%d %H:%M:%S %Z')
