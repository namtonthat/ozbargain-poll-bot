"""
A bot that scrapes Ozbargain polls and generates a webchart for them - stored in Github every day.
"""

from bs4 import BeautifulSoup
import requests
import pandas as pd
from math import pi
import markdown2
from datetime import datetime
import json
from dataclasses import dataclass
from typing import List

from bokeh.io import save, output_file
from bokeh.plotting import figure, curdoc
from bokeh.palettes import TolRainbow, Sunset
from bokeh.transform import cumsum

import logging

logging.basicConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


@dataclass
class OzbargainPoll:
    "Class to hold data for Ozbargain Poll"
    date_published: str
    node_id: int
    title: str
    options: List[str]
    votes: List[int]

    def __post_init__(self):
        "Remove | from title"
        title = self.title.replace("|", "")
        self.title = title

    @property
    def create_markdown_text(self) -> str:
        "Generate md string from poll data"
        text = (
            f"| {self.date_published} |"
            + f"<a href='{PREFIX_URL}{self.node_id}' title='Ozbargain'><b>{self.title}</b></a> |"
            + f"<a href='{self.node_id}.html' title='Rendered Pie Chart'>Poll</a> |"
        )
        return text


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
    no_options = len(x)

    if no_options > 2:
        data["color"] = TolRainbow[no_options]
    elif (no_options > 0) and (no_options <= 2):
        data["color"] = Sunset[3][:no_options]

    # checks whether an options exists and set theme
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
        poll_stats = json.loads(
            soup.find("script", {"type": "application/ld+json"}).text
        )
        date_published = poll_stats.get("datePublished")[:10]
        votes = [int(vote.get_text()) for vote in span_vote]
        title = soup.find("title").text.split(" - ")[0]
        max_options = list(TolRainbow.keys())[-1]

        if options and (len(options) <= max_options):
            create_bokeh_plot(options, votes, title, id)
            ozb_poll = OzbargainPoll(
                date_published=date_published,
                node_id=id,
                title=title,
                options=options,
                votes=votes,
            )
            return ozb_poll
        elif len(options) > max_options:
            LOGGER.info("Too many options, skipping %s", id)

    except (AttributeError, ValueError) as e:
        LOGGER.info("No data found for %s", id)
        return


def create_html_page(polls: List[OzbargainPoll]) -> None:
    """Create navigation webpage for all available Ozbargain Polls within the last day"""
    header_text = [
        '<link rel="stylesheet" href="https://assets.ubuntu.com/v1/vanilla-framework-version-3.8.2.min.css"/>',
        "<header>",
        "<hr>",
        '<div class="p-navigation__row">',
        "<h2>Ozbargain Active Polls</h2>",
        "</div>",
        "<div class='row'>",
        "<p>Last updated: {}</p>".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "</div>",
        '<hr class="is-fixed-width">',
        "</header>",
    ]

    body_texts = [
        "| Date Published | Title | Statistics |",
        "| ----- | ----- | ----- | ",
    ]
    for poll in polls:
        markdown_text = poll.create_markdown_text
        body_texts.append(markdown_text)

    body_texts = "\n".join(body_texts)

    converter = markdown2.Markdown(extras=["tables"])
    html_body = converter.convert(body_texts)
    body_styling_prefix = [
        "<body>",
        "<div class='row'>",
        "<main class='col-12'>",
    ]
    body_styling_suffix = ["</main>", "</div>", "</body>"]

    html_body = (
        "\n".join(body_styling_prefix) + html_body + "\n".join(body_styling_suffix)
    )
    html_header = "\n".join(header_text)

    index_path = f"{OUTPUT_PATH}index.html"
    html_page = html_header + html_body
    with open(f"{index_path}", "w+") as f:
        f.write(html_page)

    return


if __name__ == "__main__":
    # global variables
    PREFIX_URL = "https://www.ozbargain.com.au/node/"
    OUTPUT_PATH = "docs/"

    # find active polls
    active_polls = find_all_active_polls()

    pie_charts = []
    for poll_id in active_polls:
        pie_chart = generate_poll_webchart(poll_id)
        pie_charts.append(pie_chart)

    valid_pie_charts = [x for x in pie_charts if x is not None]

    create_html_page(valid_pie_charts)
