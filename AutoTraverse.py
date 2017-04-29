#!/usr/bin/python3

import requests, os, argparse, textwrap
from bs4 import BeautifulSoup

parser = argparse.ArgumentParser(
	prog="Traverse",
	formatter_class=argparse.RawDescriptionHelpFormatter,
	description=textwrap.dedent("""\
		AutoTraverse v0.1a
		  by Caleb White
		   
		Simple tool to traverse web directories that allow it and download all files contained in them.
		
		Options to download files in a flat structure and auto-expand archives and compressed files."""),
	epilog="""\
Note: If you do not specify a protocol, http:// will be prepended to your URL.
	
Download all the things!"""
)
parser.add_argument(
	"url",
	help="URL to download from.",
	nargs="?"
)
parser.add_argument(
	"path",
	help="Path to directory to save items into.",
	nargs="?"
)
parser.add_argument(
	"depth",
	help="Maximum depth of directories to traverse (0 for infinite).",
	nargs="?"
)
parser.add_argument(
	"--flat",
	help="Download all files in a single directory, not preserving directory structure.",
	required=False,
	action="store_true",
	dest="flat"
)
parser.add_argument(
	"--expand",
	help="Automatically expand archives and compressed files.",
	required=False,
	action="store_true",
	dest="expand"
)
parser.add_argument(
	"--moo",
	help=argparse.SUPPRESS,
	required=False,
	action='store_true',
	dest="moo"
)
args = parser.parse_args()

# Moo
if args.moo:
	print(textwrap.dedent("""\
		  .=     ,        =.
  _  _   /'/    )\\,/,/(_   \\ \\
   `//-.|  (  ,\\\\)\\//\\)\\/_  ) |
   //___\\   `\\\\\\/\\\\/\\/\\\\///'  /
,-\"~`-._ `\"--'_   `\"\"\"`  _ \\`'\"~-,_
\\       `-.  '_`.      .'_` \\ ,-\"~`/
 `.__.-'`/   (-\\        /-) |-.__,'
   ||   |     \\O)  /^\\ (O/  |
   `\\\\  |         /   `\\    /
the  \\\\  \\       /      `\\ /
cow   `\\\\ `-.  /' .---.--.\\
says    `\\\\/`~(, '()      ('
'moo'    /(O) \\\\   _,.-.,_)
        //  \\\\ `\\'`      /
       / |  ||   `\"\"\"\"~\"`
     /'  |__||
		   `o """
	))
	exit(0)


root = args.url if args.url else False
save_dir = args.path if args.path else False
if not args.path or not args.path:
	print("You must specify a URL and a path. Run {} -h for details.".format(os.path.basename(__file__)))
	exit(1)
if not root[-1:] == "/":
	root = "{}/".format(root)
if "http://" not in root and "https://" not in root:
	root = "{}{}".format("https://", root)
max_depth = int(args.depth) if args.depth else 0
flat = args.flat if args.flat else False
expand = args.expand if args.expand else False
if expand and not flat:
	print("WARNING! Archives will be expanded automatically. This combination of options should only be used with trusted sources!")
manifest_file = os.path.join(save_dir, ".manifest")

def get_manifest():
	try:
		with open(manifest_file, "r") as f:
			return f.readlines()
	except:
		f = open(manifest_file, "w")
		f.close()
		return []

old_manifest = get_manifest()
manifest = []

def traverse(branch = ""):
	headers = {
		"Accept-Encoding": "gzip, deflate",
		"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:52.0) Gecko/20100101 Firefox/52.0"
	}
	page = requests.get("{}{}".format(root, branch), headers=headers)
	
	tree = BeautifulSoup(page.text, "html.parser")
	
	for node in tree.find_all("a"):
		node_href = node.get("href")
		if root in node_href:
			node_href = node_href.replace(root, "")
		if node_href[-1:] == "/":
			if node_href == "../":
				continue
			node = "{}{}".format(branch, node_href)
			if max_depth:
				if node.count("/") > max_depth:
					continue
			print("Going deeper! Reading {}".format(node))
			traverse(node)
			continue
		# Make sure we're only following links to leaves at current depth
		if not (node_href == "{}{}".format(branch, node.contents[0]) or node_href == node.contents[0]):
			continue
		if "{}{}\n".format(branch, node_href) in old_manifest:
			continue
		get_leaf(branch, node_href)
	
	with open(manifest_file, "a") as f:
		for file in manifest:
			f.write(file)
			f.write("\n")
			
def get_leaf(branch = "", leaf = ""):
	if not flat:
		dir = os.path.join(save_dir, branch)
		if not os.path.exists(dir):
			os.makedirs(dir)
	print("Getting file {}{}".format(branch, leaf))
	save_as = ""
	if flat:
		save_as = os.path.join(save_dir, leaf)
	else:
		save_as = os.path.join(save_dir, branch, leaf)
	r = requests.get("{}{}{}".format(root, branch, leaf))
	with open(save_as, 'wb') as f:
		for chunk in r.iter_content(chunk_size=512 * 1024): 
			if chunk:
				f.write(chunk)
	manifest.append("{}{}".format(branch, leaf))
	if expand:
		extract_file(save_as)

def extract_file(file, loop=True):
	import zipfile, gzip, tarfile, shutil

	out_files = []
	file = str(file)
	f_base, f_ext = os.path.splitext(file)

	# ZIP archives
	if f_ext == ".zip":
		print("Expanding ZIP archive {0}.".format(file))
		try:
			with zipfile.ZipFile(os.path.join(save_dir, file)) as zip:
				# testzip() returns None or name of first bad file
				if zipfile.ZipFile.testzip(zip) is not None:
					print("Malformed ZIP or contents corrupted! Unable to process.")
					return False
				if flat:
					# Not using extractall() because we don't want a tree structure
					for member in zip.infolist():
						member = unique_fname(member)
						if flat:
							zip.extract(member, save_dir)
						else:
							zip.extract(member)
						out_files.append(str(member))
				else:
					zip.extractall(save_dir)
				# Delete the zip file now that we have its contents
			os.remove(os.path.join(save_dir, file))
		except:
			print("Unable to expand ZIP archive {0}. You should check its headers or something.".format(file))
			return False

	# GZIP compression
	elif f_ext == ".gz":
		print("Expanding GZIP compressed file {0}.".format(file))
		try:
			out_fname = unique_fname(f_base)
			with gzip.open(os.path.join(save_dir, file), "rb") as f_in, open(os.path.join(save_dir, out_fname), "wb") as f_out:
				shutil.copyfileobj(f_in, f_out)
			out_files.append(out_fname)
			# Delete the gz file now that we have its contents
			os.remove(os.path.join(save_dir, file))
		except:
			print("Unable to expand GZIP file {0}. It's likely malformed.".format(file))
			return False

	# TAR archives
	elif f_ext == ".tar":
		print("Expanding TAR archive {0}.".format(file))
		try:
			with tarfile.open(os.path.join(save_dir, file), "r") as tar:
				if flat:
					# Not using extractall() because we don't want a tree structure
					for member in tar.getmembers():
						if member.isreg():
							if flat:
								# Strip any path information from members
								member.name = unique_fname(os.path.basename(member.name))
							tar.extract(member, save_dir)
							out_files.append(member.name)
			# Delete the tar file now that we have its contents
			os.remove(os.path.join(save_dir, file))
		except:
			print("Unable to expand TAR archive {0}. Something is wrong with it.".format(file))
	
	# The file is not compressed or archived, or not a supported format
	else:
		return
	
	if not loop:
		return
	
	# Iterate back through, in case of layered archives or compressed archives (e.g. example.tar.gz)
	for file in out_files:
		# Set loop switch to False to avoid creating blackhole
		extract_file(file, False)
	
	
def unique_fname(file):
	# Rename file if necessary to avoid overwrite...
	basename, ext = get_fext(str(file))
	i = 0
	while os.path.exists(os.path.join(save_dir, "{0} ({1}){2}".format(basename, i, ext)) if i else "{0}/{1}".format(save_dir, file)):
		i += 1
	# Apply the filename determined by the previous step
	if i:
		file = "{0} ({1}){2}".format(basename, i, ext)
	return file

def get_fext(file):
	basename, ext = os.path.splitext(file)
	while "." in basename[-6:]:
		basename, ext2 = os.path.splitext(basename)
		ext = ext2 + ext
	return basename, ext
	
if __name__ == "__main__":
	traverse()