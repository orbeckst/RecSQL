"""
:mod:`recsql.export` --- Export to other file formats
=====================================================

Simple functions to export a :class:`numpy.rec.array` to another
format.

.. autofunction:: rec2csv

.. autofunction:: rec2latex

.. autofunction:: s_rec2latex

"""
from __future__ import with_statement, absolute_import

def rec2csv(r, filename):
    """Export a recarray *r* to a CSV file *filename*"""
    names = r.dtype.names
    def translate(x):
        if x is None or str(x).lower == "none":
            x = ""
        return str(x)
    with open(filename, "w") as csv:
        csv.write(",".join([str(x) for x in names])+"\n")
        for data in r:
            csv.write(",".join([translate(x) for x in data])+"\n")
    #print "Wrote CSV table %r" % filename
    return filename

def latex_quote(s):
    """Quote special characters for LaTeX.

    (Incomplete, currently only deals with underscores, dollar and hash.)
    """
    special = {'_':r'\_', '$':r'\$', '#':r'\#'}
    s = str(s)
    for char,repl in special.items():
        new = s.replace(char, repl)
        s = new[:]
    return s

def rec2latex(r, filename, empty=""):
    """Export a recarray *r* to a LaTeX  table in *filename*"""
    with open(filename, "w") as latex:
        latex.write(s_rec2latex(r, empty=empty))
    return filename

def s_rec2latex(r, empty=""):
    """Export a recarray *r* to a LaTeX  table in a string"""
    latex = ""
    names = r.dtype.names
    def translate(x):
        if x is None or str(x).lower == "none":
            x = empty
        return latex_quote(x)
    latex += r"\begin{tabular}{%s}" % ("".join(["c"]*len(names)),) + "\n"  # simple c columns
    latex += r"\hline"+"\n"
    latex += " & ".join([latex_quote(x) for x in names])+r"\\"+"\n"
    latex += r"\hline"+"\n"
    for data in r:
        latex += " & ".join([translate(x) for x in data])+r"\\"+"\n"
    latex += r"\hline"+"\n"
    latex += r"\end{tabular}"+"\n"
    return latex

