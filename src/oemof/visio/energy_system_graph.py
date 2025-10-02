# -*- coding: utf-8 -*-

"""Module to render an oemof energy model network in a graph.
SPDX-FileCopyrightText: Pierre-Francois Duc <pierre-francois.duc@rl-institut.de>
SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-License-Identifier: MIT
"""

import logging
import warnings
import math
import os
import plotly.graph_objs as go

try:
    import graphviz

    GRAPHVIZ_MODULE = True
except ModuleNotFoundError:
    GRAPHVIZ_MODULE = False

try:
    from oemof.network.network import Bus, Sink, Source, Transformer

    NETWORK_MODULE = True
except ModuleNotFoundError:
    NETWORK_MODULE = False
# new with oemof-solph 0.5.2
from oemof.solph.buses._bus import Bus


try:
    from oemof.solph.components import (
        GenericStorage,
        Sink,
        Source,
        Converter,
        OffsetConverter,
        ExtractionTurbineCHP,
        GenericCHP,
    )
    from oemof.solph.views import node as view_node
except ModuleNotFoundError:
    GenericStorage = None

COLOR_SOURCE = "#A4ADFB"
COLOR_SINK = "#FFD6E0"
COLOR_STORAGE = "#90F1EF"
COLOR_CONVERTER = "#7BF1A8"


def fixed_width_text(text, char_num=10):
    """Add linebreaks every char_num characters in a given text.

    Parameters
    ----------
    text: obj:'str'
        text to apply the linebreaks
    char_num: obj:'int'
        max number of characters in a line before a line break
        Default: 10
    Returns
    -------
    obj:'str'
        the text with line breaks after every char_num characters

    Examples
    --------
    >>> fixed_width_text("12345", char_num=2)
    '12\\n34\\n5'
    >>> fixed_width_text("123456")
    '123456'
    >>> fixed_width_text("12345", 5)
    '12345'
    >>> fixed_width_text("", 2)
    ''
    """
    # integer number of lines of `char_num` character
    n_lines = math.ceil(len(text) / char_num)

    # split the text in lines of `char_num` character
    split_text = []
    for i in range(n_lines):
        split_text.append(text[(i * char_num) : ((i + 1) * char_num)])

    return "\n".join(split_text)


# TODO move this to network directly
def extern_connections(nnode):
    ext_inputs = []
    ext_outputs = []
    for sn in nnode.subnodes:
        if sn.subnodes:
            ext_in, ext_out = extern_connections(sn)
            ext_inputs.extend(ext_in)
            ext_outputs.extend(ext_out)
        if hasattr(sn, "inputs"):
            for i in sn.inputs:
                if i.depth < sn.depth:
                    ext_inputs.append(i)

        if hasattr(sn, "outputs"):
            for i in sn.outputs:
                if i.depth < sn.depth:
                    ext_outputs.append(i)

    return ext_inputs, ext_outputs


class ESGraphRenderer:
    def __init__(
        self,
        energy_system=None,
        filepath=None,
        img_format=None,
        legend=False,
        txt_width=40,
        txt_fontsize=10,
        **kwargs,
    ):
        """Render an oemof energy system using graphviz.

        Parameters
        ----------
        energy_system: `oemof.solph.network.EnergySystem`
            The oemof energy stystem

        filepath: str
            path, where the rendered result shall be saved, if an extension
            is provided, the format will be automatically adapted except if
            the `img_format` argument is provided
            Default: "energy_system.gv"

        img_format: str
            extension of the available image formats of graphviz (e.g "png",
            "svg", "pdf", ... )
            Default: "pdf"

        legend: bool
            specify, whether a legend will be added to the graph or not
            Default: False

        txt_width: int
            max number of characters in a line before a line break
            Default: 10

        txt_fontsize: int
            fontsize of the image's text (components labels)
            Default: 10

        **kwargs: various
            optional arguments of the graphviz.Digraph() class

        Returns
        -------
        None: render the generated dot graph in the filepath
        """
        missing_modules = []
        if NETWORK_MODULE is False or GRAPHVIZ_MODULE is False:
            if NETWORK_MODULE is False:
                missing_modules.append("oemof.network")
            if GRAPHVIZ_MODULE is False:
                missing_modules.append("graphviz")
            raise ModuleNotFoundError(
                "You have to install the following packages to plot a graph\n"
                "pip install {0}".format(" ".join(missing_modules))
            )
        self.max_depth = None
        self.energy_system = energy_system
        if filepath is not None:
            file_name, file_ext = os.path.splitext(filepath)
        else:
            file_name = "energy_system"
            file_ext = ""

        kwargs.update(dict(filename=file_name))

        # if the `img_format` argument is not provided then the format is
        # automatically inferred from the file extension or defaults to "pdf"
        if img_format is None:
            if file_ext != "":
                img_format = file_ext.replace(".", "")
            else:
                img_format = "pdf"

        self.legend = legend
        self.img_format = img_format
        self.digraph_kwargs = kwargs
        self.txt_width = txt_width
        self.txt_fontsize = str(txt_fontsize)

    def add_components(self, components, subgraph=None, depth=0):
        subnetworks = [
            n for n in components if n.depth == depth and n.subnodes
        ]
        atomicnodes = [
            n
            for n in components
            if n.depth == depth and not n.subnodes
        ]

        # draw the subnetworks recursively
        if subnetworks:
            for sn in subnetworks:
                self.add_subnetwork(sn, subgraph=subgraph, depth=depth)


        if atomicnodes:
            components_to_add = atomicnodes

        busses = []

        for nd in components_to_add:
            # make sur the label is a string and not a tuple
            label = str(nd.label)
            if nd.depth <= self.max_depth:
                if isinstance(nd, Bus):
                    self.add_bus(label, subgraph=subgraph)
                    # keep the bus reference for drawing edges later
                    busses.append(nd)
                elif isinstance(nd, Sink):
                    self.add_sink(label, subgraph=subgraph)
                elif isinstance(nd, Source):
                    self.add_source(label, subgraph=subgraph)
                elif isinstance(nd, OffsetConverter):
                    self.add_transformer(label, subgraph=subgraph)
                elif isinstance(nd, GenericCHP):
                    self.add_chp(label, subgraph=subgraph)
                elif isinstance(nd, ExtractionTurbineCHP):
                    self.add_chp(label, subgraph=subgraph)
                elif isinstance(nd, Converter):
                    self.add_transformer(label, subgraph=subgraph)
                elif isinstance(nd, Transformer):
                    self.add_transformer(label, subgraph=subgraph)
                elif isinstance(nd, GenericStorage):
                    self.add_storage(label, subgraph=subgraph)
                else:
                    logging.warning(
                        "The oemof component {} of type {} is not implemented in "
                        "the rendering method of the energy model graph drawer. "
                        "It will be therefore rendered as an ellipse".format(
                            nd.label, type(nd)
                        )
                    )
                    self.add_component(label, subgraph=subgraph)

            else:
                if isinstance(nd, Bus):
                    busses.append(nd)
        # draw the edges between the nodes based on each bus inputs/outputs
        for bus in busses:
            for component in bus.inputs:
                # draw an arrow from the component to the bus
                self.connect(component, bus)
            for component in bus.outputs:
                self.connect(bus, component)
        self.busses.extend(busses)

    def add_subnetwork(self, sn, subgraph=None, depth=0):
        if subgraph is None:
            dot = self.dot
        else:
            dot = subgraph

        with dot.subgraph(name="cluster_" + str(sn.label)) as c:
            # color of the box
            c.attr(color="black")
            # title of the box
            c.attr(label=str(sn.label))
            self.add_components(sn.subnodes, subgraph=c, depth=depth + 1)
            if depth + 1 <= self.max_depth:
                pass
            else:
                ext_inputs, ext_outputs = extern_connections(sn)

                self.max_depth_connexions.extend([(i, sn) for i in ext_inputs])
                self.max_depth_connexions.extend([(sn, o) for o in ext_outputs])

                # draw a component at the depth limit
                if sn.depth <= self.max_depth:
                    dot.node(
                        fixed_width_text(str(sn.label), char_num=self.txt_width),
                        shape="rectangle",
                        style="dashed",
                        color="grey",
                        fontsize=self.txt_fontsize,
                    )

                # collect the information about potential connections (no node will be drawn)
                self.add_components(sn.subnodes, subgraph=c, depth=depth + 1)

    def add_bus(self, label="Bus", subgraph=None):
        if subgraph is None:
            dot = self.dot
        else:
            dot = subgraph
        dot.node(
            label,
            shape="rectangle",
            fontsize="10",
            fixedsize="shape",
            width="4.1",
            height="0.3",
            style="filled",
            color="lightgrey",
            tooltip=label,
        )

    def add_sink(self, label="Sink", subgraph=None):
        if subgraph is None:
            dot = self.dot
        else:
            dot = subgraph
        dot.node(
            fixed_width_text(label, char_num=self.txt_width),
            shape="trapezium",
            color=COLOR_SINK,
            fontsize=self.txt_fontsize,
        )

    def add_source(self, label="Source", subgraph=None):
        if subgraph is None:
            dot = self.dot
        else:
            dot = subgraph
        dot.node(
            fixed_width_text(label, char_num=self.txt_width),
            shape="invtrapezium",
            color=COLOR_SOURCE,
            fontsize=self.txt_fontsize,
        )

    def add_transformer(self, label="Transformer", subgraph=None):
        if subgraph is None:
            dot = self.dot
        else:
            dot = subgraph
        dot.node(
            fixed_width_text(label, char_num=self.txt_width),
            shape="rectangle",
            color=COLOR_CONVERTER,
            fontsize=self.txt_fontsize,
        )

    def add_chp(self, label="CHP", subgraph=None):
        if subgraph is None:
            dot = self.dot
        else:
            dot = subgraph
        dot.node(
            fixed_width_text(label, char_num=self.txt_width),
            shape="rectangle",
            fontsize=self.txt_fontsize,
            style="filled",
            fillcolor="yellow;0.1:blue",
            # color="magenta",
        )

    def add_storage(self, label="Storage", subgraph=None):
        if subgraph is None:
            dot = self.dot
        else:
            dot = subgraph
        dot.node(
            fixed_width_text(label, char_num=self.txt_width),
            shape="rectangle",
            style="rounded",
            color=COLOR_STORAGE,
            fontsize=self.txt_fontsize,
        )

    def add_component(self, label="component", subgraph=None):
        if subgraph is None:
            dot = self.dot
        else:
            dot = subgraph
        dot.node(
            fixed_width_text(label, char_num=self.txt_width),
            fontsize=self.txt_fontsize,
        )

    def connect(self, a, b):
        """Draw an arrow from node a to node b

        Parameters
        ----------
        a: `oemof.solph.network.Node`
            An oemof node (usually a Bus or a Component)

        b: `oemof.solph.network.Node`
            An oemof node (usually a Bus or a Component)
        """


        if a.depth <= self.max_depth and b.depth <= self.max_depth:
            if not isinstance(a, Bus):
                a = fixed_width_text(str(a.label), char_num=self.txt_width)
            else:
                a = str(a.label)
            if not isinstance(b, Bus):
                b = fixed_width_text(str(b.label), char_num=self.txt_width)
            else:
                b = str(b.label)

            self.dot.edge(a, b, color="black")
        else:
            if isinstance(a, Bus):
                component = b
            else:
                component = a
            logging.debug(
                "IGNORED THE COMPONENT ",
                component,
                " as it is below the max depth",
            )

    def _generate_graph(self, max_depth=None):
        self.dot = graphviz.Digraph(format=self.img_format, **self.digraph_kwargs)
        self.busses = []
        self.max_depth_connexions = []
        if max_depth is not None:
            if max_depth >= 0:
                self.max_depth = max_depth
            else:
                logging.warning("The max_depth cannot be lower than 0")
        else:
            self.max_depth = max([n.depth for n in self.energy_system.nodes])

        if self.legend is True:
            with self.dot.subgraph(name="cluster_1") as c:
                # color of the legend box
                c.attr(color="black")
                # title of the legend box
                c.attr(label="Legends")
                self.add_bus(subgraph=c)
                self.add_sink(subgraph=c)
                self.add_source(subgraph=c)
                self.add_transformer(subgraph=c)
                self.add_storage(subgraph=c)

        # draw a node for each of the energy_system's component.
        # the shape depends on the component's type.
        self.add_components(self.energy_system.nodes)

        for link in self.max_depth_connexions:
            self.connect(*link)

    def view(self, max_depth=None, **kwargs):
        """Call the view method of the DiGraph instance"""
        self._generate_graph(max_depth)
        self.dot.view(**kwargs)

    def render(self, max_depth=None, **kwargs):
        """Call the render method of the DiGraph instance"""
        self._generate_graph(max_depth)
        fname = self.dot.render(cleanup=True, **kwargs)
        logging.info(
            f"The energy system graph was saved under '{fname}' in the current directory"
        )
        return self.dot

    def pipe(self, max_depth=None, **kwargs):
        """Call the pipe method of the DiGraph instance"""
        self._generate_graph(max_depth)
        self.dot.pipe(**kwargs)

    def source(self, max_depth=None):
        self._generate_graph(max_depth)
        return self.dot.source

    def sankey(self, results, ts=None):
        """Return a dict to a plotly sankey diagram"""
        busses = []

        labels = []
        sources = []
        targets = []
        values = []

        # bus_data.update({bus: solph.views.node(results_main, bus)})

        # draw a node for each of the network's component.
        # The shape depends on the component's type
        for nd in self.energy_system.nodes:
            label = str(nd.label)
            if isinstance(nd, Bus):

                # keep the bus reference for drawing edges later
                bus = nd
                busses.append(bus)

                bus_label = bus.label

                labels.append(label)

                flows = view_node(results, bus_label)["sequences"]

                # draw an arrow from the component to the bus
                for component in bus.inputs:
                    if component.label not in labels:
                        labels.append(component.label)

                    sources.append(labels.index(component.label))
                    targets.append(labels.index(bus_label))

                    val = flows[((component.label, bus_label), "flow")].sum()
                    if ts is not None:
                        val = flows[((component.label, bus_label), "flow")][ts]
                    # if val == 0:
                    #     val = 1
                    values.append(val)

                for component in bus.outputs:
                    # draw an arrow from the bus to the component
                    if component.label not in labels:
                        labels.append(component.label)

                    sources.append(labels.index(bus_label))
                    targets.append(labels.index(component.label))

                    val = flows[((bus_label, component.label), "flow")].sum()
                    if ts is not None:
                        val = flows[((bus_label, component.label), "flow")][ts]
                    # if val == 0:
                    #     val = 1
                    values.append(val)

        fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=labels,
                        hovertemplate="Node has total value %{value}<extra></extra>",
                        color="blue",
                    ),
                    link=dict(
                        source=sources,  # indices correspond to labels, eg A1, A2, A2, B1, ...
                        target=targets,
                        value=values,
                        hovertemplate="Link from node %{source.label}<br />"
                        + "to node%{target.label}<br />has value %{value}"
                        + "<br />and data <extra></extra>",
                    ),
                )
            ]
        )

        fig.update_layout(title_text="Basic Sankey Diagram", font_size=10)
        return fig.to_dict()
