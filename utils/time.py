from datetime import datetime, timezone, timedelta
from dateutil import tz

DEFAULT_TIMEZONE = tz.gettz('Europe/Berlin')


def from_timestamp(timestamp):
    utc_stamp = datetime.utcfromtimestamp(timestamp)
    aware_stamp = utc_stamp.replace(tzinfo=timezone.utc)
    return aware_stamp.astimezone(DEFAULT_TIMEZONE)


def get_local_now():
    utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
    return utc_now.astimezone(DEFAULT_TIMEZONE)


# converts utc datetime to a local representation
def get_local_strftime(utc_date, str_format):
    utc_now = utc_date.replace(tzinfo=timezone.utc)
    local_now = utc_now.astimezone(DEFAULT_TIMEZONE)
    return local_now.strftime(str_format)


# get seconds until next hour (or x hours)
def get_seconds(added_hours=1, timestamp=False, obj=False):
    now = get_local_now()
    clean = now + timedelta(hours=added_hours)
    goal_time = clean.replace(minute=0, second=0, microsecond=0)

    if obj is True:
        return goal_time

    start_time = now.replace(microsecond=0)

    if added_hours < 1:
        goal_time, start_time = start_time, goal_time

    if timestamp is True:
        return start_time.timestamp()
    else:
        return (goal_time - start_time).seconds
