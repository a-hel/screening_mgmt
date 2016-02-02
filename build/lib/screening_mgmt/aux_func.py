import math, re

def sm_shorten_name(long_name):
    """Abbreviate the name of micro-organsisms and other scientific
    names.
    
    "Escherichia coli" -> "E. coli"
    
    Argument:
    long_name -- A string. Is only processes if at least one whitespace is
                 found, otherwise the original object is returned.
    """

    try:
        parts = long_name.split(" ")
        return "{0}. {1}".format(parts[0][0].upper(), parts[1].lower())
    except (IndexError, AttributeError):
        return long_name

def sm_split_data(data, std_conc="0"):
    """Parse data strings to detect concentration and unit. Return a tuple with
    [compound, concentration, unit, original_string]
    
    Arguments:
    data -- a string, i.e. "Ciprofloxacin 5 mg/ml"
    
    Optional kwargs:
    std_conc -- Standard concentration, which will be filled in if no
                concentration can be found.
    """

    std_pattern = re.compile(r'[\d.]+\s*')
    conc_pattern = re.compile(r'\s*[\d.]+\s*(?![\S])')
    res = []

    if isinstance(data, basestring):
        data = [data]
    for d in data:
        while hasattr(d, '__iter__'):
            d = d[0]
        conc = ["","","",d]
        print std_pattern
        print std_conc
        std_pos = re.match(std_pattern, std_conc)
        if std_pos:
            pos = std_pos.span()
            conc[1] = std_conc[0: pos[1]].rstrip()
            conc[2] = std_conc[pos[1]:].lstrip()
        try:
            conc_pos_list = [x.span() for x in re.finditer(conc_pattern, d)]
        except TypeError, e:
            conc_pos_list = 0
            print "Error parsing {0}: \n {1}".format(d,e)
            continue
        if conc_pos_list:
            conc_pos = conc_pos_list[-1]
            if conc_pos[-1] < len(d):
                splitted = [d[0: conc_pos[0]].rstrip(),
                    d[conc_pos[0]:conc_pos[1]].lstrip().rstrip(),
                    d[conc_pos[1]:].lstrip()]
                for i in range(0, len(splitted)):
                    if splitted[i]:
                        conc[i] = splitted[i]
            else:
                conc[0] = d
        else:
            conc[0] = d
        conc[1] = float(conc[1])
        res.append(conc)
    return(zip(*res))

def sm_quality(signal = 1, bg = 0, signal_sd=0, bg_sd=0):
    """Get the quality parameters of a measurement and return a dict with
    S2B (signal to background), S2N (signal to noise) and Z (Z-value).
    
    Arguments:
        
    signal -- signal
    bg -- background
    signal_sd -- standard deviation of the signal
    bg_sd -- standard deviation of the background
    """
    
    return {"S2B": signal/bg,
        "S2N": (signal-bg)/math.sqrt(signal_sd**2 + bg_sd**2),
        "Z": 1-(3*(signal_sd+bg_sd)/(signal-bg))
        
        }

