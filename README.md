# some-helpful-python-programs
1. zipper.py: a simple python program to create zip file out of the files that are present in the current directory.Simple to use :
    ```python3 zipper.py ```
2. duplicate_finder.py: a simple python program created to remove the files with duplicate of it from the current folder. Works on the folders where the program is saved in.Just run :
   ```python3 duplicate_finder.py```
3. large_file_finder.py: a simple python script to display the large file as per the user following are the ways the script can be used : <br />
   ```python large_file_finder.py /home/user/Documents```<br />
   or<br />
   ```python large_file_finder.py -n 50```<br />
   or<br />
   ```python large_file_finder.py -s 100MB```<br />
   or<br />
   ``` many other ways can be used to display the files that are there in the folder to display the required files as per the needs of the user```<br />
4. empty_folder_cleaner.py: a simple python program to delete empty folders in a given directory.Following are the methods to run the script : <br />
```python empty_folder_cleaner.py /path/to/your/folder```

5. file_age_analysis.py: this is a simple python program to scan a given directory and compute age based on teh modified time and all accordingly. How to use this program : < br/>
- Analyze current directory, show groups by age
```
python file_age_analysis.py --group
```
- Find files not accessed in more than 60 days
```
python file_age_analysis.py /path/to/dir --stale 60
```
- Show files modified in last 7 days
```
python file_age_analysis.py /path/to/dir --recent 7
```
- Combine options
```
python file_age_analysis.py /path/to/dir --stale 30 --recent 15 --group
```
6. hidden_file_finder.py: Find and manage hidden files across platforms. Cross-platform tool to discover, analyze, and manage hidden files and directories.How to use this program : < bt/>
- Scan current directory
```
python hidden_file_finder.py
```
- Scan specific directory recursively
```
python hidden_file_finder.py /home/user/Documents
```
- Scan only current level (no subdirectories)
```
python hidden_file_finder.py --no-recursive
```
7. disk_usage_monitor.py: This file contains the code that continuously monitors disk usage on a system and sends alerts (via console, email, log files, or system notifications) if disk space usage exceeds configurable warning or critical thresholds.
```
python disk_usage_monitor.py
```
8.file_hasher.py : A comprehensive file hashing utility with extensive features for integrity checking. 

```
python file_hasher.py document.pdf
```

```
python file_hasher.py document.pdf -m md5 sha256 sha512
```

```
python file_hasher.py /path/to/directory -r
```
8.csv_to_json.py : A comprehensive CSV to JSON converter that works on any system with flexible command-line options.

```
python csv_to_json.py data.csv results.json
```
```
python csv_to_json.py data.csv
```
