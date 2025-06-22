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
