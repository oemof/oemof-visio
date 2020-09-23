import warnings
from oemof_visio import plot

try:
    from oemof_visio.energy_system_graph import ESGraphRenderer
except ModuleNotFoundError:
    warnings.warn(
        "If you want to render the energy system network in a graph you need to install "
        "extra dependencies \n\n pip install oemof-visio[network]"
    )
