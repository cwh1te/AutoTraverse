import requests
import os
import argparse
import textwrap
import yaml
import json
import hashlib
from bs4 import BeautifulSoup

# Default config with help and stuff
# Adding an entry here will add it to:
# - Commandline help
# - Commandline options
# - Config wizard
default_config = {
  # "name" : [
  #   "Help text.",
  #   "Setup help",
  #   type, default value, [required]
  # ]
  "url" : [
    "URL to download from.",
    "Define a URL to target",
    str, "", True
  ],
  "path" : [
    "Path to directory to save items into.",
    "Specify a path to save things to",
    str, "", True
  ],
  "depth" : [
    "Maximum depth of directories to traverse (0 for infinite).",
    "Specify a search depth to stop at",
    int, False, False
  ],
  "chunksize" : [
    "Chunk size for writing to disk (default is 4096).",
    "Specify a custom chunk size",
    int, 4096, False
  ],
  "peeksize" : [
    "How many bytes of a file to read to determine its uniqueness.",
    "Specify a minimum number of bytes to read to determine file uniqueness (default is 32768)",
    int, 32768, False
  ],
  "peekpct" : [
    "Percentage of a file to read to determine its uniqueness.",
    "What is the minimum percentage of a file that should be evaluated for uniqueness (default is 2)?",
    int, 2, False
  ],
  "--expand" : [
    "Automatically expand archives and compressed files.",
    "Do you want to expand archives?",
    bool, False, False
  ],
  "--flat" : [
    "Ignore archive directory structure.",
    "Do you want to ignore directory structure when expanding archives?",
    bool, False, False
  ],
  "--skip-cert-check" : [
    "Skip certificate checks when making HTTPS connections.",
    "Do you want to skip certificate validation when making HTTPS connections?",
    bool, False, False
  ],
  "--write-config" : [
    "Write options to config file as defaults.",
    "Do you want to save this configuration as the default?",
    bool, False, False
  ],
  "--assume-unchanged" : [
    "Make download decisions solely based on filenames and paths.",
    "Do you want to assume downloaded files will never change?",
    bool, True, False
  ],
  "--delete-superceded" : [
    "Delete files if a newer copy has been downloaded.",
    "Do you want to remove old copies of files?",
    bool, True, False
  ],
  "--progressbar" : [
    "Display a progress bar with estimated completion time.",
    "Do you want fancy progress bars?",
    bool, False, False
  ],
}

# Populate argument parser
parser = argparse.ArgumentParser(
  prog="AutoTraverse",
  formatter_class=argparse.RawDescriptionHelpFormatter,
  description=textwrap.dedent("""\
    AutoTraverse v0.4.1a
      by Caleb White
       
    Simple tool to traverse web directories and download all files contained in them.
    
    Options to auto-expand archives and compressed files."""),
  epilog="""\
Note: If you do not specify a protocol, https:// will be prepended to your URL.
  
Download all the things!"""
)

for option in default_config.keys():
  if option[:2] == "--":
    parser.add_argument(
      option,
      help=default_config[option][0],
      required=default_config[option][4],
      action="store_true",
      dest=option[2:]
    )
  elif option[:1] == "-":
    parser.add_argument(
      option,
      help=default_config[option][0],
      required=default_config[option][4],
      type=default_config[option][2],
      nargs="+",
      dest=option[1:]
    )
  else:
    parser.add_argument(
      option,
      help=default_config[option][0],
      type=default_config[option][2],
      nargs="?"
    )

parser.add_argument(
  "--moo",
  help=argparse.SUPPRESS,
  required=False,
  action='store_true',
  dest="moo")

args = parser.parse_args()

# Moo - the most important part of all this nonsense
if args.moo:
  print(textwrap.dedent("""\
           ,=    ,        =.
  _  _   /'/    )\\,/,/(_   \\`\\
   `//-.|  (  ,\\\\)\\//\\)\\/_  ) |
   //___\\   `\\\\\\/\\\\/\\/\\\\///'  /
,-\"~`-._ `\"--'_   `\"\"\"`  _ \\`'\"~-,_
\\       `-.  '_`.      .'_` \\ ,-\"~`/
 `.__.-'`/   (-\\        /-) |-.__,'
   ||   |     \\O)  /^\\ (O/  |
   `\\\\  |         /   `\\    /
the  \\\\  \\       /      `\\ /
cow   `\\\\ `-.  /' .---.--.\\
says    `\\\\/`~(, '()      ()
'moo'    /(O) \\\\   _,.-.,_)
        //  \\\\ `\\'`      /
       / |  ||   `\"\"~~~\"`
     /'  |__||
           `o """))
  exit(0)

# Load settings or use defaults
config = {}
if os.path.isfile("settings.yml"):
  config = yaml.safe_load(open("settings.yml"))
if not config:
  config = default_config.copy()

# Override default/stored values with commandline input
for option in default_config.keys():
  # Strip "--" and "-" from input names to make suitable variable names
  option_name = option[2:] if option[:2] == "--" else option
  option_name = option_name[1:] if option_name[:1] == "-" else option_name
  if getattr(args, option_name):
    if not type(getattr(args, option_name)) is default_config[option][2]:
      config[option_name] = default_config[option][2](getattr(args, option_name))
    else:
      config[option_name] = getattr(args, option_name)

# If config is default, offer first time wizard
if config == default_config:
  print("Welcome to AutoTraverse!")
  response = input("Would you like to go through initial configuration? [Y]es/[n]o ")
  if response == "" or response[0] in ["y", "Y"]:
    for option in default_config.keys():
      option_name = option[2:] if option[:2] == "--" else option
      option_name = option_name[1:] if option_name[:1] == "-" else option_name
      option_value = None
      while type(option_value) is not default_config[option][2]:
        if default_config[option][2] == bool:
          option_value = input(f"{default_config[option][1]} {'[Y]/[n]' if default_config[option][3] else '[y]/[N]'}: ")
          if option_value == "":
            option_value = default_config[option][3]
          else:
            option_value = True if option_value[0] in ["y", "Y"] else False
        else:
          option_value = input(f"{default_config[option][1]}{' (blank to skip)' if not default_config[option][4] else ''}: ")
          if option_value == "" and not default_config[option][4]:
            break
        if option_value == "" and default_config[option][4]:
          print("This option is required. Please try again.")
          option_value = None
      if option_value:
        config[option_name] = option_value

# Handle defaults that weren't overwritten
for option in default_config.keys():
  option_name = option[2:] if option[:2] == "--" else option
  option_name = option_name[1:] if option_name[:1] == "-" else option_name
  if option_name not in config.keys() or config[option_name] == default_config[option]:
    config[option_name] = default_config[option][3]

# Scrub leftover defaults
for option in [x for x in config.keys()]:
  if option[0] == "-":
    del config[option]

# Final checks and input normalizing
if not config["url"] or not config["path"]:
  print("You must specify a URL and a path.",
    f"Run python {os.path.basename(__file__)} -h for details.")
  exit(1)
if not config["url"][-1] == "/":
  config["url"] = f"{config['url']}/"
if "http://" not in config["url"] and "https://" not in config["url"]:
  config["url"] = f"https://{config['url']}"
if not os.path.isdir(config["path"]):
  try:
    os.makedirs(config["path"])
  except:
    print(f"Path does not exist and failed to create it: {config['path']}")
    exit(1)

# Write config if requested
if config["write-config"]:
  with open("settings.yml", "w") as f:
    yaml.safe_dump(config, f)

if config["progressbar"]:
  # This is only imported on demand to respect people's right to not run code from Google
  import progressbar

# Build Traverse class
class Traverse(object):
  def __init__(self, config: dict, *args, **kwargs):
    self.base_depth = config["url"].count("/") -3
    config["depth"] += self.base_depth
    self.config = config
    self.headers = {
      "Accept-Encoding": "gzip, deflate",
      "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:52.0) Gecko/20100101 Firefox/52.0"
    }

    if config["expand"] and not config["flat"]:
      print("WARNING! Archives will be expanded automatically. This combination of options should only be used with trusted sources!")

    self.manifest_file = os.path.join(config["path"], ".manifest")
    self.manifest = [DownloadFile()]
    self.cur_depth = 0

    if config["skip-cert-check"]:
      requests.packages.urllib3.disable_warnings()

    try:
      with open(self.manifest_file, "r") as f:
        self.manifest = str(f.readlines()[0]) or "[]"
        try:
          if self.manifest:
            # Some very basic attempts to clean the manifest
            while self.manifest[-1:] in ["\n", ","]:
              self.manifest = self.manifest[:-1]
            if self.manifest[0] != "[":
              self.manifest = f"[{self.manifest}]"
            #print(self.manifest)
            self.manifest = [DownloadFile(x) for x in json.loads(self.manifest)]
        except:
          print(f"Corrupted manifest: {self.manifest_file}")
          os.rename(self.manifest_file, f"{self.manifest_file}.corrupted")
          os._exit(1)
    except:
      f = open(self.manifest_file, "w")
      f.close()
    

  def traverse(self, branch: str = "") -> bool:
    if branch == "":
      print(f"Loading {self.config['url']}")
    page = requests.get(
      f"{self.config['url']}{branch}",
      headers=self.headers,
      verify=not self.config["skip-cert-check"]
    )
    if not page.ok:
      print(f"Bad response ({page.status_code}) getting directory {branch}")
      return False
    
    seen_files = [x.name for x in self.manifest if x.path == os.path.join(self.config['path'], branch)]
    
    tree = BeautifulSoup(page.text, "html.parser")
    
    for node in tree.find_all("a"):
      node_href = node.get("href")
      if node_href[0:4] == "http":
        if not self.config["url"] in node_href:
          print(f"Ignoring off-site link: {node_href}")
          continue
        if len(node_href) < len(self.config["url"]):
          continue
      if self.config["url"] in node_href:
        node_href = node_href.replace(self.config["url"], "")
      if node_href[-1] == "/":
        # Let's not backtrack
        if node_href == "../" or node_href in self.config["url"]:
          continue
        node = f"{branch}{node_href}"
        if self.config["depth"] not in [False, -1]:
          if node.count("/") > self.config["depth"]:
            continue
        print(f"{'Going deeper! ' if node.count('/') > self.cur_depth else ''}Reading {node}")
        self.cur_depth = node.count("/")
        self.traverse(node)
        continue
      # Make sure we're only following links to leaves at current depth
      if not (node_href == f"{branch}{node.contents[0]}" or node_href == node.contents[0]):
        continue
      md5 = ""
      if node_href in seen_files:
        if self.config["assume-unchanged"]:
          continue
        # Check for early byte hash differences
        manfile = [x for x in self.manifest if x.source == f"{self.config['url']}{branch}{node_href}"][0]
        peekfile = self.peek_leaf(branch, node_href, manfile)
        md5 = peekfile.peekhash
        if peekfile.peekhash == manfile.peekhash:
          continue
        # Rebuild manifest without the superceded file
        self.manifest = [x for x in self.manifest if x.peekhash != manfile.peekhash and x.source != f"{self.config['url']}{branch}{node_href}"]
        if self.config["delete-superceded"]:
          try:
            os.remove(os.path.join(manfile.path, manfile.lname))
          except:
            print(f"Failed deleting superceded file {os.path.join(manfile.path, manfile.lname)}")
      self.get_leaf(branch, node_href, md5)
    
    if branch == "":
      f = open(self.manifest_file, "w")
      f.close()
      with open(self.manifest_file, "a") as f:
        for manfile in self.manifest:
          f.write(f"{json.dumps(manfile.__dict__)},")
      print("Done!")
      return True

  def get_stream(self, target: str) -> requests.Request:
    return requests.get(
      target,
      headers=self.headers,
      stream=True,
      verify=not self.config["skip-cert-check"]
    )

  def peek_leaf(self, branch: str, leaf: str, dlfile: 'DownloadFile' = None) -> 'DownloadFile':
    """Downloads some portion of a file and returns the comparison result and MD5 hash."""
    r = self.get_stream(f"{self.config['url']}{branch}{leaf}")
    dsize = int(r.headers.get('content-length'))
    if not r.ok: return DownloadFile() # Continue on error
    if dlfile:
      peekfile = DownloadFile(dlfile.__dict__)
      if not dlfile.dsize == dsize: return dlfile
      peekfile.peeksize = dlfile.peeksize if dlfile.peeksize < dsize else dsize
      peekpct_bytes = (1/dlfile.peekpct) * dsize
    else:
      peekfile = DownloadFile({
        'peekpct' : self.config['peekpct'],
        'peeksize' : self.config['peeksize'] if self.config['peeksize'] < dsize else dsize
      })
      peekpct_bytes = (1/self.config['peekpct']) * dsize
    peekfile.dsize = dsize

    if peekpct_bytes > peekfile.peeksize: peekfile.peeksize = peekpct_bytes
    chunksize = self.config['chunksize'] if self.config['chunksize'] < peekfile.peeksize else peekfile.peeksize
    peekfile.peekhash = hashlib.md5()
    downloaded = 0
    for chunk in r.iter_content(chunk_size=chunksize):
      if chunk:
        downloaded += len(chunk)
        if downloaded <= peekfile.dsize:
          peekfile.peekhash.update(chunk)
        else:
          break
    r.close()
    peekfile.peekhash = peekfile.peekhash.hexdigest()
    return peekfile

  def get_leaf(self, branch: str, leaf: str, peekhash: str = "") -> bool:
    save_path = os.path.join(self.config['path'], branch)
    if not peekhash:
      F = self.peek_leaf(branch, leaf)
      F.name = leaf
      F.path = save_path
      F.source = f"{self.config['url']}{branch}{leaf}"
    else:
      F = DownloadFile({
        'name' : leaf,
        'path' : save_path,
        'source' : f"{self.config['url']}{branch}{leaf}",
        'peekpct' : self.config['peekpct'],
        'peeksize' : self.config['peeksize'],
        'peekhash' : peekhash,
      })
    if not os.path.exists(save_path):
      os.makedirs(save_path)
    r = self.get_stream(F.source)
    if not r.ok:
      print(f"Bad response ({r.status_code}) getting file {branch}{leaf}")
      return False
    elif not F.dsize:
      F.dsize = int(r.headers.get('content-length'))
    pbar = None
    if self.config['progressbar']:
      # Initialize progressbar
      pbar = progressbar.ProgressBar(
        widgets=[
              f"Getting file {branch}{leaf}: ",
              progressbar.Counter(),
              f"/{F.dsize} (",
              progressbar.Percentage(),
              ') ',
              progressbar.Bar(),
              progressbar.AdaptiveETA()
          ], maxval=F.dsize
      ).start()
    else:
      print(f"Getting file {branch}{leaf} ({F.dsize } bytes)...")
    # Get the file
    downloaded = 0
    with open(os.path.join(save_path, F.lname), 'wb') as f:
      for chunk in r.iter_content(chunk_size=self.config["chunksize"]):
        if chunk:
          downloaded += len(chunk)
          if downloaded <= F.dsize:
            if pbar:
              pbar.update(downloaded)
          else:
            print(f"\nWarning: Exceeded advertised size! {downloaded} > {F.dsize}")
            if pbar:
              pbar.update(F.dsize)
          f.write(chunk)
        else:
          if pbar:
            pbar.update(int(r.headers.get("content-length")))
    F.saved = True
    if pbar:
      pbar.finish()
      print()
    # Append to manifest
    self.manifest.append(F)
    # Write to disk to prevent lost information from early termination
    with open(self.manifest_file, "a") as f:
        f.write(f"{json.dumps(F.__dict__)},")
    if self.config["expand"]:
      F.extract()
    return True

class DownloadFile(object):
  def __init__(self, dlfile: dict = {}, *args, **kwargs):
    # Deserialize imported file object automagically
    self.__dict__.update(dlfile)
    # These properties always need to exist
    self.name = getattr(self, 'name', '')
    self.path = getattr(self, 'path', '')
    self.source = getattr(self, 'source', '')
    self.dsize = getattr(self, 'dsize', 0)
    # Populate other property values
    self.lname

  @property
  def lname(self) -> str:#filename
    """The local file name if saved, otherwise a dynamically generated candidate."""
    if not getattr(self, 'saved', False) or not getattr(self, '_lname', ''):
      self._lname = self.get_unique_fname(self.path, self.name)
    return self._lname
  
  @property
  def lsize(self) -> int:#bytes
    """The size of the file if saved, otherwise 0."""
    try:
      return os.path.getsize(os.path.join(self.path, self.lname))
    except: # Probably not saved, don't care
      return 0

  def get_unique_fname(self, filepath: str, filename: str) -> str:
    """Returns a unique (non-pre-existing) filename for a given filename and path."""
    basename, ext = self.get_fext(filename, extpartlim=2)
    i = 0
    while os.path.exists(os.path.join(filepath, f"{basename} ({i}){ext}" if i else filename)):
      i += 1
    return f"{basename} ({i}){ext}" if i else filename

  def get_fext(self, filename: str, extlim: int = -1, extpartlim: int = None) -> (str, str):
    """
      Returns name and extension parts for a given filename.

      Basically os.path.splitext() except recursive and with options.

      Parameters:
        filename (str): The filename to split
        extlim (int): Limit the number of characters to evaluate at a time as potential extensions
        extpartlim (int): Limit the number of extension parts to evaluate before returning
    """
    ext = ""
    extpartlim = extpartlim or filename.count('.')
    # Avoid infinite recursion
    if extlim >= len(filename): extlim = -1
    while '.' in filename[-extlim:] and ext.count('.') < extpartlim:
      filename, ext2 = os.path.splitext(filename)
      # Avoid infinite recursion
      if not ext2: break
      ext = ext2 + ext
    return filename, ext

  def extract(self, file: str = "", loop: bool = True) -> bool:
    import zipfile, gzip, tarfile, shutil

    out_files = []
    if not file:
      file = self.lname
    f_base, f_ext = os.path.splitext(file)

    # ZIP archives
    if f_ext == ".zip":
      print(f"Expanding ZIP archive {file}.")
      try:
        with zipfile.ZipFile(os.path.join(self.path, file)) as zip:
          # testzip() returns None or name of first bad file
          if zipfile.ZipFile.testzip(zip) is not None:
            print("Malformed ZIP or contents corrupted! Unable to process.")
            return False
          if self.config["flat"]:
            # Not using extractall() because we don't want a tree structure
            for member in zip.infolist():
              member = self.get_unique_fname(self.path, member)
              if self.config["flat"]:
                zip.extract(member, self.path)
              else:
                zip.extract(member)
              out_files.append(str(member))
          else:
            zip.extractall(self.path)
          # Delete the zip file now that we have its contents
        os.remove(os.path.join(self.path, file))
      except:
        print(f"Unable to expand ZIP archive {file}. You should check its headers or something.")
        return False

    # GZIP compression
    elif f_ext == ".gz":
      print(f"Expanding GZIP compressed file {file}.")
      try:
        out_fname = self.get_unique_fname(self.path, f_base)
        with gzip.open(os.path.join(self.path, file), "rb") as f_in, open(os.path.join(self.path, out_fname), "wb") as f_out:
          shutil.copyfileobj(f_in, f_out)
        out_files.append(out_fname)
        # Delete the gz file now that we have its contents
        os.remove(os.path.join(self.path, file))
      except:
        print(f"Unable to expand GZIP file {file}. It's likely malformed.")
        return False

    # TAR archives
    elif f_ext == ".tar":
      print(f"Expanding TAR archive {file}.")
      try:
        with tarfile.open(os.path.join(self.path, file), "r") as tar:
          if self.config["flat"]:
            # Not using extractall() because we don't want a tree structure
            for member in tar.getmembers():
              if member.isreg():
                if self.config["flat"]:
                  # Strip any path information from members
                  member.name = self.get_unique_fname(self.path, os.path.basename(member.name))
                tar.extract(member, self.path)
                out_files.append(member.name)
        # Delete the tar file now that we have its contents
        os.remove(os.path.join(self.path, file))
      except:
        print(f"Unable to expand TAR archive {file}. Something is wrong with it.")
    
    # The file is not compressed or archived, or not a supported format
    else:
      return
    
    if not loop:
      return
    
    # Iterate back through, in case of layered archives or compressed archives (e.g. example.tar.gz)
    for file in out_files:
      # Set loop switch to False to avoid creating blackhole
      self.extract(file, False)
  
if __name__ == "__main__":
  try:
    t = Traverse(config)
    t.traverse()
  except KeyboardInterrupt:
    print("\nReceived keyboard interrupt. Bye!")
  except:
    print("Hrmm... something went wrong.")
    raise
