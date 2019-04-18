import requests, os, argparse, textwrap, yaml, progressbar
from bs4 import BeautifulSoup

# Default config with help and stuff
# Adding an entry here will add it to:
# - Commandline help
# - Commandline options
# - Config wizard
default_config = {
	# "name" : [
	# 	"Help text.",
	# 	"Setup help",
	# 	type, default value, [required]
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
	"-depth" : [
		"Maximum depth of directories to traverse (0 for infinite).",
		"Specify a search depth to stop at",
		int, False, False
	],
	"-chunksize" : [
		"Chunk size for writing to disk (default is 4096).",
		"Specify a custom chunk size",
		int, 4096, False
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
		"Do you want to save this configuration as the default?\nYou can edit or delete settings.yml later.",
		bool, False, False
	],
}

# Populate argument parser
parser = argparse.ArgumentParser(
	prog="AutoTraverse",
	formatter_class=argparse.RawDescriptionHelpFormatter,
	description=textwrap.dedent("""\
		AutoTraverse v0.3a
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
					option_value = input("{0} {1}: ".format(
						default_config[option][1],
						"[Y]/[n]" if default_config[option][3] else "[y]/[N]"
					))
					if option_value == "":
						option_value = default_config[option][3]
					else:
						option_value = True if option_value[0] in ["y", "Y"] else False
				else:
					option_value = input("{0}{1}: ".format(
						default_config[option][1],
						" (blank to skip)" if not default_config[option][4] else ""
					))
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
	print("You must specify a URL and a path. Run {} -h for details.".format(os.path.basename(__file__)))
	exit(1)
if not config["url"][-1] == "/":
	config["url"] = "{}/".format(config["url"])
if "http://" not in config["url"] and "https://" not in config["url"]:
	config["url"] = "{}{}".format("https://", config["url"])
if not os.path.isdir(config["path"]):
	try:
		os.makedirs(config["path"])
	except:
		print("Path does not exist and failed to create it: {0}".format(config["path"]))
		exit(1)

# Write config if requested
if config["write-config"]:
	with open("settings.yml", "w") as f:
		yaml.safe_dump(config, f)

# Build Traverse class
class Traverse(object):
	def __init__(self, config, *args, **kwargs):
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
		self.cur_depth = 0

		if config["skip-cert-check"]:
			requests.packages.urllib3.disable_warnings()

		try:
			with open(self.manifest_file, "r") as f:
				self.manifest = f.readlines()
		except:
			f = open(self.manifest_file, "w")
			f.close()
			self.manifest = []

	def traverse(self, branch = ""):
		if branch == "":
			print("Loading {0}".format(self.config["url"]))
		page = requests.get(
			"{}{}".format(self.config["url"], branch),
			headers=self.headers,
			verify=not self.config["skip-cert-check"]
		)
		if not page.ok:
			print("Bad response ({0}) getting directory {1}".format(page.status_code, branch))
			return
		
		tree = BeautifulSoup(page.text, "html.parser")
		
		for node in tree.find_all("a"):
			node_href = node.get("href")
			if node_href[0:4] == "http":
				if not self.config["url"] in node_href:
					print("Ignoring off-site link: {0}".format(node_href))
					continue
				if len(node_href) < len(self.config["url"]):
					continue
			if self.config["url"] in node_href:
				node_href = node_href.replace(self.config["url"], "")
			if node_href[-1] == "/":
				# Let's not backtrack
				if node_href == "../" or node_href in self.config["url"]:
					continue
				node = "{}{}".format(branch, node_href)
				if self.config["depth"] not in [False, -1]:
					if node.count("/") > self.config["depth"]:
						continue
				print("{0}Reading {1}".format("Going deeper! " if node.count("/") > self.cur_depth else "", node))
				self.cur_depth = node.count("/")
				self.traverse(node)
				continue
			# Make sure we're only following links to leaves at current depth
			if not (node_href == "{}{}".format(branch, node.contents[0]) or node_href == node.contents[0]):
				continue
			if "{}{}\n".format(branch, node_href) in self.manifest:
				continue
			self.get_leaf(branch, node_href)
		
		f = open(self.manifest_file, "w")
		f.close()
		with open(self.manifest_file, "a") as f:
			for file in self.manifest:
				f.write(file)
		if branch == "":
			print("Done!")

	def get_leaf(self, branch = "", leaf = ""):
		save_path = os.path.join(self.config["path"], branch)
		if not os.path.exists(save_path):
			os.makedirs(save_path)
		save_as = os.path.join(self.config["path"], branch, leaf)
		r = requests.get(
			"{}{}{}".format(self.config["url"], branch, leaf),
			headers=self.headers,
			stream=True,
			verify=not self.config["skip-cert-check"]
		)
		if not r.ok:
			print("Bad response ({0}) getting file {1}{2}".format(r.status_code, branch, leaf))
			return
		download_size = int(r.headers.get("content-length"))
		pbar = progressbar.ProgressBar(
				widgets=[
						"Getting file {0}{1}: ".format(branch, leaf),
						progressbar.Counter(),
						"/{0} (".format(r.headers.get("content-length")),
						progressbar.Percentage(),
						") ",
						progressbar.Bar(),
						progressbar.AdaptiveETA()
				], maxval=download_size
		).start()
		downloaded = 0
		with open(save_as, 'wb') as f:
			for chunk in r.iter_content(chunk_size=self.config["chunksize"]):
				if chunk:
					chunk_size = len(chunk)
					downloaded += chunk_size
					if downloaded <= download_size:
						pbar.update(downloaded)
					else:
						pbar.update(download_size)
						print("\nWarning: Exceeded advertised size! {0} > {1}".format(downloaded, download_size))
					f.write(chunk)
				else:
					pbar.update(int(r.headers.get("content-length")))
		pbar.finish()
		print()
		# Append to manifest
		self.manifest.append("{0}{1}\n".format(branch, leaf))
		# Write to disk to prevent lost information from early termination
		with open(self.manifest_file, "a") as f:
				f.write(self.manifest[-1])
		if self.config["expand"]:
			self.extract_file(save_as)

	def extract_file(self, file, loop=True):
		import zipfile, gzip, tarfile, shutil

		out_files = []
		file = str(file)
		f_base, f_ext = os.path.splitext(file)

		# ZIP archives
		if f_ext == ".zip":
			print("Expanding ZIP archive {0}.".format(file))
			try:
				with zipfile.ZipFile(os.path.join(self.config["path"], file)) as zip:
					# testzip() returns None or name of first bad file
					if zipfile.ZipFile.testzip(zip) is not None:
						print("Malformed ZIP or contents corrupted! Unable to process.")
						return False
					if self.config["flat"]:
						# Not using extractall() because we don't want a tree structure
						for member in zip.infolist():
							member = self.unique_fname(member)
							if self.config["flat"]:
								zip.extract(member, self.config["path"])
							else:
								zip.extract(member)
							out_files.append(str(member))
					else:
						zip.extractall(self.config["path"])
					# Delete the zip file now that we have its contents
				os.remove(os.path.join(self.config["path"], file))
			except:
				print("Unable to expand ZIP archive {0}. You should check its headers or something.".format(file))
				return False

		# GZIP compression
		elif f_ext == ".gz":
			print("Expanding GZIP compressed file {0}.".format(file))
			try:
				out_fname = self.unique_fname(f_base)
				with gzip.open(os.path.join(self.config["path"], file), "rb") as f_in, open(os.path.join(self.config["path"], out_fname), "wb") as f_out:
					shutil.copyfileobj(f_in, f_out)
				out_files.append(out_fname)
				# Delete the gz file now that we have its contents
				os.remove(os.path.join(self.config["path"], file))
			except:
				print("Unable to expand GZIP file {0}. It's likely malformed.".format(file))
				return False

		# TAR archives
		elif f_ext == ".tar":
			print("Expanding TAR archive {0}.".format(file))
			try:
				with tarfile.open(os.path.join(self.config["path"], file), "r") as tar:
					if self.config["flat"]:
						# Not using extractall() because we don't want a tree structure
						for member in tar.getmembers():
							if member.isreg():
								if self.config["flat"]:
									# Strip any path information from members
									member.name = self.unique_fname(os.path.basename(member.name))
								tar.extract(member, self.config["path"])
								out_files.append(member.name)
				# Delete the tar file now that we have its contents
				os.remove(os.path.join(self.config["path"], file))
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
			self.extract_file(file, False)
		
		
	def unique_fname(self, file):
		# Rename file if necessary to avoid overwrite...
		basename, ext = self.get_fext(str(file))
		i = 0
		while os.path.exists(os.path.join(self.config["path"], "{0} ({1}){2}".format(basename, i, ext) if i else file)):
			i += 1
		# Apply the filename determined by the previous step
		if i:
			file = "{0} ({1}){2}".format(basename, i, ext)
		return file

	def get_fext(self, file):
		basename, ext = os.path.splitext(file)
		while "." in basename[-6:]:
			basename, ext2 = os.path.splitext(basename)
			ext = ext2 + ext
		return basename, ext
	
if __name__ == "__main__":
	t = Traverse(config)
	t.traverse()
