# -*- coding: utf-8 -*-

"""

Tested using the following versions of the dependencies:
* oemof.network>=0.5.1
* oemof.solph>=0.6.1
* oemof.visio>=0.0.3a1

"""
###########################################################################
# imports
###########################################################################

import logging

from oemof.network import Node

from oemof.solph import EnergySystem
from oemof.solph import buses
from oemof.solph import components
from oemof.solph import create_time_index
from oemof.solph import flows


def main():

    logging.info("Initialize the energy system")
    date_time_index = create_time_index(2012, number=3)

    # create the energysystem and assign the time index
    energysystem = EnergySystem(timeindex=date_time_index, infer_last_interval=False)
    ##########################################################################
    # Create oemof objects
    ##########################################################################

    logging.info("Create oemof objects")

    bus = buses.Bus(label="bus1_d1")
    bus2 = buses.Bus(label="bus2_d1")
    energysystem.add(bus, bus2)

    energysystem.add(
        components.Sink(
            label="sink_d1",
            inputs={bus: flows.Flow()},
        )
    )
    source_dep_1 = components.Source(
        label="source_d1",
        outputs={bus2: flows.Flow(variable_costs=0.1)},
    )

    energysystem.add(source_dep_1)
    energysystem.add(
        components.Converter(
            label="converter_d1",
            inputs={bus2: flows.Flow()},
            outputs={bus: flows.Flow()},
        )
    )

    sn = Node("sn_d1")

    bus_dep_2 = sn.subnode(
        buses.Bus,
        "bus_d2",
    )

    conv_dep_2 = sn.subnode(
        components.Converter,
        "converter_d2",
        inputs={bus2: flows.Flow(), bus_dep_2: flows.Flow()},
        outputs={bus: flows.Flow()},
    )

    sn2 = sn.subnode(
        Node,
        "sn_d2",
    )

    bus_dep_3 = sn2.subnode(
        buses.Bus,
        "bus_d3",
    )

    source_dep_1.outputs.update({bus_dep_3: flows.Flow()})

    conv_dep_3 = sn2.subnode(
        components.Converter,
        "converter_d3",
        inputs={bus_dep_3: flows.Flow()},
        outputs={bus_dep_2: flows.Flow()},
    )

    source_dep_3 = sn2.subnode(
        components.Source,
        "source_d3",
        outputs={bus_dep_3: flows.Flow()},
    )

    energysystem.add(sn)

    from oemof.visio import ESGraphRenderer

    gr = ESGraphRenderer(energy_system=energysystem, filepath="depth_example.pdf")
    for i in [2, 1, 0]:
        gr.render(max_depth=i, filename=f"depth_example_{i}", format="png")
    # gr.render()
    #
    # # from graphviz import Digraph
    # #
    #
    # #
    # # graph = Digraph(body=dot_text)
    # #
    # # import pdb;pdb.set_trace()
    #
    # with open("graph.dot", "w") as f:
    #     f.write(gr.source())
    #
    # with open("ref_graph.dot") as f:
    #     ref_dot = f.read()
    #
    # with open("graph.dot") as f:
    #     to_compare_dot = f.read()
    #
    # print(gr.source() == to_compare_dot)

    # from oemof.visio import ESGraphRenderer
    # gr = ESGraphRenderer(energy_system=energysystem)
    #
    # with open("ref_graph.dot") as f:
    #     ref_dot = f.read()
    #
    # assert gr.source() == ref_dot
    # import pdb;
    # pdb.set_trace()


if __name__ == "__main__":
    main()
