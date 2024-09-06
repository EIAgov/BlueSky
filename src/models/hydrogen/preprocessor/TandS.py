import pandas as pd


def clean_storage_data(util):
    # storage injection costs
    df = pd.read_csv(
        util.base_dir + util.inputKeys.loc['StorageINJCost', 'path'], index_col=0, header=0
    )

    # deflate prices
    df['StorageINJCost'] = df['StorageINJCost'] / df['year'].apply(util.deflate_prices)

    # add census regions
    reg_df = pd.DataFrame({'regCen': util.census})
    df = reg_df.merge(df.reset_index(), how='cross')

    # reorganize and rename indexes
    df = df[['regCen', 'technology', 'StorageINJCost']]
    df.rename(
        columns={'technology': 'storageTech', 'StorageINJCost': 'base_StorageINJCost'}, inplace=True
    )
    util.write_aimms_output(
        df,
        ['base_StorageINJCost'],
        util.base_dir + util.outputKeys.loc['StorageINJCost', 'path'],
        note='Sourced from FECM',
        unit='millions of BasisYear_$/yr',
    )

    # storage withdrawal costs

    df = pd.read_csv(
        util.base_dir + util.inputKeys.loc['StorageWTHCost', 'path'], index_col=0, header=0
    )

    # deflate prices
    df['StorageWTHCost'] = df['StorageWTHCost'] / df['year'].apply(util.deflate_prices)

    # add census regions
    reg_df = pd.DataFrame({'regCen': util.census})
    df = reg_df.merge(df.reset_index(), how='cross')

    # reorganize and rename indexes
    df = df[['regCen', 'technology', 'StorageWTHCost']]
    df.rename(
        columns={'technology': 'storageTech', 'StorageWTHCost': 'base_StorageWTHCost'}, inplace=True
    )
    util.write_aimms_output(
        df,
        ['base_StorageWTHCost'],
        util.base_dir + util.outputKeys.loc['StorageWTHCost', 'path'],
        note='Sourced from FECM',
        unit='BasisYear_$/kg mile',
    )

    # transportation cost

    df = pd.read_csv(util.base_dir + util.inputKeys.loc['TransportationCost', 'path'])
    regCENarcs = pd.read_csv(util.base_dir + util.inputKeys.loc['regCENarcs', 'path'])
    print(regCENarcs)
    regCENarcs['map_regCENarc'] = regCENarcs['map_regCENarc'].astype(str)
    # deflate prices
    df['TransportationCost'] = df['TransportationCost'] / df['year'].apply(util.deflate_prices)

    # add source and destination census regions

    df = regCENarcs.merge(df.reset_index(), how='cross')
    print(df)
    """
    reg_df = pd.DataFrame({'regCen': util.census})
    reg_j_df = pd.DataFrame({'regCen_j':util.census})
    reg_df = reg_df.merge(reg_j_df.reset_index(),how = 'cross')
    df = reg_df.merge(df.reset_index(), how='cross')
    """

    # reorganize and rename indexes
    df = df[['regCen', 'regCen_j', 'TransportationCost']]
    df.rename(columns={'TransportationCost': 'base_TransportationCost'}, inplace=True)
    util.write_aimms_output(
        df,
        ['base_TransportationCost'],
        util.base_dir + util.outputKeys.loc['TransportationCost', 'path'],
        note='Sourced from FECM',
        unit='BasisYear_$/kg mile',
    )

    # storage capacity expansion costs

    df = pd.read_csv(util.base_dir + util.inputKeys.loc['SUCCost', 'path'], index_col=0, header=0)

    # deflate prices
    df['SUCCost'] = df['SUCCost'] / df['year'].apply(util.deflate_prices)

    # add census regions
    reg_df = pd.DataFrame({'regCen': util.census})
    df = reg_df.merge(df.reset_index(), how='cross')

    # reorganize and rename indexes
    df = df[['regCen', 'technology', 'SUCCost']]
    df.rename(columns={'technology': 'storageTech', 'SUCCost': 'base_SUCCost'}, inplace=True)
    util.write_aimms_output(
        df,
        ['base_SUCCost'],
        util.base_dir + util.outputKeys.loc['SUCCost', 'path'],
        note='Sourced from FECM',
        unit='BasisYear_$/kg mile',
    )

    # transportation capacity expansion costs

    df = pd.read_csv(util.base_dir + util.inputKeys.loc['TUCCost', 'path'])

    # deflate prices
    df['TUCCost'] = df['TUCCost'] / df['year'].apply(util.deflate_prices)

    # add source and destination census regions
    reg_df = pd.DataFrame({'regCen': util.census})
    reg_j_df = pd.DataFrame({'regCen_j': util.census})
    reg_df = reg_df.merge(reg_j_df.reset_index(), how='cross')
    df = reg_df.merge(df.reset_index(), how='cross')

    # reorganize and rename indexes
    df = df[['regCen', 'regCen_j', 'TUCCost']]
    df.rename(columns={'TUCCost': 'base_TUCCost'}, inplace=True)
    util.write_aimms_output(
        df,
        ['base_TUCCost'],
        util.base_dir + util.outputKeys.loc['TUCCost', 'path'],
        note='Sourced from FECM',
        unit='BasisYear_$/kg mile',
    )

    return


def clean_pipeline_data(util):
    # representative pipelines were calculated between each each adjacent census division. Pass along total capital costs and energy intensity
    df = pd.read_excel(
        util.base_dir + util.inputKeys.loc['pipe_cost', 'path'], index_col=None, header=0
    )
    costs = df.copy()[['r1', 'r2', 'Energy Intensity (kWh/kg h2)', 'Total Capital Cost']]
    costs.replace(
        {
            'New England': 'NewEngland',
            'Middle Atlantic': 'MidAtlantic',
            'East North Central': 'ENCentral',
            'West North Central': 'WNCentral',
            'South Atlantic': 'SAtlantic',
            'East South Central': 'ESCentral',
            'West South Central': 'WSCentral',
            'Mountain': 'Mountain',
            'Pacific': 'Pacific',
        },
        inplace=True,
    )
    costs.rename(
        columns={
            'r1': 'regCen',
            'r2': 'regCen_j',
            'Energy Intensity (kWh/kg h2)': 'pipe_energy_intensity',
            'Total Capital Cost': 'pipe_tcc',
        },
        inplace=True,
    )

    util.write_aimms_output(
        costs,
        ['pipe_energy_intensity', 'pipe_tcc'],
        util.base_dir + util.outputKeys.loc['pipeline_costs', 'path'],
        note='Calculated as representative 18 inch pipelines',
        unit='TCC in 2023 USD and energy intensity in kWh/kg h2',
    )


def run(util):
    print('running TandS.py')
    clean_storage_data(util)
    clean_pipeline_data(util)
    print('TandS.py complete')
