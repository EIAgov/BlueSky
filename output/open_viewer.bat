start "" http://127.0.0.1:8050/
pushd %~dp0
call C:\ProgramData\anaconda3\Scripts\activate.bat
call conda activate bsky
python viewer.py
pause
