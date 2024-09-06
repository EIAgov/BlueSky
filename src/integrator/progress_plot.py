"""
A plotter that can be used for combined solves

Currently, this makes live plot.  It could be mod'ed to just save them to outputs
"""

from matplotlib import pyplot as plt, ticker
from pathlib import Path

from definitions import OUTPUT_ROOT

# some defaults

styles = {
    'H2': {'color': 'tab:blue', 'linestyle': 'dashed', 'alpha': 0.7},
    'ELEC': {'color': 'tab:orange', 'linestyle': 'dashdot', 'alpha': 0.7},
    'NET': {'color': 'tab:brown', 'linestyle': 'solid', 'alpha': 0.7},
    'Load': {'color': 'tab:green', 'linestyle': 'solid', 'alpha': 0.7},
    'Price': {'color': 'tab:cyan', 'linestyle': 'solid', 'alpha': 0.7},
}


def plot_it(
    h2_price_records=[],
    elec_price_records=[],
    h2_obj_records=[],
    elec_obj_records=[],
    h2_demand_records=[],
    elec_demand_records=[],
    load_records=[],
    elec_price_to_res_records=[],
):
    """cheap plotter of iterative progress"""

    fig, [ax1, ax2, ax3, ax4] = plt.subplots(4, 1, sharex=True, constrained_layout=True)  # type: ignore
    ax1_b = ax1.twinx()
    ax2_b = ax2.twinx()
    # ax2.set_yscale('log')
    ax3_b = ax3.twinx()
    ax4_b = ax4.twinx()
    ax4_b.set_yscale('log')

    # Labelling
    ax1.set_title('Cross-Demands of...')
    ax2.set_title('Price')
    ax4.set_title('OBJ Value')
    ax4.set_xlabel('Iteration')
    ax1.set_ylabel('H2')
    ax2.set_ylabel('H2')
    ax4.set_ylabel('H2')
    ax1_b.set_ylabel('ELEC')
    ax2_b.set_ylabel('ELEC')
    ax4_b.set_ylabel('ELEC/NET')
    ax3.set_ylabel('Load')
    ax3_b.set_ylabel('Price')
    ax3.set_title('Res Model Load & Price')

    p1a = ax1.plot(*list(zip(*h2_demand_records)), label='H2', **styles['H2'])
    p1b = ax1_b.plot(*list(zip(*elec_demand_records)), label='ELEC', **styles['ELEC'])
    ax1.legend(handles=p1a + p1b, reverse=True)

    p2a = ax2.plot(*list(zip(*h2_price_records)), label='H2', **styles['H2'])
    p2b = ax2_b.plot(*list(zip(*elec_price_records)), label='ELEC', **styles['ELEC'])
    ax2.legend(handles=p2a + p2b, reverse=True)

    p3a = ax3.plot(*list(zip(*load_records)), label='Load', **styles['Load'])
    p3b = ax3_b.plot(*list(zip(*elec_price_to_res_records)), label='Price', **styles['Price'])
    ax3.legend(handles=p3a + p3b, reverse=True)

    p4a = ax4.plot(*list(zip(*h2_obj_records)), label='H2', **styles['H2'])
    p4b = ax4_b.plot(*list(zip(*elec_obj_records)), label='ELEC', **styles['ELEC'])

    # let's compute and a net objective line, which will help compare
    # need to break these down in the odd case that the iterations don't line up
    net_obj_records = []
    h2_dict = dict(h2_obj_records)
    e_dict = dict(elec_obj_records)
    all_keys = h2_dict.keys() | e_dict.keys()
    for i in range(min(all_keys), max(all_keys) + 1):
        net_obj_records.append((i, h2_dict.get(i, 0) + e_dict.get(i, 0)))

    p4c = ax4_b.plot(*list(zip(*net_obj_records)), label='NET', **styles['NET'])

    ax4.legend(handles=p4a + p4b + p4c, reverse=True)

    # set the x-ticks to be on integer (iteration) values
    tick_spacing = 1
    ax4.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))

    # grid it
    ax1.grid(True)
    ax2.grid(True)
    ax3.grid(True)
    ax4.grid(True)
    plt.savefig(Path(OUTPUT_ROOT, 'iteration_check.png'), format='png', dpi=300)
    # plt.show()
