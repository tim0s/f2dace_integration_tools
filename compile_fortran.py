from fparser.common.readfortran import FortranStringReader
from fparser.common.readfortran import FortranFileReader
from fparser.two.parser import ParserFactory
import sys, os
import argparse
import numpy as np

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from dace import SDFG, SDFGState, nodes, dtypes, data, subsets, symbolic
from dace.frontend.fortran import fortran_parser
from fparser.two.symbol_table import SymbolTable

import dace.frontend.fortran.ast_components as ast_components
import dace.frontend.fortran.ast_transforms as ast_transforms
import dace.frontend.fortran.ast_utils as ast_utils
import dace.frontend.fortran.ast_internal_classes as ast_internal_classes


def find_path_recursive(base_dir):
    dirs = os.listdir(base_dir)
    fortran_files = []
    for path in dirs:
        if os.path.isdir(os.path.join(base_dir, path)):
            fortran_files.extend(find_path_recursive(os.path.join(base_dir, path)))
        if os.path.isfile(os.path.join(base_dir, path)) and (path.endswith(".F90") or path.endswith(".f90")):
            fortran_files.append(os.path.join(base_dir, path))
    return fortran_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            prog = "F2DaCe ICON Driver",
            )
    parser.add_argument("basedir", help="Path to root of the source dir")
    parser.add_argument("infile", help="Input file to compile")
    parser.add_argument("outfile", help="Where to place the output SDFG")
    args = parser.parse_args()

    fortran_files = find_path_recursive(args.basedir)
    inc_list = [args.basedir + "/include"]
    
    sdfg = fortran_parser.create_sdfg_from_fortran_file_with_options(
        args.infile,
        include_list=inc_list,
        source_list=fortran_files,
        icon_sources_dir=args.basedir,
        icon_sdfgs_dir=args.outfile,
        normalize_offsets=True)

    #sdfg.view()
