# AutoTraverse
Simple tool to traverse web directories and download all files contained in them.
		
Options to auto-expand archives and compressed files.

Setup:
```bash
pip3 install -r requirements.txt
```

Usage:
```
python3 AutoTraverse.py URL save_directory [depth] [chunksize] [--flat] [--expand]
```

Example:
```
python3 AutoTraverse.py "https://www.example.com" "/path/to/save/location" 5 4096 --flat --expand
```
