import os
import numpy as np
import pandas as pd

import operation
import history
import TandS
import other

import importlib
from tabulate import tabulate


class Utility:
    def __init__(self, pyomo_switch):
        self.pyomo_switch = pyomo_switch
        self.base_dir = os.getcwd()

        self.census = [
            'NewEngland',
            'MidAtlantic',
            'ENCentral',
            'WNCentral',
            'SAtlantic',
            'ESCentral',
            'WSCentral',
            'Mountain',
            'Pacific',
        ]

        self.nerc = [
            'TRE',
            'FRCC',
            'MISW',
            'MISC',
            'MISE',
            'MISS',
            'ISNE',
            'NYCW',
            'NYUP',
            'PJME',
            'PJMW',
            'PJMC',
            'PJMD',
            'SRCA',
            'SRSE',
            'SRCE',
            'SPPS',
            'SPPC',
            'SPPN',
            'SRSG',
            'CANO',
            'CASO',
            'NWPP',
            'RMRG',
            'BASN',
        ]

        self.hr = np.arange(1, 25).tolist()
        self.seas = ['1', '2', '3', '4']

        self.inputKeys = pd.read_csv('paths_in.csv', index_col=0, header=0)

        self.outputKeys = pd.read_csv('paths_out.csv', index_col=0, header=0)

        if self.pyomo_switch == True:
            self.outputKeys['path'] = [
                '/pyomo_data' + path[:-3] + 'csv' for path in self.outputKeys['path']
            ]

        self.last_hYear = 2023
        self.first_hYear = 1990

        self.smr_ng_feedstock_percent = 0.83

        self.state_census_map = pd.read_excel('state-census mapping.xlsx', header=0)

        self.base_dollar_year = 2022
        self.deflator_series = pd.read_csv('deflator_series.csv')

        if pyomo_switch is True:
            if os.path.isdir(self.base_dir + '\pyomo_data') is False:
                os.mkdir(self.base_dir + '\pyomo_data')
            if os.path.isdir(self.base_dir + '\pyomo_data\output_data') is False:
                os.mkdir(self.base_dir + '\pyomo_data\output_data')
            if os.path.isdir(self.base_dir + '\pyomo_data\output_data\operations') is False:
                os.mkdir(self.base_dir + '\pyomo_data\output_data\operations')
            if os.path.isdir(self.base_dir + '\pyomo_data\output_data\history') is False:
                os.mkdir(self.base_dir + '\pyomo_data\output_data\history')
            if os.path.isdir(self.base_dir + '\pyomo_data\output_data\TandS') is False:
                os.mkdir(self.base_dir + '\pyomo_data\output_data\TandS')
            if os.path.isdir(self.base_dir + '\pyomo_data\output_data\other') is False:
                os.mkdir(self.base_dir + '\pyomo_data\output_data\other')

        else:
            if os.path.isdir(self.base_dir + '\output_data') is False:
                os.mkdir(self.base_dir + '\output_data')
            if os.path.isdir(self.base_dir + '\output_data\operations') is False:
                os.mkdir(self.base_dir + '\output_data\operations')
            if os.path.isdir(self.base_dir + '\output_data\history') is False:
                os.mkdir(self.base_dir + '\output_data\history')
            if os.path.isdir(self.base_dir + '\output_data\TandS') is False:
                os.mkdir(self.base_dir + '\output_data\TandS')
            if os.path.isdir(self.base_dir + '\output_data\other') is False:
                os.mkdir(self.base_dir + '\output_data\other')

        self.sets_to_output(
            [self.census, self.nerc],
            ['CensusRegions_', 'NERCRegions_'],
            self.base_dir + self.outputKeys.loc['region_sets', 'path'],
        )
        self.write_single_value_param(
            self.smr_ng_feedstock_percent,
            'smr_ng_feedstock_prc',
            self.base_dir + self.outputKeys.loc['smr_ng_feedstock_prc', 'path'],
            note='Source: GREET 2019',
        )
        self.write_single_value_param(
            "'" + str(self.base_dollar_year) + "'",
            'base_dollar_year',
            self.base_dir + self.outputKeys.loc['base_dollar_year', 'path'],
            note='all dollar values deflated to this year',
            unit='$' + str(self.base_dollar_year),
        )

    def write_csv_output(self, df, value_columns, output_path, note=None, unit=None):
        """
        pyomo switch function that replaces write_aimms_output.
        takes in the same data as the write_aimms_output

        outputs a csv file of the dataframe.
        """
        # 1. strip all unnecessary whitespace
        df.columns.str.strip()

        # 2. drop any rows containing missing values in an index column
        df.dropna(axis=0, subset=df.columns.difference(value_columns), inplace=True)

        # 3. remaining NA's (should only be in value columns, with spaces
        df.fillna(value=0, inplace=True)

        df.to_csv(output_path, index=False)

    def write_aimms_output(self, df, value_columns, output_path, note=None, unit=None):
        """
        Takes a pandas DataFrame that has been formatted by dataframe_to_aimms_format() and saves data to a text file.

        Parameters
        ----------
        df_to_write : dataframe
            pandas dataframe already formatted for AIMMS.
        output_path : str
            directory where the AIMMS ready text file should be written to.
        note : str
            write a note here to insert a labeled documentation line to output
        unit : str
            write the unit of the value column here to insert a labeled documentation line to output

        Returns
        -------
        None
        """

        if self.pyomo_switch == True:
            self.write_csv_output(df, value_columns, output_path, note, unit)
        else:
            # 1. strip all unnecessary whitespace
            df.columns.str.strip()

            # 2. drop any rows containing missing values in an index column
            df.dropna(axis=0, subset=df.columns.difference(value_columns), inplace=True)

            # 3. remaining NA's (should only be in value columns, with spaces
            df.fillna(value='', inplace=True)

            # 3. get the width of the longest width value for each column
            new_col_names = []
            for i in df.columns:
                # value columns will need to be converted to string and then back to float
                if i in value_columns:
                    df[i] = df[i].astype(str).str.replace(' ', '_', regex=True).astype(float)
                # extra whitespace is stripped and spaces inbetween values are replaced with underscores
                else:
                    df[i].str.strip()
                    df[i] = df[i].str.replace(' ', '_', regex=True)

                max_width = 0
                # iterate through each row in a given column. Find the max width and append it to a list
                for r in df[i]:
                    if len(str(r)) > max_width:
                        max_width = len(str(r))

                new_col_names.append(i.ljust(max_width + 2))

            # replace column names with newly spaced names.
            df.columns = new_col_names

            with open(output_path, 'w') as f:
                if note is not None:
                    f.write('! Note: ' + str(note) + '\n')
                if unit is not None:
                    f.write('! Unit: ' + str(unit) + '\n')

                f.write('Composite Table:\n')
                f.write(
                    tabulate(
                        df,
                        showindex=False,
                        headers=df.columns,
                        tablefmt='plain',
                        numalign='left',
                        stralign='left',
                    )
                )
                f.write('\n;')

    def write_single_value_param(self, value, var_name, output_path, note=None, unit=None):
        """
        This takes a single value parameter (no index to the parameter) and writes the parameter name and value into an
        AIMMS friendly format/txt file. Allos for notes and unit documentation, but not required.

        Parameters
        ----------
        value : single element
            One single int, float, or string.
        var_names : list
            parameter name that reflects the AIMMS model structure.
        output_path : str
            directory where the AIMMS ready text file should be written to.

        Returns
        -------
        None
        """

        if self.pyomo_switch == True:
            df = pd.DataFrame({var_name: [value]})
            df.to_csv(output_path[:-3] + 'csv', index=False)

        else:
            with open(output_path, 'w') as f:
                if note is not None:
                    f.write('! Note: ' + str(note) + '\n')
                if unit is not None:
                    f.write('! Unit: ' + str(unit) + '\n')

                f.write(var_name + ' := ' + str(value))

    def sets_to_output(self, arrays, var_names, output_path):
        """
        Takes either a single dimensioned numpy array or a list of single dimensioned numpy arrays. It will take all
        arrays and write them to a single output text file. Each array will be formatted to be read as a Set by AIMMS, using
        the var_names parameter for set assignment. the dimenion of var_names needs to match the number of numpy arrays
        passed in. The var_names elements will need to match the names of the Sets being used in AIMMS/WHAM.

        Parameters
        ----------
        arrays : numpy array or list of numpy arrays
            One array for each set, containing every element of that set.
        var_names : list
            list of set names that the elements of each numpy array will be assigned to in AIMMS.
        output_path : str
            directory where the AIMMS ready text file should be written to.

        Returns
        -------
        None
        """

        if self.pyomo_switch == True:
            for i in range(len(var_names)):
                df = pd.DataFrame({var_names[i]: arrays[i]})
                df.to_csv(output_path[:-3] + var_names[i] + '.csv', index=False)
        else:
            with open(output_path, 'w') as f:
                # if a list of numpy arrays was given
                if isinstance(arrays, list):
                    for count, single in enumerate(arrays):
                        f.write(var_names[count] + ' := DATA {')
                        for i in range(len(single)):
                            if i == 0:
                                if type(single[i]) is str:
                                    f.write(str.strip(single[i]))
                                else:
                                    f.write(str(single[i]))
                            else:
                                if type(single[i]) is str:
                                    f.write(',' + str.strip(single[i]))
                                else:
                                    f.write(',' + str(single[i]))
                        f.write('};\n\n')

                # else assume a single numpy array was passed along
                else:
                    f.write(var_names[0] + ' := DATA {')
                    for i in range(len(arrays)):
                        if i == 0:
                            if type(arrays[i]) is str:
                                f.write(str.strip(arrays[i]))
                            else:
                                f.write(str(arrays[i]))
                        else:
                            if type(arrays[i]) is str:
                                f.write(',' + str(arrays[i]))
                            else:
                                f.write(',' + str(arrays[i]))
                    f.write('};\n')

    def deflate_prices(self, year):
        deflator = (
            self.deflator_series.loc[self.deflator_series['year'] == year]['price_deflator'].iloc[0]
            / self.deflator_series.loc[self.deflator_series['year'] == self.base_dollar_year][
                'price_deflator'
            ].iloc[0]
        )

        return deflator


if __name__ == '__main__':
    pyomo_switch = True
    util = Utility(pyomo_switch)

    # other.run(util)
    operation.run(util)
    history.run(util)
    TandS.run(util)
    print('Done!')
