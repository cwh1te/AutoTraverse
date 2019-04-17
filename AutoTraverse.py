import requests, os, argparse, textwrap, yaml, progressbar
from bs4 import BeautifulSoup

# Default config with help and stuff
# Adding an entry here will add it to:
# - Commandline help
# - Commandline options
# - TODO: First time wizard
default_config = {
	# "name" :			["Help text", type, "default"]
	"url" :     ["URL to download from.", str, ""],
	"path" :    ["Path to directory to save items into.", str, ""],
	"depth" :   ["Maximum depth of directories to traverse (0 for infinite).", int, False],
	"chunksize":["Chunk size for writing to disk (default is 4096).", int, 4096],
	"--flat" :  ["Download all files in a single directory, not preserving directory structure.", bool, False],
	"--expand" :["Automatically expand archives and compressed files.", bool, False]
}

# Populate argument parser
parser = argparse.ArgumentParser(
	prog="AutoTraverse",
	formatter_class=argparse.RawDescriptionHelpFormatter,
	description=textwrap.dedent("""\
		AutoTraverse v0.2a
		  by Caleb White
		   
		Simple tool to traverse web directories that allow it and download all files contained in them.
		
		Options to download files in a flat structure and auto-expand archives and compressed files."""),
	epilog="""\
Note: If you do not specify a protocol, https:// will be prepended to your URL.
	
Download all the things!"""
)

for option in default_config.keys():
	if option[:2] == "--":
		parser.add_argument(
			option,
			help=default_config[option][0],
			required=False,
			action="store_true",
			dest=option[2:]
		)
	elif option[:1] == "-":
		parser.add_argument(
			option,
			help=default_config[option][0],
			required=False,
			type=default_config[option][1],
			nargs="+",
			dest=option[1:]
		)
	else:
		parser.add_argument(
			option,
			help=default_config[option][0],
			type=default_config[option][1],
			nargs="?"
		)

parser.add_argument(
	"--moo",
	help=argparse.SUPPRESS,
	required=False,
	action='store_true',
	dest="moo"
)

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
if os.path.isfile("settings.yml"):
	config = yaml.safe_load(open("settings.yml"))
else:
	config = default_config.copy()

# Override default/stored values with commandline input
for option in default_config.keys():
	# Strip "--" and "-" from input names to make suitable variable names
	option_name = option[2:] if option[:2] == "--" else option
	option_name = option_name[1:] if option_name[:1] == "-" else option_name
	if getattr(args, option_name):
		if not type(getattr(args, option_name)) is default_config[option][1]:
			config[option_name] = default_config[option][1](getattr(args, option_name))
		else:
			config[option_name] = getattr(args, option_name)

# Handle defaults that weren't overwritten
for option in default_config.keys():
	option_name = option[2:] if option[:2] == "--" else option
	option_name = option_name[1:] if option_name[:1] == "-" else option_name
	if option_name not in config.keys() or config[option_name] == default_config[option]:
		config[option_name] = default_config[option][2]

if not config["url"] or not config["path"]:
	print("You must specify a URL and a path. Run {} -h for details.".format(os.path.basename(__file__)))
	exit(1)
if not config["url"][-1] == "/":
	config["url"] = "{}/".format(config["url"])
if "http://" not in config["url"] and "https://" not in config["url"]:
	config["url"] = "{}{}".format("https://", config["url"])

base_depth = config["url"].count("/") -3
config["depth"] += base_depth -1

if config["expand"] and not config["flat"]:
	print("WARNING! Archives will be expanded automatically. This combination of options should only be used with trusted sources!")
manifest_file = os.path.join(config["path"], ".manifest")

def get_manifest():
	try:
		with open(manifest_file, "r") as f:
			return f.readlines()
	except:
		f = open(manifest_file, "w")
		f.close()
		return []

manifest = get_manifest()

def traverse(branch = ""):
	headers = {
		"Accept-Encoding": "gzip, deflate",
		"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:52.0) Gecko/20100101 Firefox/52.0"
	}
	if branch == "":
		print("Loading {0}".format(config["url"]))
	page = requests.get("{}{}".format(config["url"], branch), headers=headers)
	
	tree = BeautifulSoup(page.text, "html.parser")
	
	for node in tree.find_all("a"):
		node_href = node.get("href")
		if node_href[0:4] == "http":
			if not config["url"] in node_href:
				print("Ignoring off-site link: {0}".format(node_href))
				continue
		if config["url"] in node_href:
			node_href = node_href.replace(config["url"], "")
		if node_href[-1] == "/":
			if node_href == "../" or node_href in config["url"]:
				continue
			node = "{}{}".format(branch, node_href)
			if config["depth"] is not False:
				if node.count("/") > config["depth"]:
					continue
			print("{0}Reading {1}".format("Going deeper! " if node.count("/") > base_depth else "", node))
			traverse(node)
			continue
		# Make sure we're only following links to leaves at current depth
		if not (node_href == "{}{}".format(branch, node.contents[0]) or node_href == node.contents[0]):
			continue
		if "{}{}\n".format(branch, node_href) in manifest:
			continue
		get_leaf(branch, node_href)
	
	f = open(manifest_file, "w")
	f.close()
	with open(manifest_file, "a") as f:
		for file in manifest:
			f.write(file)
	print("Done!")
			
def get_leaf(branch = "", leaf = ""):
	if not config["flat"]:
		save_path = os.path.join(config["path"], branch)
		if not os.path.exists(save_path):
			os.makedirs(save_path)
	save_as = ""
	if config["flat"]:
		save_as = os.path.join(config["path"], leaf)
	else:
		save_as = os.path.join(config["path"], branch, leaf)
	r = requests.get("{}{}{}".format(config["url"], branch, leaf), stream=True)
	download_size = int(r.headers.get("content-length"))
	pbar = progressbar.ProgressBar(
			widgets=[
					"Getting file {}{}: ".format(branch, leaf),
					progressbar.Counter(),
					"/{} (".format(r.headers.get("content-length")),
					progressbar.Percentage(),
					") ",
					progressbar.Bar(),
					progressbar.AdaptiveETA()
			], maxval=download_size
	).start()
	downloaded = 0
	with open(save_as, 'wb') as f:
		for chunk in r.iter_content(chunk_size=config["chunksize"]):
			if chunk:
				chunk_size = len(chunk)
				downloaded += chunk_size
				if downloaded <= download_size:
					pbar.update(downloaded)
				else:
					pbar.update(download_size)
					print("\nWarning: Download exceeds advertised size! {0} > {1}".format(downloaded, download_size))
				f.write(chunk)
			else:
				pbar.update(int(r.headers.get("content-length")))
	pbar.finish()
	print()
	# Append to manifest
	manifest.append("{}{}\n".format(branch, leaf))
	# Write to disk to prevent lost information from early termination
	with open(manifest_file, "a") as f:
			f.write(manifest[-1])
	if config["expand"]:
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
			with zipfile.ZipFile(os.path.join(config["path"], file)) as zip:
				# testzip() returns None or name of first bad file
				if zipfile.ZipFile.testzip(zip) is not None:
					print("Malformed ZIP or contents corrupted! Unable to process.")
					return False
				if config["flat"]:
					# Not using extractall() because we don't want a tree structure
					for member in zip.infolist():
						member = unique_fname(member)
						if config["flat"]:
							zip.extract(member, config["path"])
						else:
							zip.extract(member)
						out_files.append(str(member))
				else:
					zip.extractall(config["path"])
				# Delete the zip file now that we have its contents
			os.remove(os.path.join(config["path"], file))
		except:
			print("Unable to expand ZIP archive {0}. You should check its headers or something.".format(file))
			return False

	# GZIP compression
	elif f_ext == ".gz":
		print("Expanding GZIP compressed file {0}.".format(file))
		try:
			out_fname = unique_fname(f_base)
			with gzip.open(os.path.join(config["path"], file), "rb") as f_in, open(os.path.join(config["path"], out_fname), "wb") as f_out:
				shutil.copyfileobj(f_in, f_out)
			out_files.append(out_fname)
			# Delete the gz file now that we have its contents
			os.remove(os.path.join(config["path"], file))
		except:
			print("Unable to expand GZIP file {0}. It's likely malformed.".format(file))
			return False

	# TAR archives
	elif f_ext == ".tar":
		print("Expanding TAR archive {0}.".format(file))
		try:
			with tarfile.open(os.path.join(config["path"], file), "r") as tar:
				if config["flat"]:
					# Not using extractall() because we don't want a tree structure
					for member in tar.getmembers():
						if member.isreg():
							if config["flat"]:
								# Strip any path information from members
								member.name = unique_fname(os.path.basename(member.name))
							tar.extract(member, config["path"])
							out_files.append(member.name)
			# Delete the tar file now that we have its contents
			os.remove(os.path.join(config["path"], file))
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
	while os.path.exists(os.path.join(config["path"], "{0} ({1}){2}".format(basename, i, ext)) if i else "{0}/{1}".format(config["path"], file)):
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
