# For basic Site class
from stackoversight.scraping.site import Site
# For site tags and sorts
from enum import Enum
# Use regex to filter links
import re
# For proxy exception
import requests
# For soup processing
from bs4 import BeautifulSoup
# Need that mutable tuple my dude
from recordclass.mutabletuple import mutabletuple


class StackOverflow(Site):
    # Stack Overflow limits each client id to 10000 requests per day, the timeout parameter is in seconds
    limit = None
    timeout_sec = 86400

    def __init__(self, client_keys: list):
        sessions = [self.init_key(key) for key in client_keys]

        super(StackOverflow, self).__init__(sessions, self.timeout_sec, self.limit)

    class Sorts(Enum):
        frequency = 'MostFrequent'
        bounty = 'BountyEndingSoon'
        vote = 'MostVotes'
        recent = 'RecentActivity'
        newest = 'Newest'

    class Filters(Enum):
        unanswered = 'NoAnswers'
        unaccepted = 'NoAcceptedAnswer'
        bounty = 'Bounty'

    class Tabs(Enum):
        newest = 'Newest'
        active = 'Active'
        bounty = 'Bounties'
        unanswered = 'Unanswered'
        frequent = 'Frequent'
        vote = 'Votes'

    class Tags(Enum):
        python = 'python'
        python2 = 'python-2.7'
        python3 = 'python-3.x'

    class Categories(Enum):
        question = 'questions'

    """
        tags needs to be a list!
    """
    @staticmethod
    def create_parent_link(category: Enum, tags=None, tab=None, sort=None, filter=None):
        url = 'https://stackoverflow.com/'

        if category:
            url += category.value

        if tags:
            url += '/tagged/'

            for tag in tags:
                url += tag.value + '%20'

        if url.endswith('%20'):
            url = url[:-3]

        if tab:
            url += '/?tab=' + tab.value
        elif sort:
            url += '/?sort=' + sort.value

        if filter:
            url += '&filters=' + filter.value

        if tab or sort or filter:
            url += '&edited=true'

        return url

    def get_child_links(self, parent_link: str, pause=False, pause_time=None):
        soup = self.get_soup(parent_link, pause, pause_time)

        # search the parse tree for all with the <a> tag, which is for a hyperlink and use the href tag to get the
        # url from them
        links = [link.get('href') for link in soup.find_all('a')]

        # handle possible error
        if not links:
            print("The proxy is up but it is failing to pull from the site.")
            raise requests.exceptions.ProxyError

        # filter to make sure only processing non empty links with question followed by a number and drop duplicates
        links = list(set(filter(re.compile('/questions/[0-9]').search, [link for link in links if link])))

        # insert preceding url section if needed
        precede = parent_link.split('/questions/')[0]
        links = [precede + link if link.startswith('/') else link for link in links]

        # filter out those that are not on the same site as the parent url
        return [link for link in links if link.startswith(precede)]

    def handle_request(self, url: str, session: str):
        return requests.get(url + '&key=' + session)

    @staticmethod
    def get_text(soup: BeautifulSoup):
        try:
            return [element.get_text() for element in soup.find_all(attrs={'class': 'post-text'})]
        except:
            # can fail when none are found
            return []

    @staticmethod
    def get_code(soup: BeautifulSoup):
        try:
            return [element.get_text() for element in soup.find_all('code')]
        except:
            # can fail when none are found
            return []

    @staticmethod
    def get_category(url: str):
        return url.split('https://')[1].split('.')[0]

    @staticmethod
    def get_id(self, url: str):
        return url.split('/')[4]

    def init_key(self, key: str):
        response = requests.get('https://api.stackexchange.com/2.2/info?site=stackoverflow' + '&key=' + key)
        response = response.json()

        if not self.limit:
            self.limit = response['quota_max']

        return mutabletuple(self.limit - response['quota_remaining'], key)
