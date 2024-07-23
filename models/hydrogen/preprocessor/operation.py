import pandas as pd

def clean_census_indexed_op(util):
    """Output O&M costs and capacity expansion costs for non electrolyzer production methods"""

    #1 Operations and Mainentance costs non_electrolyzer
    df = pd.read_csv(util.base_dir + util.inputKeys.loc['OM_nonElectrolyzer', 'path'], index_col=0, header=0)
    
    #deflate prices
    df['OM_cost'] = df['OM_cost'] / df['year'].apply(util.deflate_prices)
  
    #add census regions and seasons
    reg_df = pd.DataFrame({'regCen': util.census})
    seas_df = pd.DataFrame({'seas': util.seas})
    index_df = reg_df.merge(seas_df, how='cross')
    df = index_df.merge(df.reset_index(), how='cross')

    # reorganize and rename indexes
    df = df[['seas', 'regCen','technology', 'OM_cost']]
    df.rename(columns={'OM_cost': 'base_FixedOM_NonElectrolyzer', 'technology': 'prodTech'}, inplace=True)
    util.write_aimms_output(df, ['base_FixedOM_NonElectrolyzer'], util.base_dir + util.outputKeys.loc['FixedOM_NonElectrolyzer', 'path'], note='Sourced from H2A. discounted over lifetime with financials factored in', unit='$/kg of H2 produced')
     
    # non_electrolyzer variable O&M costs less energy
    df = pd.read_csv(util.base_dir + util.inputKeys.loc['nonElectrolyzerVarOM', 'path'], index_col=0, header=0)
    df = index_df.merge(df.reset_index(), how='cross')
    df = df[['seas', 'regCen','prodTech', 'value']]
    df.rename(columns={'value': 'base_VarOM_NonElectrolyzer', 'technology': 'prodTech'}, inplace=True)
    
    util.write_aimms_output(df, ['base_VarOM_NonElectrolyzer'], util.base_dir + util.outputKeys.loc['VarOM_NonElectrolyzer', 'path'], note='Sourced from H2A. Variable OM less energy', unit='$/kg of H2 produced')


    #2 capacity expansion costs
    df = pd.read_csv(util.base_dir + util.inputKeys.loc['PUC_nonElectrolyzer', 'path'], index_col=0, header=0)
    
    #deflate prices
    df['cap_cost'] = df['cap_cost'] / df['year'].apply(util.deflate_prices)
    
    #add census regions
    reg_df = pd.DataFrame({'regCen': util.census})
    df = reg_df.merge(df.reset_index(), how='cross')
    
    # reorganize and rename indexes
    df = df[['regCen','technology', 'cap_cost']]
    df.rename(columns={'cap_cost': 'base_PUCCostNonElectrolyzer', 'technology': 'prodTech'}, inplace=True)
    
    util.write_aimms_output(df, ['base_PUCCostNonElectrolyzer'], util.base_dir + util.outputKeys.loc['PUC_nonElectrolyzer', 'path'], note='Sourced from H2A. discounted over lifetime with financials factored in', unit='$/kg H2')

    #3 Operations and Mainentance costs electrolyzer
    df = pd.read_csv(util.base_dir + util.inputKeys.loc['OMCostElectrolyzer', 'path'], index_col=0, header=0)
    
    #deflate prices
    df['OMCostElectrolyzer'] = df['OMCostElectrolyzer'] / df['year'].apply(util.deflate_prices)

    #add nerc regions and seasons
    nerc_df = pd.DataFrame({'regNERC': util.nerc})
    seas_df = pd.DataFrame({'seas': util.seas})
    index_df = nerc_df.merge(seas_df, how='cross')
    df = index_df.merge(df.reset_index(), how='cross')

    # reorganize and rename indexes
    df = df[['seas', 'regNERC', 'technology', 'OMCostElectrolyzer']]
    df.rename(columns={'OMCostElectrolyzer': 'base_FixedOM_Electrolyzer', 'technology': 'prodTech'}, inplace=True)
    
    util.write_aimms_output(df, ['base_FixedOM_Electrolyzer'],
                                util.base_dir + util.outputKeys.loc['FixedOMCostElectrolyzer', 'path'],
                                note='Sourced from H2A. discounted over lifetime with financials factored in',
                                unit='$/kg of H2 produced')
    
        
    # variable O&M costs for electrolyzer less energy
    df = pd.read_csv(util.base_dir + util.inputKeys.loc['ElectrolyzerVarOM', 'path'], index_col=0, header=0)
    df = index_df.merge(df.reset_index(), how='cross')
    df = df[['seas', 'regNERC', 'prodTech', 'value']]
    df.rename(columns={'value': 'base_VarOM_Electrolyzer'}, inplace=True)
    
    util.write_aimms_output(df, ['base_VarOM_Electrolyzer'], util.base_dir + util.outputKeys.loc['VarOM_Electrolyzer', 'path'], note='Sourced from H2A. Variable OM less energy', unit='$/kg of H2 produced')
    
    #4 capacity expansion costs electrolyzer
    df = pd.read_csv(util.base_dir + util.inputKeys.loc['PUCCostElectrolyzer', 'path'], index_col=0, header=0)
    
    #deflate prices
    df['PUCCostElectrolyzer'] = df['PUCCostElectrolyzer'] / df['year'].apply(util.deflate_prices)
    
    #add nerc regions
    nerc_df = pd.DataFrame({'regNERC': util.nerc})
    df = nerc_df.merge(df.reset_index(), how='cross')

    
    # reorganize and rename indexes
    df = df[['regNERC', 'technology', 'PUCCostElectrolyzer']]
    df.rename(columns={'PUCCostElectrolyzer': 'base_PUCCostElectrolyzer', 'technology': 'prodTech'}, inplace=True)
    
    util.write_aimms_output(df, ['base_PUCCostElectrolyzer'],
                            util.base_dir + util.outputKeys.loc['PUCCostElectrolyzer', 'path'],
                            note='Sourced from H2A. discounted over lifetime with financials factored in',
                            unit='$/kg of H2 produced')
        
    #5 Feedstock Consumption
    df = pd.read_csv(util.base_dir + util.inputKeys.loc['FeedstockConsumption', 'path'])

    # reorganize and rename indexes
    df = df[['technology','fuel', 'FeedstockConsumption']]
    df.rename(columns={'technology': 'prodTech'}, inplace=True)
    
    util.write_aimms_output(df, ['FeedstockConsumption'],
                                util.base_dir + util.outputKeys.loc['FeedstockConsumption', 'path'],
                                note='H2a sourced. Natural Gas consumption only. All electricity feedstock re-categorized as HPConsumption',
                                unit='MMBtu/kg H2')
        
    #6 Electrolyzer Fuel Consumption
    df = pd.read_csv(util.base_dir + util.inputKeys.loc['ElectrolyzerFuelConsumption', 'path'])

    # reorganize and rename indexes
    df = df[['technology', 'fuel', 'ElectrolyzerFuelConsumption']]
    df.rename(columns={'technology': 'prodTech'}, inplace=True)
    
    util.write_aimms_output(df, ['ElectrolyzerFuelConsumption'],
                            util.base_dir + util.outputKeys.loc['ElectrolyzerFuelConsumption', 'path'],
                            note='H2a sourced. Electricity only.',
                            unit='kWh/kg H2')
        
        
    #7 Heat and Power Consumption
    df = pd.read_csv(util.base_dir + util.inputKeys.loc['HPConsumption', 'path'])
    df = df.melt(id_vars=['technology'], value_vars=['NG', 'electricity'], var_name='fuel', value_name='consumption')
   
 

    # reorganize and rename indexes
    df = df[['technology','fuel','consumption']]
    df.rename(columns={'consumption':'HPConsumption','technology': 'prodTech'}, inplace=True)
    #write NG to aimms
    
    util.write_aimms_output(df, ['HPConsumption'],
                                util.base_dir + util.outputKeys.loc['HPConsumption', 'path'],
                                note='Heat and Power from H2a. all electricity feedstock re-categorized as HPConsumption',
                                unit='natural gas: MMBtu/kg H2, electricity: kWh/kg H2')

    #8 CO2 Capture Rate
    df = pd.read_csv(util.base_dir + util.inputKeys.loc['CO2CaptureRate', 'path'])
    
    # reorganize and rename indexes
    df = df[['technology', 'capture_rate']]
    df.rename(columns={'capture_rate': 'CO2CaptureRate', 'technology': 'prodTech'}, inplace=True)
    
    util.write_aimms_output(df, ['CO2CaptureRate'], util.base_dir + util.outputKeys.loc['CO2CaptureRate', 'path'], note='Sourced from H2A', unit='kg CO2/kg H2')
    
def run(util):
    print('running operation.py')
    clean_census_indexed_op(util)
    print('operation.py complete')

    #comment