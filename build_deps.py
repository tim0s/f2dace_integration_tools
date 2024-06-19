import argparse
import sqlite3
import re
import os
from glob import glob
import networkx as nx
import subprocess



def init_db():
  con = sqlite3.connect("icon.db")
  cur = con.cursor()
  cur.execute("DROP TABLE IF EXISTS files;")
  cur.execute("DROP TABLE IF EXISTS results;")
  cur.execute("DROP TABLE IF EXISTS dependencies;")
  cur.execute("CREATE TABLE files(id INTEGER PRIMARY KEY, name TEXT, extension TEXT, path TEXT, size INTEGER, lines INTEGER);")
  cur.execute("CREATE TABLE results(id INTEGER PRIMARY KEY, file_id INTEGER, retval INTEGER, output TEXT, error TEXT, compile_start INTEGER, compile_end INTEGER);")
  cur.execute("CREATE TABLE dependencies(id INTEGER PRIMARY KEY, src_id INTEGER, dep_id INTEGER);")
  con.commit()

def populate_src_db(src_files, base_path):
  con = sqlite3.connect("icon.db")
  cur = con.cursor()
  for src_file in src_files:
    full_path = f"{base_path}{src_file}"
    # split scr_file into components
    m = re.match("(.*)/(.*)\.(.*)", full_path)
    assert(m)
    path = m[1]
    name = m[2]
    extension = m[3]
    # get size and number of lines
    size = os.path.getsize(full_path)
    lines = 0
    with open(full_path, "rb") as f:
      lines = sum(1 for _ in f)
    cur.execute(f"INSERT INTO files (name, extension, path, size, lines) VALUES (\"{name}\", \"{extension}\", \"{path}\", {size}, {lines});")
  con.commit()

def parse_filelist(flist):
  flist = flist.strip()
  flist = flist.split(" ")
  return flist


def find_file_id(fname, cur):
  res = cur.execute(f"SELECT id FROM files WHERE name == \"{fname}\";")
  r = res.fetchall()
  if (len(r)==1):
    return r[0][0]
  elif (len(r)==0):
    return None
  else:
    raise ValueError("There seem to be multiple files with the same name!")


def add_dependency(src, dep, cur, con):
  src = find_file_id(src, cur)
  dep = find_file_id(dep, cur)
  if (src is not None) and (dep is not None):
    if src != dep:
      cur.execute(f"INSERT INTO dependencies (src_id, dep_id) VALUES ({src}, {dep});")


def parse_dep(dep_file):
  con = sqlite3.connect("icon.db")
  cur = con.cursor()
  with open(dep_file, "r") as df:
    lines = df.readlines()
    for line in lines:
      lhs, rhs = line.split(":")
      lhs = parse_filelist(lhs)
      rhs = parse_filelist(rhs)
      for l in lhs:
        for r in rhs:
          l = l.split('.')[0]
          r = r.split('.')[0]
          l = l.split('/')[-1]
          r = r.split('/')[-1]
          add_dependency(l,r, cur, con)
  con.commit()
  con.close()
  

def generate_build_order():
  con = sqlite3.connect("icon.db")
  cur = con.cursor()
  res = cur.execute(f"SELECT src_id, dep_id FROM dependencies;")
  r = res.fetchall()
  G = nx.DiGraph()
  G.add_edges_from(r)
  r = nx.dfs_postorder_nodes(G)
  con.close()
  return list(r)

def compile_fid(file_id, srcdir):
  con = sqlite3.connect("icon.db")
  cur = con.cursor()

  # these should be replaced by the code below
  output = "no output obtained"
  retval = 42
  error_class = "undef"

  # check if all deps of this file have compiled successfully, otherwise mark this one as failed
  # due to dependencies - we gurantee that files are built in an order where dependencies are always
  # compiled first
  run_compile = True   #assume all deps are avail, check below
  res = cur.execute(f"SELECT dep_id FROM dependencies WHERE src_id == {file_id};")
  r = res.fetchall()
  flat = [x[0] for x in r]
  print(f"dependencies for {str(file_id)} are {str(flat)}")
  for dep_id in flat:
    res = cur.execute(f"SELECT retval FROM results WHERE file_id == {dep_id};")
    r = list(res.fetchall())
    assert(len(r) == 1)
    if r[0][0] > 0:
      print(f"dependency {str(dep_id)} compiled with retval {str(r)} (non-zero) thus bailing out")
      output = "None, did not run."
      error_class = "dependency"
      retval = 255
      run_compile = False
      break

  if run_compile:
      res = cur.execute(f"SELECT path, name, extension FROM files WHERE id == {file_id};")
      r = res.fetchall()
      path = f"{r[0][0]}/{r[0][1]}.{r[0][2]}"
      cmd = f"python3 ./compile_fortran.py {srcdir} {path} ./sdfgs"
      try:
        res = subprocess.run(cmd, shell=True, capture_output=True, timeout=180)
        output = "Stderr:\n" + str(res.stderr) + "\n\nStdout:\n" + str(res.stdout)
        retval = res.returncode
        if retval == 0:
          print(f"Compile finished without error. Output: {output}")
          error_class = "success"
        else:
          error_class = "compile_error"
          print("Compile finished with non-zeoro exit code, output: "+output)
      except subprocess.TimeoutExpired:
        output = "Stderr:\n" + str(res.stderr) + "\n\nStdout:\n" + str(res.stdout)
        error_class = "timeout"
        print("Compile finished with timeout, output: "+output)

  cur.execute(f"INSERT INTO results (file_id, retval, output, error) VALUES (?,?,?,?);", (file_id, retval, output, error_class))
  con.commit()
  con.close()
  return None


parser = argparse.ArgumentParser(
                    prog='f2dace_depbuilder',
                    description='Build a dependency graph from a source tree',
                    epilog='')
parser.add_argument('srcdir', help="source directory with .d files")
args = parser.parse_args()

init_db()

# add all source files to a db
print("Processing FORTRAN sources...")
src_files = []
for filename in glob(f"**/*.f90", root_dir=args.srcdir, recursive=True):
    src_files.append(filename)
populate_src_db(src_files, os.path.join(os.getcwd(),args.srcdir))
print(str(len(src_files))+ " added to database.")

# add all deps to a db
print("Processing dependencies...")
dep_files = []
for filename in glob(f"**/*.d", root_dir=args.srcdir, recursive=True):
    dep_files.append(filename)
for dep_file in dep_files:
  parse_dep(os.path.join(args.srcdir, dep_file))
print("done.")


# compile each file (bottom up in the dep tree)
print("Compiling all source files")
build_order = generate_build_order()
for idx,fid in enumerate(build_order):
  print(f"Compiling {idx} of {len(build_order)}")
  compile_fid(fid, args.srcdir)
print("Compilation complete")

# produce reports
# TODO

