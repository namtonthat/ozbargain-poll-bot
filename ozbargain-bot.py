"""
A bot that scrapes Ozbargain polls and generates a webchart for them - stored in Github every day.
"""

from bs4 import BeautifulSoup
import requests
import os

from bokeh.io import show, export_png
from bokeh.plotting import figure
from datetime import datetime


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
    all_polls =soup.find_all("td", {'class': "topic"})

    poll_ids = []
    LOGGER.info('Sourcing active polls')
    for poll in all_polls:
        is_expired = poll.find("span", class_="marker expired")
        if not is_expired:
            url_poll_id = poll.select('a')[0].get('href')
            poll_id = url_poll_id.split('/')[-1]
            poll_ids.append(poll_id)

    return poll_ids

def generate_poll_webchart(id):
    "Generates a webchart for a given poll"
    prefix_url = "https://www.ozbargain.com.au/node/"
    url = prefix_url + str(id)
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    poll = soup.find(id="poll")
    # scraping data
    span_vote = poll.find_all("span", class_="nvb voteup")
    span_options = poll.find_all("span", class_="polltext")
    options = [option.get_text() for option in span_options]
    votes = [vote.get_text() for vote in span_vote]
    title = soup.find("title").text.split(" - ")[0]

    # create figure
    p = figure(x_range=options, height=250, title=title,
           toolbar_location=None, tools="")

    p.vbar(x=options, top=votes, width=1.5)

    # customisation
    p.xgrid.grid_line_color = None
    p.xaxis.axis_label = "Options"
    p.yaxis.axis_label = "Votes"
    p.y_range.start = 0

    output_path = f"outputs/"
    if not os.path.exists(output_path):
      os.makedirs(output_path)

    LOGGER.info('Generating webchart for poll: %s', id)
    export_png(p, filename=f"{output_path}/{poll_id}.png")
    return

if __name__ == "__main__":
    active_polls = find_all_active_polls()

    for poll_id in active_polls:
        generate_poll_webchart(poll_id)