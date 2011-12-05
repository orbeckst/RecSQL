"""
:mod:`recsql.export` --- Export to other file formats
=====================================================

.. autofunction:: rec2csv

"""
from __future__ import with_statement

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
        return str(x)
    latex += r"\begin{tabular}{%s}" % ("".join(["c"]*len(names)),) + "\n"  # simple c columns
    latex += r"\hline"+"\n"
    latex += " & ".join([str(x) for x in names])+r"\\"+"\n"
    latex += r"\hline"+"\n"
    for data in r:
        latex += " & ".join([translate(x) for x in data])+r"\\"+"\n"
    latex += r"\hline"+"\n"
    latex += r"\end{tabular}"+"\n"
    return latex

