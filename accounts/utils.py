from datetime import datetime, timedelta


def is_empty(input):
    if not input:
        return True

    if type(input) == str:
        return input.strip() == ""

    if type(input) == list:
        return any([is_empty(i) for i in input])

    return False
