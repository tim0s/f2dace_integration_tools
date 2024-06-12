import os
import re
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
    args_copy = cmd['arguments']
    # the directory of each command is the working dir when the cmd was called
    os.chdir(cmd['directory'])

    # figure out the filenames for deps and preprocessed source
    assert(type(cmd['file']) == str)
    m = re.match("^(.+)(\..+?)$", cmd['file'])
    assert(m is not None)
    preproc_outfile = f"{m[1]}_preprocessed{m[2]}"
    deps_outfile = f"{m[1]}.d"
    
    # preprocess the file by adding -E -cpp to the compiler flags 
    print(f"Preprocessing {m[1]}{m[2]}\n output will go to {preproc_outfile}")
    for i,arg in enumerate(cmd['arguments']):
      if arg == '-o':
        cmd['arguments'][i+1] = preproc_outfile
    args = cmd['arguments'] + [f"-E -cpp"]
    preproc_cmd = " ".join(args)
    print("Running: "+preproc_cmd)
    os.system(preproc_cmd)
    cmd['arguments'] = args_copy

    # get deps by adding -dM to the compiler flags --- this does not generate deps???
    #print(f"Generating dependencies for {m[1]}{m[2]}\n output will go to {deps_outfile}")
    #for i,arg in enumerate(cmd['arguments']):
    #  if arg == '-o':
    #    cmd['arguments'][i+1] = deps_outfile
    #args = cmd['arguments'] + [f"-dM"]
    #preproc_cmd = " ".join(args)
    #print("Running: "+preproc_cmd)
    #os.system(preproc_cmd)



