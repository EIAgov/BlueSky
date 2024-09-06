import typing

# guard against circular import
if typing.TYPE_CHECKING:
    from model.h2_model import H2Model

# def __init__(self, model: h2_model, mode='standard', start_year=2025, end_year=2026):
#     self.grid = model.grid
#     self.mode = mode
#     self.start_year = start_year
#     self.end_year = end_year
#     m = model

#     if self.mode == 'standard':
#         self.time = 'annual'

#     if mode == 'integrated':
#         pass


def get_electricty_consumption(hm: 'H2Model', region, year):
    return sum(
        hm.electricity_consumption_rate[tech] * hm.h2_volume[hub, tech, year]
        for tech in hm.technology
        for hub in hm.grid.registry.regions[region].hubs.keys()
    )


def get_electricity_consumption_rate(hm: 'H2Model', tech):
    rates = {'PEM': 54.3, 'SMR': 5.1}
    return rates[tech]


def get_production_cost(hm: 'H2Model', hub, tech, year):
    if hm.mode == 'standard':
        if tech == 'PEM':
            return (
                hm.electricity_price[hm.grid.registry.hubs[hub].region.name, year]
                * hm.electricity_consumption_rate[tech]
            )
        elif tech == 'SMR':
            return (
                hm.gas_price[hm.grid.registry.hubs[hub].region.name, year]
                + hm.electricity_price[hm.grid.registry.hubs[hub].region.name, year]
                * hm.electricity_consumption_rate[tech]
            )
        else:
            return 0

    elif hm.mode == 'integrated':
        if tech == 'PEM':
            return (
                hm.electricity_price[hm.grid.registry.hubs[hub].region.name, year]
                * hm.electricity_consumption_rate[tech]
            )
        elif tech == 'SMR':
            return (
                hm.gas_price[hm.grid.registry.hubs[hub].region.name, year]
                + hm.electricity_price[hm.grid.registry.hubs[hub].region.name, year]
                * hm.electricity_consumption_rate[tech]
            )
        else:
            return 0


def get_elec_price(hm: 'H2Model', region, year):
    if hm.mode == 'standard':
        if hm.grid.registry.regions[region].data is None:
            return 0
        else:
            return hm.grid.registry.regions[region].get_data('electricity_cost')

    elif hm.mode == 'integrated':
        return hm.grid.registry.regions[region].get_data('electricity_cost')


def get_gas_price(hm: 'H2Model', region, year):
    if hm.grid.registry.regions[region].data is None:
        return 0

    else:
        return hm.grid.registry.regions[region].get_data('gas_cost')


def get_demand(hm: 'H2Model', region, time):
    if hm.mode == 'standard':
        if hm.grid.registry.regions[region].data is None:
            return 0
        else:
            return hm.grid.registry.regions[region].get_data('demand') * 1.05 ** (
                time - hm.year.first()
            )

    elif hm.mode == 'integrated':
        return hm.demand[region, time]

    return 0
