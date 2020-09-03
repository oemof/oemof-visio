import os
import graphviz
import oemof.solph
import logging


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
    """
    # total number of characters in the text
    text_length = len(text)
    # integer number of lines of `char_num` character
    n_lines = int(text_length / char_num)
    # number of character in the last line
    last_line_length = text_length % char_num

    # split the text in lines of `char_num` character
    split_text = []
    for i in range(n_lines):
        split_text.append(text[(i * char_num) : ((i + 1) * char_num)])

    # I if the last line is not empty
    if n_lines > 0:
        if last_line_length > 0:
            split_text.append(text[((i + 1) * char_num) :])
        answer = "\n".join(split_text)
    else:
        answer = text
    return answer


class ESGraphRenderer:
    def __init__(
        self,
        energy_system=None,
        filepath="energy_system",
        img_format=None,
        legend=False,
        txt_width=10,
        txt_fontsize=10,
        **kwargs
    ):
        """Render an oemof energy system using graphviz.

        Parameters
        ----------
        energy_system: `oemof.solph.network.EnergySystem`
            The oemof energy stystem

        filepath: str
            path, where the rendered result shall be saved, if an extension is provided, the format
            will be automatically adapted except if the `img_format` argument is provided
            Default: "energy_system"

        img_format: str
            extension of the available image formats of graphviz (e.g "png", "svg", "pdf", ... )
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
        file_name, file_ext = os.path.splitext(filepath)

        # if the `img_format` argument is not provided then the format is
        # automatically inferred from the file extension or defaults to "pdf"
        if img_format is None:
            if file_ext != "":
                img_format = file_ext.replace(".", "")
            else:
                img_format = "pdf"

        self.dot = graphviz.Digraph(filename=file_name, format=img_format, **kwargs)
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
            if isinstance(nd, oemof.solph.network.Bus):
                self.add_bus(nd.label)
                # keep the bus reference for drawing edges later
                self.busses.append(nd)
            elif isinstance(nd, oemof.solph.network.Sink):
                self.add_sink(nd.label)
            elif isinstance(nd, oemof.solph.network.Source):
                self.add_source(nd.label)
            elif isinstance(nd, oemof.solph.network.Transformer):
                self.add_transformer(nd.label)
            elif isinstance(nd, oemof.solph.components.GenericStorage):
                self.add_storage(nd.label)
            else:
                logging.warning(
                    "The oemof component {} of type {} is not implemented in the rendering "
                    "method of the energy model graph drawer. It will be therefore"
                    "rendered as an ellipse".format(nd.label, type(nd))
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
        )

    def add_sink(self, label="Sink", subgraph=None):
        if subgraph is None:
            dot = self.dot
        else:
            dot = subgraph
        dot.node(
            fixed_width_text(label, char_num=self.txt_width),
            shape="trapezium",
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
            fontsize=self.txt_fontsize,
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
        if not isinstance(a, oemof.solph.network.Bus):
            a = fixed_width_text(a.label, char_num=self.txt_width)
        else:
            a = a.label
        if not isinstance(b, oemof.solph.network.Bus):
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


if __name__ == "__main__":
    from oemof.solph import Sink, Source, Transformer, Bus, Flow, EnergySystem
    energysystem = EnergySystem()
    bus_ac = Bus(label="AC")
    bus_dc = Bus(label="DC")
    wind = Source(label="wind", outputs={bus_ac: Flow()})
    pv = Source(label="pv", outputs={bus_dc: Flow()})
    demand_el = Sink(label="demand_el", inputs={bus_ac: Flow()})
    storage_el = oemof.solph.components.GenericStorage(
        label="storage_el",
        inputs={bus_ac: Flow()},
        outputs={bus_ac: Flow()},
    )
    pv_converter = Transformer(
        label="chp_gas", inputs={bus_dc: Flow()}, outputs={bus_ac: Flow()}
    )
    excess_el = Sink(label="excess_el", inputs={bus_ac: Flow()})
    energysystem.add(
        bus_ac, bus_dc, wind, pv, demand_el, storage_el, excess_el, pv_converter
    )
    gr = ESGraphRenderer(energysystem)
    gr.view()
