"""
A bot that scrapes Ozbargain polls and generates a webchart for them - stored in Github every day.
"""

from bs4 import BeautifulSoup
import requests
import pandas as pd
from math import pi
import os
import markdown2
from pathlib import Path

from bokeh.io import show, save, output_file
from bokeh.plotting import figure, curdoc
from bokeh.palettes import TolRainbow, Sunset
from bokeh.transform import cumsum

import logging

logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def find_all_active_polls():
    """
    Finds all active polls on Ozbargain
    """
    url = "https://www.ozbargain.com.au/forum/polls"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    all_polls = soup.find_all("td", {"class": "topic"})

    poll_ids = []
    LOGGER.info("Sourcing active polls")
    for poll in all_polls:
        is_expired = poll.find("span", class_="marker expired")
        if not is_expired:
            url_poll_id = poll.select("a")[0].get("href")
            poll_id = url_poll_id.split("/")[-1]
            poll_ids.append(poll_id)

    return poll_ids


def create_bokeh_plot(options, votes, title, id):
    "Generate bokeh pie chart"
    LOGGER.info("Data found for %s", id)
    x = dict(zip(options, votes))
    data = pd.Series(x).reset_index(name="value").rename(columns={"index": "options"})
    data["angle"] = data["value"] / data["value"].sum() * 2 * pi
    if len(x) > 2:
        data["color"] = TolRainbow[len(x)]
    elif (len(x) > 0) and (len(x) <= 2):
        data["color"] = Sunset[3][: len(x)]

    # checks whether an options exists
    # set theme
    curdoc().theme = "light_minimal"

    # create figure
    p = figure(
        width=1000,
        height=1000,
        title=f"{title}",
        tooltips="@options: @value",
        x_range=(-0.5, 1.0),
        name="pie",
    )

    p.wedge(
        x=0,
        y=1,
        radius=0.4,
        start_angle=cumsum("angle", include_zero=True),
        end_angle=cumsum("angle"),
        line_color="white",
        fill_color="color",
        legend_field="options",
        source=data,
    )

    p.axis.axis_label = None
    p.axis.visible = False
    p.grid.grid_line_color = None
    p.title.text_font = "tahoma"

    LOGGER.info("Generating webchart for poll: %s", id)

    # setting output
    output_file(filename=f"{OUTPUT_PATH}/{id}.html", title=title)

    save(p)

    return


def generate_poll_webchart(id):
    "Generates a pie chart for a given poll"
    url = PREFIX_URL + str(id)
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    poll = soup.find(id="poll")
    LOGGER.info("Parsing data for %s", id)
    # scraping data
    try:
        span_vote = poll.find_all("span", class_="nvb voteup")
        span_options = poll.find_all("span", class_="polltext")
        options = [option.get_text() for option in span_options]
        votes = [int(vote.get_text()) for vote in span_vote]
        title = soup.find("title").text.split(" - ")[0]
        if options:
            create_bokeh_plot(options, votes, title, id)
            return title, id

    except AttributeError:
        LOGGER.info("No data found for %s", id)
        return


def create_html_page(title_and_id_array):
    """Create navigation webpage for all available Ozbargain Polls within the last day"""
    markdown_text = "## Ozbargain Active Polls (within the last week)\n\n"

    for (title, value) in title_and_id_array:
        markdown_text += f"* <a href='{PREFIX_URL}/{value}' title='Ozbargain Poll'>({value})</a> <a href='{value}.html' title='Rendered Pie Chart'>{title}</a>\n"

    html_page = markdown2.markdown(markdown_text)
    index_path = f"{OUTPUT_PATH}/index.html"

    with open(f"{index_path}", "w+") as f:
        f.write(html_page)

    return


if __name__ == "__main__":
    # global variables
    PREFIX_URL = "https://www.ozbargain.com.au/node/"
    OUTPUT_PATH = "docs/"

    # empty path if it exists
    Path.rmdir(OUTPUT_PATH)

    # create paths
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)

    # find active polls
    active_polls = find_all_active_polls()

    pie_charts = []
    for poll_id in active_polls:
        pie_chart = generate_poll_webchart(poll_id)
        pie_charts.append(pie_chart)

    create_html_page(pie_charts)
