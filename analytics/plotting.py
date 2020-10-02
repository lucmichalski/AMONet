import logging
import math
import os
import geopandas as gpd
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from typing import List
from decouple import config
from shapely.geometry import Point


def base_plotter(
    data_x: list,
    data_y: list,
    x_label: str,
    y_label: str,
    filename: str,
    title: str = "",
    bar: bool = False,
    horizontal: bool = False,
    hist: bool = False,
    pie: bool = True,
    temporal: bool = False,
    rotate_ticks: bool = False,
    log_scale: bool = False,
    legend: List[str] = [],
    param_plot: dict = {},
    param_ax: dict = {},
):
    """
    A helper function to make a basic plot.

    Parameters
    ----------
    data_x and data_y : array/list
        Data to plot

    x_label, y_label: str
        Labels of axes

    filename : str
        Name of file to save plot

    title : str
        Title of plot

    bar : bool
        Bar plot?

    horizontal : bool
        Horizontal bar plot?

    hist : bool
        Histogram plot?

    pie : bool
        Pie chart?

    temporal : bool
        Temporal data with data_x being datetimes?

    rotate_ticks : bool
        Rotate ticks of x-axis?

    log_scale : bool
        Logarithmic scaling for axes?

    legend : list
        List including text(s) of legend that should be added to plot(s)

    param_ax : dict
       Dictionary of kwargs to pass to ax.plot
       see: https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.axes.Axes.plot.html#matplotlib.axes.Axes.plot

    param_plot : dict
       Dictionary of kwargs to pass to plt.subplots
       see: https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.pyplot.subplots.html#matplotlib.pyplot.subplots
    """

    # layout
    plt.style.use("seaborn-white")
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = "Ubuntu"
    plt.rcParams["font.monospace"] = "Ubuntu Mono"
    plt.rcParams["font.size"] = 14
    plt.rcParams["axes.labelsize"] = 14
    plt.rcParams["axes.labelweight"] = "bold"
    plt.rcParams["axes.titlesize"] = 14
    plt.rcParams["xtick.labelsize"] = 12
    plt.rcParams["ytick.labelsize"] = 12
    plt.rcParams["legend.fontsize"] = 14
    plt.rcParams["figure.titlesize"] = 16
    plt.rcParams["axes.grid"] = True

    # create figure/axes
    fig, ax = plt.subplots(1, 1, **param_plot)

    # rotate ticks
    if rotate_ticks:
        ax.tick_params(axis="x", rotation=90)

    # actual plot
    if bar and not horizontal:
        ax.bar(data_x, data_y, **param_ax)
    elif bar and horizontal:
        ax.barh(data_y, data_x, **param_ax)
        ax.invert_yaxis()  # labels read top-to-bottom
    elif hist:
        ax.hist(data_x, density=True, **param_ax)
    elif pie:
        wedges, texts, autotexts = ax.pie(data_x, **param_ax, autopct="%1.1f%%", startangle=90, pctdistance=0.8)
        ax.axis("equal")
        # pie chart specific legend
        if legend:
            ax.legend(wedges, legend, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    else:
        ax.plot(data_x, data_y, **param_ax)

    # log scale
    if log_scale:
        ax.set_xscale("log")
        ax.set_yscale("log")

    # labels for temporal data
    if temporal:
        locator = mdates.AutoDateLocator()
        formatter = mdates.ConciseDateFormatter(locator)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)

    # add legend
    if legend and not pie:
        ax.legend(legend)

    # set labels
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)

    # add title
    if title:
        ax.set_title(title, loc="center", pad=10)

    # save
    plt.savefig(os.path.join(config("DATA_DIR"), "analytics/" + filename), dpi=300, bbox_inches="tight")

    # cleaning figure
    plt.clf()


def table_plotter(data: list, filename: str, title: str, param_plot: dict = {}, param_ax: dict = {}):
    """
    A helper function to make a plot of a table.

    Parameters
    ----------
    data : list (of lists)
       Data to plot

    filename : str
        Name of file to save plot

    title : str
        Title of plot

    param_ax : dict
       Dictionary of kwargs to pass to ax.plot
       see: https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.axes.Axes.plot.html#matplotlib.axes.Axes.plot

    param_plot : dict
       Dictionary of kwargs to pass to plt.subplots
       see: https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.pyplot.subplots.html#matplotlib.pyplot.subplots
    """

    # create figure/axes
    fig, ax = plt.subplots(1, 1, **param_plot)

    # actual plot
    table = ax.table(cellText=data, **param_ax)

    # table specific layout
    ax.axis("off")
    table.auto_set_font_size(False)
    table.set_fontsize(12)

    # adjust cell height and width
    cellDict = table.get_celld()
    for i in range(0, len(data[0])):
        cellDict[(0, i)].set_height(0.075)  # header
        for j in range(1, len(data) + 1):
            cellDict[(j, i)].set_height(0.05)  # normal rows

    # add title
    ax.set_title(title, fontsize=16, loc="center", pad=10)

    # save
    plt.savefig(os.path.join(config("DATA_DIR"), "analytics/" + filename), dpi=300, bbox_inches="tight")

    # cleaning figure
    plt.clf()


def draw_world_map(latitude: List[float], longitude: List[float]):
    """ Draw world map showing the given geo locations. """

    # prepare data
    df = pd.DataFrame({"latitude": latitude, "longitude": longitude})
    df["geometry"] = [Point(xy) for xy in zip(df.longitude, df.latitude)]
    df.drop(["latitude", "longitude"], axis=1, inplace=True)
    gdf = gpd.GeoDataFrame(df, crs="EPSG:4326")  # convert to geopandas dataframe

    # plot
    fig, ax = plt.subplots()

    world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
    world_plot = world.plot(color="grey", ax=ax, alpha=0.4)
    gdf.plot(ax=world_plot, marker="o", color="red", markersize=5, alpha=0.2)

    # layout
    ax.axis("off")

    # save
    plt.savefig(os.path.join(config("DATA_DIR"), "analytics/world_map.png"), dpi=300, bbox_inches="tight")

    # cleaning figure
    plt.clf()
