# Running with VS Code

The utility class of main.py stores the current working directory of the file. In order to get the correct working directory while running the terminal in VSCode, do the following:
1. Select File
2. Add Folder to Workspace...
3. Select the "preprocessor" folder within the repository you are working out of

# Python environment
Use the following python environment to ensure package consistency
O:\python_environments\aeo2025_py311\Scripts\python.exe

# main.py

main.py is the flow controller of the preprocessor. It is responsible for:
1. Importing and running all submodules. Each submodules is called with their respective submodule.run() command. This will clean and output data for each parameter grouping
2. Building the Utility class. Currently, the utility class does the following:
	a. Hold commons sets such as regions, seasons, and hours
	b. Hold both input and output filepaths. Using this to read raw data allows the pre-processor to easily use alternative files and removes file path hardcoding
	c. Hold commonly used functions. Especially functions that converts dataframes to AIMMS composite tables and lists/arrays into AIMMS data sets using Data {} notation

main.py passes an instantiation of the Utility class into each submodule to reduce repetitive coding within submodules.

# Steps to process more data
1. add new dataset to its respective folder within the raw_data folder. Preferably in CSV format
2. add dataset file path to paths_in.csv. Give a unique name for the 'key' entry. This can be a shorthand for whatever parameter you are preparing for AIMMS.
3. within its respective submodule, create a new definition that will prepare AIMMS output from the newly added dataset. *IMPORTANT: column ordering of output matters. Indexes should match exactly 
the index names used by AIMMS, and in the same order. The final column of the dataframe should be the value of the parameter, and the name of the column should match the parameter name.
4. add path name to paths_out.csv to tell the preprocessor where to save the new output
5. within the data cleaning definition, call the proper Utility function to write out data in the correct AIMMS format using the path identified in step 4.
6. call the new definition from submodule.run(), passing through the instantiated utility class

Most data cleaing activities should be done within the preprocessor, not before saving the data to the raw_data folder. This allows for natural documentation of data cleaning through the code.
The exact organization of individual submodule functions is up to the user's preference. Column naming is also up to the user's preference for raw data files. Column naming in output is NOT up to preference.
Follow the column naming conventions of the AIMMS model.

# Committing Code
Make sure to version control all input files, output files, file path changes, and python code changes.