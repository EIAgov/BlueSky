@echo off

REM Locate and Open Anaconda prompt: EXAMPLE: "C:\Users\arh\anaconda3\condabin\activate.bat"
call "C:\PATH-TO-ANACONDA\user\anaconda3\condabin\activate.bat"

REM Navigate to project directory and create new environment using exisitng yml file: EXAMPLE: "C:\Users\arh\OneDrive - Energy Information Administration\gh_repos_n\bluesky_prototype"
cd "C:\PATH-TO-BLUSKY_REPO\gh_repos_n\bluesky_prototype" && conda env create -f conda_env.yml && conda activate bsky && pip install highspy


