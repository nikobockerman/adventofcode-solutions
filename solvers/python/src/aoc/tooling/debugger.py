import sys


def is_connected() -> bool:
    try:
        if sys.gettrace() is not None:
            return True
    except AttributeError:
        pass

    try:
        if sys.monitoring.get_tool(sys.monitoring.DEBUGGER_ID) is not None:
            return True
    except AttributeError:
        pass

    return False
