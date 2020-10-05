
"""Module contains tools facilitating plotting

SPDX-FileCopyrightText: Uwe Krien <krien@uni-bremen.de>
SPDX-FileCopyrightText: Steffen Wekamp
SPDX-FileCopyrightText: Patrik Schönfeldt <patrik.schoenfeldt@dlr.de>

SPDX-License-Identifier: MIT
"""

import logging
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta
from matplotlib.widgets import Slider


def slice_df(df, date_from=None, date_to=None):
    r"""

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with time index to slice.
    date_from : datetime.datetime
        Start time. If not given the first value of the index is used.
    date_to : datetime.datetime
        End time. If not given the last value of the index is used.

    Returns
    -------
    pandas.DataFrame

    """
    if date_from is None:
        date_from = df.index[0]
    if date_to is None:
        date_to = df.index[-1]
    return df.loc[date_from:date_to]


def rearrange_df(df, order, quiet=False):
    r"""
    Change the order of the subset DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        Table to rearrange.
    order : list
        New order of columns
    quiet : bool
        If True the warning will be suppressed.

    Returns
    -------
    pandas.DataFrame

    Notes
    -----
    Columns that are not in the order list will be removed.
    """

    cols = list(df.columns.values)
    neworder = [x for x in list(order) if x in set(cols)]
    missing = [x for x in list(cols) if x not in set(order)]
    if len(missing) > 0 and not quiet:
        logging.warning(
            "Columns that are not part of the order list are removed: " +
            str(missing))
    return df[neworder]


def color_from_dict(colordict, df):
    r""" Method to convert a dictionary containing the components and its
    colors to a color list that can be directly used with the color
    parameter of the pandas plotting method.

    Parameters
    ----------
    colordict : dictionary
        A dictionary that has all possible components as keys and its
        colors as items.
    df : pd.DataFrame
        Table to fetch colors for..

    Returns
    -------
    list
        Containing the colors of all components of the subset attribute
    """
    tmplist = list(
        map(colordict.get, list(df.columns)))
    tmplist = ['#ff00f0' if v is None else v for v in tmplist]
    if len(tmplist) == 1:
        colorlist = tmplist[0]
    else:
        colorlist = tmplist

    return colorlist


def set_datetime_ticks(ax, dates, tick_distance=None, number_autoticks=3,
                       date_format='%d-%m-%Y %H:%M', offset=0, tight=False):
    r""" Set configurable ticks for the time axis. One can choose the
    number of ticks or the distance between ticks and the format.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        An axes object of matplotlib
    dates : pandas.index
        The datetime index of the sequences.
    tick_distance : real
        The distance between to ticks in hours. If not set autoticks are
        set (see number_autoticks).
    number_autoticks : int (default: 3)
        The number of ticks on the time axis, independent of the time
        range. The higher the number of ticks is, the shorter should be the
        date_format string.
    date_format : string (default: '%d-%m-%Y %H:%M')
        The string to define the format of the date and time. See
        https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
        for more information.
    offset : int
        Normally the xticks start with the first value but it is possible to
        define an offset. An offset of 12 hours will set the tick to midday
        instead of the beginning of the day (12:00 instead of 0:00).
    tight : bool
        If set to True unused space on the x-axis will be avoided
        (experimental).
    """
    if tick_distance is None:
        tick_distance = int(len(dates) / number_autoticks) - 1

    ax.set_xticks(range(0 + offset, len(dates) - 1, tick_distance),
                  minor=False)
    ax.set_xticklabels(
        [item.strftime(date_format)
         for item in dates.tolist()[0::tick_distance]],
        rotation=0, minor=False)
    if tight:
        ax.set_xlim(0, int(len(dates)))
    return ax


def divide_bus_columns(bus_label, columns):
    r"""
    Divide columns into input columns and output columns. This is function
    depends on the API of the oemof outputlib. Last changes (v0.2.0).

    Parameters
    ----------
    bus_label : str
        Label of the bus.
    columns

    Returns
    -------

    """
    return {
        'in_cols': [
            c for c in columns if (len(c[0]) > 1 and c[0][1] == bus_label)],
        'out_cols': [
            c for c in columns if (len(c[0]) > 1 and c[0][0] == bus_label)]}


def add_last_index(x_axis, number_of_rows):
    """Method
    This method adds another x axis label to the array. If the input is a datetime, it adds the correct next datetime.
    If it's a integer, it adds one.
    :param x_axis:
    :param number_of_rows:
    :return:
    """
    if isinstance(x_axis[0],np.datetime64):
        # Calculate time granularity of the x axis ...
        timedelta = np.datetime64(x_axis[1]) - np.datetime64(x_axis[0])
        # ... and add one more label to the labels so that the last one is not cut out (because of the "post" step)
        x_axis = np.append(x_axis, x_axis[len(x_axis) - 1] + timedelta)
    elif isinstance(x_axis[0],pd.datetime):
        x_axis = pd.to_datetime(x_axis)
        # Calculate time granularity of the x axis ...
        timedelta = x_axis[len(x_axis)-1] - x_axis[0]
        # ... and add one more label to the labels so that the last one is not cut out (because of the "post" step)
        x_axis = x_axis.append(x_axis[1:2]+timedelta)
    else:
        x_axis = np.append(x_axis, number_of_rows + 1)
    return x_axis


def stacked_bar(df, df_in, df_out, ax, bus_label):
    r""" Plotting a combined bar and line plot of a bus to see the fitting of
        in- and out-coming flows of the bus balance.
        One can pass the label of the bus and a DataFrame with all flows. The
        label is used to separate in- and out-flows.
        Parameters
        ----------
        df : pandas.DataFrame
            DateFrame to plot. Output from
            oemof.outputlib.views.node(results, bus_label)['sequences']. If df is
            defined df_in and df_out will be ignored.
        df_in : pandas.DataFrame
            Table with input flows. You can pass df_in and df_out instead of the
            full table and the label.
        df_out : pandas.DataFrame
            Table with output flows. You can pass df_in and df_out instead of the
            full table and the label.
        ax : matplotlib.axes.Axes
            An axes object of matplotlib
        bus_label : str
            Label of the bus you want to plot.
        Returns
        -------
        Plot with stacked bars for out flows - stacked lines for in flows
        """
    plt_definitions = []
    plt_definitions_in = []

    np_array = np.array(df_in.T)
    number_of_rows = np.size(np_array, 1)
    n_columns = np.size(np_array, 0)
    np_array = np.append(np_array, np_array[0:n_columns, number_of_rows - 1:number_of_rows], axis=1)

    np_array_in = np.array(df_out.T)
    number_of_rows_in = np.size(np_array_in, 1)
    n_columns_in = np.size(np_array_in, 0)
    np_array_in = np.append(np_array_in, np_array_in[0:n_columns_in, number_of_rows_in - 1:number_of_rows_in], axis=1)

    if df is not None:
        x_axis = add_last_index(df.index.tolist(), number_of_rows)
    else:
        x_axis = add_last_index(df_in.index.tolist(), number_of_rows)

    bottom = np.zeros(number_of_rows+1)
    bottom_in = np.zeros(number_of_rows_in + 1)
    top = np_array[0]
    top_in = np_array_in[0]

    for i, row_data in enumerate(np_array):  # in range(n_columns):
        top = np.sum([bottom, np_array[i]], axis=0)
        plt_definitions.append(plt.fill_between(x_axis, top, y2=bottom, step='post'))
        bottom += np_array[i]

    linestyle = ['-','--',':']
    for i, row_data in enumerate(np_array_in):  # in range(n_columns):
        top_in = np.sum([bottom_in, np_array_in[i]], axis=0)
        plt_definitions_in.append(plt.plot(x_axis, top_in, color='k', linewidth=1.5, label=[i], linestyle=linestyle[i], drawstyle='steps-post'))
        bottom_in += np_array_in[i]

    df_out = df_out.reset_index(drop=True)

    plt.xlim(left=min(x_axis), right=max(x_axis))
    ax.set_ylabel(bus_label)

    return


def io_plot(bus_label=None, df=None, df_in=None, df_out=None, ax=None,
            cdict=None, line_kwa=None, bar_kwa=None, area_kwa=None,
            inorder=None, outorder=None, smooth=False):
    r""" Plotting a combined bar and line plot of a bus to see the fitting of
    in- and out-coming flows of the bus balance.

    One can either pass the label of the bus and a DataFrame with all flows or
    two DataFrames (one with the in-flows and one with the out-flows). The
    label is used to separate in- and out-flows if only one DataFrame is
    passed.

    Parameters
    ----------
    bus_label : str
        Label of the bus you want to plot.
    df : pandas.DataFrame
        DateFrame to plot. Output from
        oemof.outputlib.views.node(results, bus_label)['sequences']. If df is
        defined df_in and df_out will be ignored.
    df_in : pandas.DataFrame
        Table with input flows. You can pass df_in and df_out instead of the
        full table and the label.
    df_out : pandas.DataFrame
        Table with output flows. You can pass df_in and df_out instead of the
        full table and the label.
    ax : matplotlib.axes.Axes
        An axes object of matplotlib
    cdict : dictionary
        A dictionary that has all possible components as keys and its
        colors as items.
    line_kwa : dictionary
        Keyword arguments to be passed to the pandas line plot.
    bar_kwa : dictionary
        Keyword arguments to be passed to the pandas bar plot.
    area_kwa : dictionary
        Keyword arguments to be passed to the pandas area plot.
    inorder : list
        Order of columns to plot the line plot
    outorder : list
        Order of columns to plot the bar plot
    smooth : bool
        If smooth is True a line plot without stairs and an area plot instead
        of a bar plot is used. A smooth plot is faster but mathematical
        incorrect. So it is recommended to use it for a high number of time
        steps or for a quick draft plot.

    Note
    ----
    Further keyword arguments will be passed to the
    :class:`slice_unstacked method <DataFramePlot.slice_unstacked>`.

    Returns
    -------
    handles, labels
        Manipulated labels to correct the unusual construction of the
        stack line plot. You can use them for further manipulations.
    """
    if bar_kwa is None:
        bar_kwa = {}
    if line_kwa is None:
        line_kwa = {}
    if area_kwa is None:
        area_kwa = {}

    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)

    if df_in is not None:
        df_in = df_in.copy()
    if df_out is not None:
        df_out = df_out.copy()

    if df is not None:
        divided_columns = divide_bus_columns(bus_label, df.columns)
        in_cols = divided_columns['in_cols']
        out_cols = divided_columns['out_cols']
        df_in = df[in_cols].copy()
        df_out = df[out_cols].copy()

    # Create a bar (or area) plot for all input flows
    if inorder is not None:
        df_in = rearrange_df(df_in, inorder)
    else:
        df_in.sort_index(axis=1, ascending=True, inplace=True)

    df_in = df_in.reset_index(drop=True)

    if cdict is not None:
        colors = color_from_dict(cdict, df_in)
    else:
        colors = None

    if smooth:
        df_in.plot(kind='area', linewidth=0, stacked=True,
                   ax=ax, color=colors, **area_kwa)
    else:
        df_in.plot(kind='bar', linewidth=0, stacked=True, width=1,
                   ax=ax, color=colors, **bar_kwa)

    # Create a line plot for all output flows
    if outorder is not None:
        df_out = rearrange_df(df_out, outorder)
    else:
        df_out.sort_index(axis=1, ascending=True, inplace=True)

    df_out = df_out.reset_index(drop=True)

    # The following changes are made to have the bottom line on top layer
    # of all lines. Normally the bottom line is the first line that is
    # plotted and will be on the lowest layer. This is difficult to read.
    new_df = pd.DataFrame(index=df_out.index)
    tmp = 0
    for col in df_out.columns:
        new_df[col] = df_out[col] + tmp
        tmp = new_df[col]
    if outorder is None:
        new_df.sort_index(axis=1, ascending=False, inplace=True)
    else:
        lineorder = list(outorder)
        lineorder.reverse()
        new_df = new_df[lineorder]

    if cdict is not None:
        colorlist = color_from_dict(cdict, df_out)
    else:
        colorlist = None

    if isinstance(colorlist, list):
        colorlist.reverse()

    separator = len(new_df.columns)

    if smooth:
        new_df.plot(kind='line', ax=ax, color=colorlist, **line_kwa)
    else:
        new_df.plot(kind='line', ax=ax, color=colorlist,
                    drawstyle='steps-mid', **line_kwa)

    # Adapt the legend to the new order
    handles, labels = ax.get_legend_handles_labels()
    tmp_lab = [x for x in reversed(labels[0:separator])]
    tmp_hand = [x for x in reversed(handles[0:separator])]
    handles = tmp_hand + handles[separator:]
    labels = tmp_lab + labels[separator:]
    labels.reverse()
    handles.reverse()

    ax.legend(handles, labels)

    return {
        'handles': handles,
        'labels': labels,
        'ax': ax}


def io_stack_plot(df=None, ax=None, inorder=None, outorder=None, slider=None,
                  width=None, title_label=None, x_axis_label=None, legend_label=None):
    n_plots = len(df)

    fig = plt.figure(figsize=(18, 9))
    fig.subplots_adjust(bottom=0.20)  # kleiner = näher am slider

    i = 1
    for bus_label, bus_df in df.items():
        # Add number of subplots
        if i == 1:
            ax = fig.add_subplot(n_plots, 1, i)
        else:
            ax = fig.add_subplot(n_plots, 1, i, sharex=ax)

        # Divide Input DF into bus flows (in and out)
        divided_columns = divide_bus_columns(bus_label, bus_df.columns)
        in_cols = divided_columns['in_cols']
        out_cols = divided_columns['out_cols']

        df_in = bus_df[in_cols].copy()

        # rearrange DF order - optional argument
        if inorder is not None and bus_label in inorder:
            df_in = rearrange_df(df_in, inorder[bus_label])
        else:
            df_in.sort_index(axis=1, ascending=True, inplace=True)
            df_in = df_in.reset_index(drop=True)

        df_out = bus_df[out_cols].copy()

        if outorder is not None and bus_label in outorder:
            df_out = rearrange_df(df_out, outorder)
        else:
            df_out.sort_index(axis=1, ascending=True, inplace=True)
            df_out = df_out.reset_index(drop=True)

        # create stacked bar + stacked line plot
        stacked_bar(bus_df, df_in, df_out, ax, bus_label)

        # add legend (use optional order if given (legend_label)
        if legend_label is not None and bus_label in legend_label:
            print(legend_label[bus_label])
            plt.legend(legend_label[bus_label], loc='upper right')
        else:
            df_out_in = df_out.columns.tolist() + df_in.columns.tolist()
            plt.legend(df_out_in, loc='upper right')

        # add x axis label (if given use optional values)
        if x_axis_label:
            plt.ylabel(x_axis_label[i - 1])
        else:
            plt.ylabel('Power in [kW]')

        # add graph label (if given use optional values)
        if title_label:
            plt.title(title_label[i - 1])
        else:
            plt.title(bus_label)

        # preparation plot axis function (min - max values for both axes)
        np_array = np.array(df_in.T)
        number_of_rows = np.size(np_array, 1)
        x_axis = add_last_index(bus_df.index.tolist(), number_of_rows)

        xmin = min(x_axis)
        xmax = max(x_axis)
        ymin = 0
        ymax = max([np.sum(a) for a in df_in.values]) * 1.2
        plt.axis([xmin, xmax, ymin, ymax])

        # add +1 for next bus label loop
        i += 1

    # add slider (optional argument
    if slider:
        barpos = plt.axes([0.125, 0.1, 0.775, 0.03])  # start - oben/unten - ende - dicke
        slider = Slider(barpos, 'Date', 0, 1, valinit=0)

        # add optional width if given - otherwise its used for 168 values (1 week = hourly resoultion)
        if width:
            width = width
        else:
            width = 168

        # update function for the seen part of the graph as a function of slider position
        def update(val):
            pos = slider.val
            pos = xmin + pos * (xmax - xmin - timedelta(hours=width))
            ax.axis([pos, pos + timedelta(hours=width), ymin, ymax])

        slider.on_changed(update)
