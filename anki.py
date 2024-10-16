import genanki
import os

from bs4 import BeautifulSoup
from pathlib import Path

with open('./pages/style.css', 'r', encoding='utf-8') as file:
    style = file.read()

with open("index.html", 'r', encoding='utf-8') as file:
    content = file.read()
    soup = BeautifulSoup(content, 'html.parser')

    if soup.find(['html', 'body']):
        script_tags = soup.find_all('script')
        scripts_content = "\n".join(str(tag) for tag in script_tags)


anki_quran_model = genanki.Model(
    1871019098,
    'Quran Pages',
    fields=[
        {'name': 'Page_num'},
        {'name': 'Html'},
    ],
    templates=[
        {
            'name': 'Card 1',
            'qfmt': '{{Html}}'+scripts_content,
            'afmt': '{{FrontSide}}',
        },
    ],
    css="\n"+style

)


directory = Path('./pages/')

my_deck = genanki.Deck(
    2059400140,
    'Quran_anki')


class MyNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0], self.fields[1])


for file_path in directory.iterdir():
    if file_path.is_file() and file_path.suffix == '.html':
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            soup = BeautifulSoup(content, 'html.parser')

            if soup.find(['html', 'body']):
                prev_button = soup.find('button', id="prevPage")
                next_button = soup.find('button', id="nextPage")

                if prev_button:
                    prev_button.decompose()
                if next_button:
                    next_button.decompose()

                style_tags = soup.find_all('style')
                style_content = "\n".join(str(tag) for tag in style_tags)

                div_tag = soup.find('body')
                div_content = "\n".join(str(tag) for tag in div_tag)

                file_name = os.path.splitext(os.path.basename(file_path))[0]

                my_note = MyNote(
                    model=anki_quran_model,
                    fields=[f"{int(file_name):03}", f'{style_content} {div_content}'],
                )
                my_deck.add_note(my_note)


genanki.Package(my_deck).write_to_file('output.apkg')