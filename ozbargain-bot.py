"""
A bot that scrapes Ozbargain polls and generates a webchart for them - stored in Github every day.
"""

from bs4 import BeautifulSoup
import requests
import pandas as pd
from math import pi
import os
import markdown2

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
    "Generates a pie chart for a given poll"
    prefix_url = "https://www.ozbargain.com.au/node/"
    url = prefix_url + str(id)
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    poll = soup.find(id="poll")
    LOGGER.info('Parsing data for %s', id)
    # scraping data
    try:
            span_vote = poll.find_all("span", class_="nvb voteup")
            span_options = poll.find_all("span", class_="polltext")
            options = [option.get_text() for option in span_options]
            votes = [int(vote.get_text()) for vote in span_vote]
            title = soup.find("title").text.split(" - ")[0]
    except AttributeError:
            LOGGER.info('No data found for %s', id)
            return

    if options:
            LOGGER.info('Data found for %s', id)
            x = dict(zip(options, votes))
            data = pd.Series(x).reset_index(name='value').rename(columns={'index': 'options'})
            data['angle'] = data['value']/data['value'].sum() * 2*pi
            if len(x) > 2:
                    data['color'] = TolRainbow[len(x)]
            elif (len(x) > 0) and (len(x) <=2):
                    data['color'] = Sunset[3][:len(x)]

            # checks whether an options exists
            # set theme
            curdoc().theme='light_minimal'

            # create figure
            p = figure(width=1000, height=1000, title=f"{title}",
                    tooltips="@options: @value", x_range=(-0.5, 1.0))


            p.wedge(x=0, y=1, radius=0.4,
                    start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
                    line_color="white", fill_color='color', legend_field='options', source=data)

            p.axis.axis_label = None
            p.axis.visible = False
            p.grid.grid_line_color = None



            LOGGER.info('Generating webchart for poll: %s', id)
            # setting output
            output_file(filename=f"{OUTPUT_PATH}/{id}.html", title=title)

            save(p)
            return id

def create_html_page(array):
    """ Render HTML index page for navigation """
    markdown_text = ""
    for value in array:
        markdown_text+=f"* <a href='{value}.html'>{value}</a>\n"

    html_page = markdown2.markdown(markdown_text)
    index_path = f"{OUTPUT_PATH}/index.html"

    with open(f'{index_path}', 'w+') as f:
        f.write(html_page)

    return

if __name__ == "__main__":
    OUTPUT_PATH = f"dist/"
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)

    active_polls = find_all_active_polls()

    pie_chart_ids = []
    for poll_id in active_polls:
        pie_chart_id = generate_poll_webchart(poll_id)
        if pie_chart_id:
            pie_chart_ids.append(pie_chart_id)
