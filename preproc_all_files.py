import os
import json
import argparse

parser = argparse.ArgumentParser(
                    prog='f2dace_preproc',
                    description='Preprocess files using the gnu tools',
                    epilog='')
parser.add_argument('inputfile', default="compile_commands.json", help="compile_commands.json input file.")
args = parser.parse_args()

compile_commands = None
with open(args.inputfile, "r") as f:
    compile_commands = json.load(f)
assert(type(compile_commands) == list)
for cmd in compile_commands:
    # the directory of each command is the working dir when the cmd was called
    os.chdir(cmd['directory'])
    # preprocess the file by adding -E to the compiler flags output will go to stdout always?
    preproc_cmd = cmd['arguments'].append("-E").join(" ")
    os.system(preproc_cmd)
    # get the dependency list by adding -dM to the compiler flags, output will go to the file indicated by -o 


