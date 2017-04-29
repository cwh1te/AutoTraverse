# AutoTraverse
A simple tool to traverse web directories and download all the files contained in them.

Options to download files in a flat structure and auto-expand archives and compressed files.

Usage:
```
python3 AutoTraverse.py URL save_directory [depth] [--flat] [--expand]
```

Example:
```
python3 AutoTraverse.py "https://www.example.com" "/path/to/save/location" 5 --flat --expand
```
