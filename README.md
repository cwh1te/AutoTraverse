# AutoTraverse
Simple tool to traverse web directories and download all files contained in them.
        
Options to auto-expand archives and compressed files.

## Setup
```bash
pip install -r requirements.txt
```
Requires Python 3.7.3+ for proper operation. Please don't open issues for old Python versions.

## Usage:
```bash
python AutoTraverse.py url path [depth] [chunksize] [peeksize] [peekpct] [-h] [--expand] [--flat]
                    [--skip-cert-check] [--assume-unchanged] [--delete-superceded] [--write-config]
                    [--progressbar]
```
You can also run it with no arguments and the initial configuration wizard will help you figure things out.

Note: In order to use the `--progressbar` flag, you will have to `pip install progressbar` separately. This is because the package is from Google and therefore many people might not trust is, so I didn't feel good having it in `requirements.txt`.

## Examples:
```
python AutoTraverse.py www.example.com /path/to/save/location 5 4096 --expand --flat --skip-cert-check
python AutoTraverse.py http://old-releases.ubuntu.com/releases oldbuntu --write-config
```

Download all the things!
