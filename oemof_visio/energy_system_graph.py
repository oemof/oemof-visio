# -*- coding: utf-8 -*-

"""Module to render an oemof energy model network in a graph.
SPDX-FileCopyrightText: Pierre-Francois Duc <pierre-francois.duc@rl-institut.de>
SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Patrik Schönfeldt
SPDX-License-Identifier: MIT
"""

import logging
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


class ESGraphRenderer:
    def __init__(
        self,
        energy_system=None,
        filepath=None,
        img_format=None,
        legend=False,
        txt_width=10,
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

        self.dot = graphviz.Digraph(format=img_format, **kwargs)
        self.txt_width = txt_width
        self.txt_fontsize = str(txt_fontsize)
        self.busses = []

        if legend is True:
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
        for nd in energy_system.nodes:
            # make sur the label is a string and not a tuple
            label = str(nd.label)
            if isinstance(nd, Bus):
                self.add_bus(nd.label)
                # keep the bus reference for drawing edges later
                self.busses.append(
                    nd
                )  # TODO here get the info from inputs and outputs and adapt the labels
            elif isinstance(nd, Sink):
                self.add_sink(nd.label)
            elif isinstance(nd, Source):
                self.add_source(nd.label)
            elif isinstance(nd, OffsetConverter):
                self.add_transformer(nd.label)
            elif isinstance(nd, GenericCHP):
                self.add_chp(nd.label)
            elif isinstance(nd, ExtractionTurbineCHP):
                self.add_chp(nd.label)
            elif isinstance(nd, Converter):
                self.add_transformer(nd.label)
            elif isinstance(nd, Transformer):
                self.add_transformer(nd.label)
            elif isinstance(nd, GenericStorage):
                self.add_storage(nd.label)
            else:
                logging.warning(
                    "The oemof component {} of type {} is not implemented in "
                    "the rendering method of the energy model graph drawer. "
                    "It will be therefore rendered as an ellipse".format(
                        nd.label, type(nd)
                    )
                )
                self.add_component(nd.label)

        # draw the edges between the nodes based on each bus inputs/outputs
        for bus in self.busses:
            for component in bus.inputs:
                # draw an arrow from the component to the bus
                self.connect(component, bus)
            for component in bus.outputs:
                # draw an arrow from the bus to the component
                self.connect(bus, component)

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
        if not isinstance(a, Bus):
            a = fixed_width_text(a.label, char_num=self.txt_width)
        else:
            a = a.label
        if not isinstance(b, Bus):
            b = fixed_width_text(b.label, char_num=self.txt_width)
        else:
            b = b.label

        self.dot.edge(a, b)

    def view(self, **kwargs):
        """Call the view method of the DiGraph instance"""
        self.dot.view(**kwargs)

    def render(self, **kwargs):
        """Call the render method of the DiGraph instance"""
        print(self.dot.render(**kwargs))
        return self.dot

    def pipe(self, **kwargs):
        """Call the pipe method of the DiGraph instance"""
        self.dot.pipe(**kwargs)

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
            if isinstance(nd, Bus):

                # keep the bus reference for drawing edges later
                bus = nd
                busses.append(bus)

                bus_label = bus.label

                labels.append(nd.label)

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
