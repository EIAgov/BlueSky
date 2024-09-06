import pandas as pd
import numpy as np

# storage currently limited to salt caverns, but could change in future with technology and enviornmental assessments
def clean_storage_cap(util):
    # load and clean salt cavern cap data 
    df = pd.read_csv(util.base_dir + util.inputKeys.loc['saltCavernCapHist', 'path'], index_col=0, header=0)
    # find earliest capacity year and build year from there to last history year
    hyears = np.arange(df.min()['Start'], util.last_hYear + 1)
    final = pd.DataFrame(data={'histyear': hyears, 'regCen': 'WSCentral', 'storageTech': 'SaltCavern','hist_storage_cap': 0})
    df.sort_values(by='Start', ascending=True, inplace=True)

    # fill historical dataset cumulatively with capacity
    for i in df['Start']:
        # for each start year, add that capacity to the dataframe for that year going forward
        temp = final.loc[final['histyear'] >= i]
        temp['hist_storage_cap'] = temp['hist_storage_cap'] + int(df.loc[df['Start'] == i]['Volume_cubic_meters'])
        final.update(temp)

    # convert from cubic meters to kg of hydrogen
    final['hist_storage_cap'] = final['hist_storage_cap'] * .08
    # remove years before nems first history year
    final = final.loc[final['histyear'] >= util.first_hYear]
    final['histyear'] = final['histyear'].astype(str)
    util.write_aimms_output(final, ['hist_storage_cap'], util.base_dir + util.outputKeys.loc['hist_storage_cap', 'path'], note='multiple sources, see data readme', unit='kg of usable h2')

def clean_smr_prod_cap_hist(util):
    
    # SMR with CCS cap history
    df = pd.read_excel(util.base_dir + util.inputKeys.loc['smr_ccs_cap', 'path'])[['skip', 'Start_year', 'Project status', 'State', 'CO2 capacity (MMt/yr)']].dropna()
    # convert CO2 caputure rate to kilograms of hydrogen production using H2A assumptions. Assuming 9.97 (kg CO2/kg H2)
    # converting to metric ton of C02 a year to kiliogram of C02 to kilogram of H2
    df = df.loc[df['skip'] == 0]
    df['cap'] = df['CO2 capacity (MMt/yr)'] * 1000000 * 1000 / 9.97
    ccs = df.merge(util.state_census_map, how='inner', left_on='State', right_on='reg')
    ccs['histyear'] = ccs['Start_year'].astype('int64')
    ccs.sort_values(by='histyear', ascending=True, inplace=True)
    # build out history and fill capacity moving forward
    hyears = np.arange(ccs.min()['histyear'], ccs.max()['histyear'] + 1)
    full_ccs = pd.DataFrame(data={'histyear': hyears.astype('int64'), 'hist_cap': 0})
    census_df = pd.DataFrame(data={'r_cen': util.census})
    full_ccs = full_ccs.merge(census_df, how='cross')
    full_ccs = full_ccs.merge(ccs[['histyear', 'r_cen', 'cap']], how='left', on=['histyear', 'r_cen']).fillna(0).drop('hist_cap', axis=1)
    full_ccs.set_index('histyear', inplace=True)
    full_ccs['total_cap'] = full_ccs.groupby('r_cen').cumsum()
    full_ccs.reset_index(inplace=True)
    full_ccs.rename(columns={'total_cap': 'ccs_cap', 'r_cen': 'regCEN'}, inplace=True)
    full_ccs.drop('cap', axis=1, inplace=True)


    # Refinery SMR history
    df = pd.read_excel(util.base_dir + util.inputKeys.loc['refinery_smr_hist', 'path'], sheet_name='Data 1', skiprows=1)
    # create state mappings out of the source key
    states = [s[10:-2] for s in df.columns]
    states[0] = 'histyear'
    df.columns = states
    df['histyear'] = df['histyear'].apply(lambda x: str(x)[0:4])
    df.drop(0, inplace=True)
    df = pd.melt(df, id_vars='histyear', var_name='State', value_name='cap')
    ref_state = df.merge(util.state_census_map, how='inner', left_on='State', right_on='reg')
    # group by census regiona and year and sum
    ref_state = ref_state[['histyear', 'r_cen', 'cap']].groupby(by=['histyear', 'r_cen'], group_keys=True, as_index=False).sum()
    # convert from million cubic feet per day to kg per year
    ref_state['cap'] = ref_state['cap'] * 1000000 * 365 *.00236


    # Non-industrial SMR capacity from the industrial team. Assuming supply equals demand with a utilizaton adjustment
    df = pd.read_excel(util.base_dir + util.inputKeys.loc['smr_cap', 'path'])
    cap = df.melt(id_vars='region', var_name = 'histyear', value_name='hist_prod_cap')
    cap.rename(columns={'region': 'regCEN'}, inplace=True)
    cap['prodTech'] = 'SMR'
    cap = cap[['histyear', 'regCEN', 'prodTech', 'hist_prod_cap']]
    # convert from trillion btu's a year to mmbtu to GJ to kilogram
    cap['hist_prod_cap'] = cap['hist_prod_cap'] * 1000000 * 1.055 / 0.120211638
    # assume capacity supply is working at 90% capacity, essentially adding 10% on top of supply
    cap['hist_prod_cap'] = cap['hist_prod_cap'] * 1.1
    cap['histyear'] = cap['histyear'].astype('int64')

    # add refinery capacity
    ref_state['histyear'] = ref_state['histyear'].astype('int64')
    ref_cap = ref_state.loc[ref_state['histyear'] >= cap['histyear'].min()]
    ref_cap.rename(columns={'r_cen': 'regCEN', 'cap': 'ref_cap'}, inplace=True)
    cap = cap.merge(ref_cap, how='left')
    cap['ref_cap'] = cap['ref_cap'].fillna(0)
    cap['hist_prod_cap'] += cap['ref_cap'] 
    cap = cap.drop('ref_cap', axis=1)

    # subtract off SMR_CCS values and then add them in as separate line items
    tmp_ccs = full_ccs.loc[(full_ccs['histyear'] >= cap['histyear'].min()) & (full_ccs['histyear'] <= util.last_hYear)]
    cap = cap.merge(tmp_ccs, how='left')
    cap['ccs_cap'] = cap['ccs_cap'].fillna(0)
    cap['hist_prod_cap'] -= cap['ccs_cap']
    cap = cap.drop('ccs_cap', axis=1)
    
    tmp_ccs['prodTech'] = 'SMR_CCS'
    tmp_ccs.rename(columns={'ccs_cap': 'hist_prod_cap'}, inplace=True)
    tmp_ccs = tmp_ccs[['histyear', 'regCEN','prodTech', 'hist_prod_cap']]
    #cap['histyear'] = cap['histyear'].astype('str')
    cap = pd.concat([cap, tmp_ccs])

    util.write_aimms_output(cap, ['histyear', 'hist_prod_cap'], util.base_dir + util.outputKeys.loc['hist_prod_cap', 'path'], note='EIA estimates', unit='annual kg of H2')

    # write future SMR_CCS planned capacity
    future_ccs = ccs.loc[(ccs['histyear'] > util.last_hYear) & (ccs['cap'] > 0)].copy()
    future_ccs['prodTech'] = 'SMR_CCS'
    future_ccs = future_ccs[['histyear', 'r_cen', 'prodTech', 'cap']].groupby(['histyear', 'prodTech', 'r_cen']).sum().reset_index()
    future_ccs.rename(columns={'histyear': 'i_calYear', 'r_cen': 'regCEN', 'cap': 'planned_cap'}, inplace=True)
    future_ccs = future_ccs[['i_calYear', 'regCEN', 'prodTech', 'planned_cap']]
    util.write_aimms_output(future_ccs, ['i_calYear','planned_cap'], util.base_dir + util.outputKeys.loc['planned_cap', 'path'], note='From refined frame a announced projects',
     unit='Annual NEW capacity in kg of hydrogen. Not cumulative')
    
def clean_electrolyzer_prod_cap_hist(util):
    df = pd.read_excel(util.base_dir + util.inputKeys.loc['electrolyzer_cap', 'path'])
    df = df[['Geography','Electrolyzer capacity (MW)', 'Project status', 'Estimated start of operation', 'Electrolysis technology','Application', 'Power source', 'State']]

    # off grid history rules. Geography=United States, capacity > 0, estimated start of operation between 1990 and last historical year, technology = PEM
    elec_hist = df.copy()
    geo = elec_hist['Geography'] == 'United States'
    cap = elec_hist['Electrolyzer capacity (MW)'] > 0
    tech = elec_hist['Electrolysis technology'] == 'PEM'
    firstYear = elec_hist['Estimated start of operation'].astype('Int64') > util.first_hYear-1 
    lastYear = elec_hist['Estimated start of operation'].astype('Int64') <= util.last_hYear
    elec_hist = elec_hist.loc[geo & cap & tech & firstYear & lastYear]
    elect_hist = elec_hist.merge(util.state_census_map,  how='inner', left_on='State', right_on='reg')
    elect_hist.groupby('r_cen').sum('Electrolyzer capacity (MW)')

    # off grid planned capacity rules. Same as history, but years are greater than the last history year
    elec_planned = df.copy()
    geo = elec_planned['Geography'] == 'United States'
    cap = elec_planned['Electrolyzer capacity (MW)'] > 0
    tech = elec_planned['Electrolysis technology'] == 'PEM'
    firstYear = elec_planned['Estimated start of operation'].astype('Int64') > util.last_hYear
    elec_planned = elec_planned.loc[geo & cap & tech & firstYear]
    elec_planned = elec_planned.merge(util.state_census_map,  how='inner', left_on='State', right_on='reg')
    elec_planned.groupby('r_cen').sum('Electrolyzer capacity (MW)')

    # learning rate electrolyzer criteria. same as history but expanding geography to global
    learning_cap = df.copy()
    cap = learning_cap['Electrolyzer capacity (MW)'] > 0
    tech = learning_cap['Electrolysis technology'] == 'PEM'
    lastYear = learning_cap['Estimated start of operation'].astype('Int64') <= util.last_hYear
    learning_cap = learning_cap.loc[cap & tech & lastYear]
    cap = learning_cap[['Electrolyzer capacity (MW)']].sum()
    # convert MW capacity into annual max theoretical production
    # assuming 1 MW capacity converts to 1,000 kWh and it takes 55 kWh to make a kilogram of hydrogen and that runs year round
    cap = cap * 1000 / 55 * 8760
    util.write_single_value_param(cap[0], "electrolyzer_learning_cap", util.base_dir + util.outputKeys.loc['electrolyzer_learning_cap', 'path'], 
                                  note="Global PEM With Estimated start construction <= 2023", unit= "Annual kg of hydrogen. Max theoretical assuming 8760 hours of production a year")


def run(util):
    print('running history.py')
    clean_storage_cap(util)
    clean_smr_prod_cap_hist(util)
    clean_electrolyzer_prod_cap_hist(util)