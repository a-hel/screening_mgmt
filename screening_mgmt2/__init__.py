#!/usr/bin/python


__all__ = ["screening_mgmt","examples", "aux_func"]
__version__ = "0.1.0"


import screening_mgmt as sm
reload(sm)

def main_menu(mode="g", *args, **kwargs):
    """Start the user interface in the specified mode. Takes the argument
    'mode' and passes on args and kwargs to that function.

    c:           Command line; starts a rudimentary command line interface.
                 Mainly for debugging and maintenance use.
    g (default): Graphic; opens the graphic user interface.
    m:           Mute; no interface is loaded.
    a:           Auto; coming soon."""

    mode = mode.lower()
    if mode == "c":
        sm.console(*args, **kwargs)
    elif mode == "g":
        sm.gui(*args, **kwargs)
    elif mode == "m":
        pass
    elif mode == "a":
        sm.auto(*args, **kwargs)
    else:
        raise ValueError("Unknow mode '{0}'. Use 'c', 'g', 'm', or 'a'."
            .format(mode))

if __name__ == "__main__":
    dial = ("Welcome to Screening management.\n\n  Type 'g' for graphic " +
    "mode,'c' for command line mode, 'a' for auto mode\n  and 'm' if you " +
    "don'twant to load any interface.\n\n>> ")
    get_mode = raw_input(dial)
    main_menu(mode=get_mode)
