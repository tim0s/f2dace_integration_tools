import argparse
import sqlite3
import re
import os
from glob import glob
import networkx as nx
import matplotlib.pyplot as plt




def init_db():
  con = sqlite3.connect("icon.db")
  cur = con.cursor()
  cur.execute("DROP TABLE IF EXISTS files;")
  cur.execute("DROP TABLE IF EXISTS errors;")
  cur.execute("DROP TABLE IF EXISTS dependencies;")
  cur.execute("CREATE TABLE files(id INTEGER PRIMARY KEY, name TEXT, extension TEXT, path TEXT, size INTEGER, lines INTEGER);")
  cur.execute("CREATE TABLE errors(id INTEGER PRIMARY KEY, file_id INTEGER, error_text TEXT, error_class TEXT);")
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


def add_dependency(src, dep, cur=None, con=None):
  if cur is None:
    con = sqlite3.connect("icon.db")
    cur = con.cursor()
  src = find_file_id(src, cur)
  dep = find_file_id(dep, cur)
  if (src is not None) and (dep is not None):
    if src != dep:
      cur.execute(f"INSERT INTO dependencies (src_id, dep_id) VALUES ({src}, {dep});")
  con.commit()

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
  

def generate_build_order():
  con = sqlite3.connect("icon.db")
  cur = con.cursor()
  res = cur.execute(f"SELECT src_id, dep_id FROM dependencies;")
  r = res.fetchall()
  G = nx.DiGraph()
  G.add_edges_from(r)
  r = nx.dfs_postorder_nodes(G)
  return r

def compile_fid(file_id, srcdir):
  con = sqlite3.connect("icon.db")
  cur = con.cursor()
  res = cur.execute(f"SELECT path, name, extension FROM files WHERE id == {file_id};")
  r = res.fetchall()
  path = f"{r[0][0]}/{r[0][1]}.{r[0][2]}"
  res = os.system(f"python3 ./compile_fortran.py {srcdir} ./sdfgs")
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
build_order = generate_build_order()
for fid in build_order:
   error = compile_fid(fid, args.srcdir)

# produce reports
# TODO

