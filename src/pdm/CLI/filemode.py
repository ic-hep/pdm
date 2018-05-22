#!/usr/bin/env python
"""
 An extension to print file mode in a human readable format.
 Borrowed from python 3 ..
 https://hg.python.org/cpython/file/3.3/Lib/stat.py
 The changes include:

 1) Importing the constants from the stat module and remove the literal constants
    present in the file.
 2) Code formatting to satisfy pylint ...

Copyright 1991-1995 by Stichting Mathematisch Centrum, Amsterdam, The Netherlands.

PSF LICENSE AGREEMENT FOR PYTHON 3.6.5

1. This LICENSE AGREEMENT is between the Python Software Foundation ("PSF"), and
   the Individual or Organization ("Licensee") accessing and otherwise using Python
   3.6.5 software in source or binary form and its associated documentation.

2. Subject to the terms and conditions of this License Agreement, PSF hereby
   grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
   analyze, test, perform and/or display publicly, prepare derivative works,
   distribute, and otherwise use Python 3.6.5 alone or in any derivative
   version, provided, however, that PSF's License Agreement and PSF's notice of
   copyright, i.e., "Copyright 2001-2018 Python Software Foundation; All Rights
   Reserved" are retained in Python 3.6.5 alone or in any derivative version
   prepared by Licensee.

3. In the event Licensee prepares a derivative work that is based on or
   incorporates Python 3.6.5 or any part thereof, and wants to make the
   derivative work available to others as provided herein, then Licensee hereby
   agrees to include in any such work a brief summary of the changes made to Python
   3.6.5.

4. PSF is making Python 3.6.5 available to Licensee on an "AS IS" basis.
   PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED.  BY WAY OF
   EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR
   WARRANTY OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE
   USE OF PYTHON 3.6.5 WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.

5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON 3.6.5
   FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF
   MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON 3.6.5, OR ANY DERIVATIVE
   THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

6. This License Agreement will automatically terminate upon a material breach of
   its terms and conditions.

7. Nothing in this License Agreement shall be deemed to create any relationship
   of agency, partnership, or joint venture between PSF and Licensee.  This License
   Agreement does not grant permission to use PSF trademarks or trade name in a
   trademark sense to endorse or promote products or services of Licensee, or any
   third party.

8. By copying, installing or otherwise using Python 3.6.5, Licensee agrees
   to be bound by the terms and conditions of this License Agreement.

"""
from stat import S_IFLNK, S_IFREG, S_IFBLK, S_IFDIR, S_IFCHR, S_IFIFO, S_IRUSR, S_IWUSR,\
    S_IXUSR, S_ISUID, S_IRGRP, S_IWGRP, S_IXGRP, S_ISGID, S_IROTH, S_IXOTH, S_IWOTH, S_ISVTX

_filemode_table = (
    ((S_IFLNK, "l"),
     (S_IFREG, "-"),
     (S_IFBLK, "b"),
     (S_IFDIR, "d"),
     (S_IFCHR, "c"),
     (S_IFIFO, "p")),

    ((S_IRUSR, "r"),),
    ((S_IWUSR, "w"),),
    ((S_IXUSR | S_ISUID, "s"),
     (S_ISUID, "S"),
     (S_IXUSR, "x")),

    ((S_IRGRP, "r"),),
    ((S_IWGRP, "w"),),
    ((S_IXGRP | S_ISGID, "s"),
     (S_ISGID, "S"),
     (S_IXGRP, "x")),

    ((S_IROTH, "r"),),
    ((S_IWOTH, "w"),),
    ((S_IXOTH | S_ISVTX, "t"),
     (S_ISVTX, "T"),
     (S_IXOTH, "x"))
)


def filemode(mode):
    """Convert a file's mode to a string of the form '-rwxrwxrwx'."""
    perm = []
    for table in _filemode_table:
        for bit, char in table:
            if mode & bit == bit:
                perm.append(char)
                break
        else:
            perm.append("-")
    return "".join(perm)
