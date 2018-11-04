import scrapy
from scrapy.spiders.init import InitSpider
from scrapy.http import Request
from scrapy.crawler import CrawlerProcess

import matplotlib.pyplot as plt

from string import capwords
import re
import logging


characters = {}
failed = False

# All scripts are scraped from The Internet Movie Script Database
class ScriptSpider(InitSpider):
    name = 'scriptSpider'
    allowed_domains = ['imsdb.com/scripts']

    def __init__(self, movie='', script_url='', **kwargs):
        self.original_title = movie
        if movie:
            self.movie = self.process_title(movie)
            self.script_url = 'https://www.imsdb.com/scripts/%s.html' % self.movie
        if script_url:
            self.script_url = script_url
        super().__init__(**kwargs)

    def process_title(self, movie):
        # Capitalize title
        movie = capwords(movie)
        # Move 'The' to end of string
        # e.g. The Dark Knight Rises -> Dark Knight Rises, The
        if movie.startswith('The '):
            movie = movie.replace('The ', '') + ', The'
        # Replace all spaces with hyphens
        return movie.replace(' ', '-')

    def init_request(self):
        yield Request(url=self.script_url, callback=self.parse_script)

    def parse_script(self, response):
        global characters
        global failed
        script = response.xpath('//pre')
        body = script.xpath('.//b/text()')
        if not body:
            print('ERROR: Script not found')
            print('Please visit imsdb.com for a list of available scripts')
            failed = True
        for line in body:
            line_text = line.extract()
            if self.is_character(line_text):
                character = self.process_character(line_text)
                if character:
                    try:
                        characters[character] += 1
                    except KeyError:
                        characters[character] = 1

    def is_character(self, line):
        # Filter scene headings
        if 'INT.' in line or 'EXT.' in line:
            return False
        # Filter transitions
        if ' DISSOLVE ' in line or ' FADE ' in line \
            or ' SMASH ' in line or ' CUT TO' in line or ' TO BLACK' in line:
            return False
        try:
            # Filter lines that end with a full stop
            if line.strip()[-1] == '.':
                return False
            # Filter page numbers and parentheticals
            first_char = ''.join(w for w in line.split())[0]
            if first_char.isdigit() or first_char == '(':
                return False
        except IndexError:
            return False
        # Symbols
        if '?' in line or '!' in line or ':' in line:
            return False
        # Misc
        if 'THE END' in line or 'OMITTED' in line or ' OMIT ' in line:
            return False
        return True

    def process_character(self, character):
        # Remove parentheticals (e.g. CONT'D, V.O.)
        character = re.sub(r'\([^)]*\)', '', character)
        # Strip all excess whitespace
        character = character.strip()
        # Remove lines that are too long to be characters
        if len(character) >= 16:
            return ''
        return character


def main():
    movie_name = ''
    movie_url = ''

    if input('Find movie by name instead of url? (y/n):  ') == 'y':
        movie_name = input('Enter movie name in lowercase: ')
    else:
        movie_url = input('Enter url for script hosted on imsdb.com: ')
    print('Finding script...')

    process = CrawlerProcess({
        'LOG_LEVEL': logging.WARNING,
    })
    process.crawl(ScriptSpider, movie=movie_name, script_url=movie_url)
    process.start()

    if failed:
        return

    global characters
    # Remove characters with less than 8 lines
    # This removes noise (bolded lines that aren't characters)
    for key, val in list(characters.items()):
        if val < 8:
            del characters[key]
    # Sort characters by descending dialogue count
    characters_sorted = sorted(characters.items(), key=lambda x: x[1], reverse=True)

    # Create colors for each bar
    col_color = [min(600, x[1]) / 600 for x in characters_sorted]

    cm = plt.cm.get_cmap('viridis')

    patches = plt.bar(range(len(characters_sorted)), [x[1] for x in characters_sorted], align='center')
    for c, p in zip(col_color, patches):
        plt.setp(p, 'facecolor', cm(c))
    plt.xticks(range(len(characters_sorted)), [x[0] for x in characters_sorted], rotation=70)

    fig = plt.gcf()
    fig.canvas.set_window_title(capwords(movie_name))

    plt.show()


if __name__ == '__main__':
    main()
