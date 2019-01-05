from os import path

def paramDict(filename, *a):
    """A simple parameter file with lines of the form
        key [value] ..., return a dict.
       Handle %includes recursively."""

    d = {}
    dir = path.dirname(filename)

    try:
        ll = open(filename).readlines()
    except:
        ll = open(filename + '.param').readlines()
    for l in ll:
        # Ignore all past a '#'
        l = l.partition('#')[0].split()
        if len(l) == 0:
            continue

        # Get the name and any values.
        name = l.pop(0)
        ll = []
        for x in l:
            try:
                x = float(x)
            except ValueError:
                pass
            ll.append(x)
        if name == '%include':
            fname = ll[0]
            if fname[0] != '/':
                fname = path.join(dir, fname)
            dd = paramDict(fname, 1)
            d.update(dd)
        else:
            d[name] = ll

    # If this is a recursive call don't do the following conversion.

    if len(a) != 0:
        return d

    # Finally, convert any singleton lists into just the first element.

    for k in d:
        if len(d[k]) == 1:
            d[k] = d[k][0]

    return d
