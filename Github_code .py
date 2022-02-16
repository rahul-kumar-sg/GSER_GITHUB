import pandas as pd
import requests
import time
import os
from urllib.parse import urlparse
from datetime import datetime as dt, datetime
from lxml import html
import numpy as np
import random
from pandas.io.json import json_normalize
import json
from sqlalchemy import create_engine
from ttictoc import tic,toc
import logging

def check_throttle(response):
    if response.headers['X-RateLimit-Remaining'] <= str(1):
        t = response.headers['X-RateLimit-Reset']
        unix_val = datetime.fromtimestamp(int(t))
        diff = (unix_val - datetime.now())
        diff = diff.total_seconds()
        logger.info('Sleeping for ' + str(diff) + ' seconds while waiting for rate limit reset...')
        time.sleep(int(diff))


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(lineno)d:%(name)s:%(message)s')

file_handler = logging.FileHandler('logger_github.log')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

cities_github_df = pd.read_excel('GSER22_github.xlsx')

timestamp = dt.now()

min_followers = [0,10]
cities_github_df = cities_github_df.drop_duplicates()

# print("Shape:{}".format(cities_github_df.shape))

count = 0

for ecosyst in cities_github_df.Ecosystem.unique():
    cities_in_ecosyst_df = cities_github_df[cities_github_df.Ecosystem == ecosyst]

    city_name = []
    developers = []
    developers0 = []
    developers10 = []
    ecosystem = []

    total_cities = len(cities_in_ecosyst_df.GoogleCity)
    logger.info("Ecosystem:{}, Total Cities Parsed:{}".format(ecosyst, total_cities))

    for city, ecosys, country in zip(cities_in_ecosyst_df.GoogleCity, cities_in_ecosyst_df.Ecosystem,
                                     cities_in_ecosyst_df.GoogleCountry):
        location_city_country = city.lower() + ',' + country.lower()
        for i in min_followers:
            api = "https://api.github.com/search/users?q=location%3A%22{}%22+followers%3A%3E{}&type=Users" \
                .format(location_city_country.lower().replace(" ", "%20"), i-1)
            try:
                tic()
                response = requests.get(api)
                elapsed = toc()
                logger.info(f"time taken for {api} {elapsed}")
                check_throttle(response)

            except:
                tic()
                response = requests.get(api)
                no_data_elapsed = toc()
                check_throttle(response)
                if len(json.loads(response.text)) == 0:
                    logger.info(f"no data returned from {api} {no_data_elapsed}")

            sec = random.randint(5,20)
            t = time.sleep(sec)

            js = json.loads(response.text)
            dev_counts = list(js.items())
            dev_counts = dev_counts[0][-1]

            developers.append(dev_counts)

            count = count + 1
            logger.info(f"{count}. Min_Followes {i}, City: {city}, Accounts: {dev_counts}, Sleep_Time: {sec} seconds")

        city_name.append(city)
        ecosystem.append(ecosys)

        developers0.append(developers[-6])
        developers10.append(developers[-5])

    df = pd.DataFrame(list(zip(ecosystem, city_name, developers0, developers10)), columns=["Ecosystem", "city", "all_developers", "top_dev_10"])

    df = df.astype(str)
    df["timestamp"] = timestamp
    engine = create_engine("mysql+pymysql://{user}:{pw}@database-1.cluster-ro-ct2brvwy8za8.us-east-1.rds.amazonaws.com/{db}"
                           .format(user="admin", pw="d5Sj5U7lZqwNYsqRjhJI", db="datacollection"))
    conn = engine.connect()
    conn.execute("CREATE TABLE IF NOT EXISTS GSER_github (Ecosystem varchar(50),\
                   city varchar(100), all_developers MEDIUMTEXT, top_dev_10 MEDIUMTEXT, timestamp timestamp);")
    df.to_sql('GSER_github', con=engine, if_exists='append', chunksize=1000, index=False)
    conn.close()


