import sqlite3
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed


DB_LAYOUT_PATH = "./QPC v4 tajweed.sqlite"
DB_WORDS_PATH = "./QPC V4.sqlite"
MAX_THREADS = 20


def get_pages_data(cursor, page_number):
    query = """
    SELECT page_number, line_number, line_type, is_centered, first_word_id, last_word_id, surah_number
    FROM pages
    WHERE page_number = ?
    """
    cursor.execute(query, (page_number,))
    return [dict(zip(['page_number', 'line_number', 'line_type', 'is_centered', 'first_word_id', 'last_word_id', 'surah_number'], row))
            for row in cursor.fetchall()]


def get_line_data(cursor, word_start, word_end):
    query = """
    SELECT word_index, word_key, text
    FROM words
    WHERE word_index BETWEEN ? AND ?
    """
    cursor.execute(query, (word_start, word_end))
    line_data = []
    for row in cursor.fetchall():
        word_index, word_key, text = row
        surah_num, verse_num, word_num = map(int, word_key.split(":"))
        next_word_key = f"{surah_num}:{verse_num}:{word_num + 1}"
        cursor.execute("SELECT word_key FROM words WHERE word_key = ?", (next_word_key,))
        end_verse = int(cursor.fetchone() is None)
        line_data.append({
            "word": word_index,
            "word_key": word_key,
            "text": text,
            "end_verse": end_verse
        })
    return line_data


def add_font_face(soup, output_file, page_number):
    new_style = f"""
    @font-face {{
        font-family: 'v4-tajweed';
        src: url('_p{page_number}.ttf?v=1') format('truetype');
        font-display: swap;
    }}
    """
    style_tag = soup.find("style") or soup.new_tag("style")
    style_tag.append(new_style)
    if not style_tag.parent:
        soup.head.append(style_tag)
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(str(soup))


def create_line_div(soup, line_data, line_number):
    line_class = "line"
    line_div = soup.new_tag("div", **{"class": line_class, "id": f"line-{line_number}"})

    current_ayah_middle = None
    ayah_div = None

    for word in line_data:
        surah_num, verse_num, word_num = word["word_key"].split(':')
        is_last_word = word["end_verse"]

        if verse_num != current_ayah_middle:
            current_ayah_middle = verse_num
            ayah_container = soup.new_tag("div", **{
                "class": "ayah-container",
                "ondblclick": f"handleAyahClick('{surah_num}:{verse_num}')",
                "style": "cursor: pointer;"  
            })
            ayah_div = soup.new_tag("div", **{
                "class": "ayah",
                "data-ayah": f"{surah_num}:{verse_num}"
            })
            ayah_container.append(ayah_div)
            line_div.append(ayah_container)

        char_class = "char char-end" if is_last_word else "char char-word"
        char_span = soup.new_tag("span", **{"class": char_class})
        char_span.string = word["text"] + " "
        ayah_div.append(char_span)

    return line_div


def to_arabic_numerals(number):
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    return ''.join(arabic_digits[int(digit)] for digit in str(number))


def determine_juz_number(page_number):
    return min((page_number - 1) // 20 + 1, 30)


def create_header(surah_number, page_number, juz_number):
    header = BeautifulSoup(features="html.parser").new_tag("header")

    surah_title_div = BeautifulSoup(features="html.parser").new_tag("div", **{"class": "surah-title"})
    surah_name_div = BeautifulSoup(features="html.parser").new_tag("div", **{"class": "surah-name"})

    surah_name_div.append(BeautifulSoup(features="html.parser").new_tag("span", **{"class": "icon-surah icon-surah-surah"}))
    surah_name_div.append(BeautifulSoup(features="html.parser").new_tag(
        "span", **{"class": f"icon-surah icon-surah{surah_number}"}))

    surah_title_div.append(surah_name_div)
    header.append(surah_title_div)

    page_number_div = BeautifulSoup(features="html.parser").new_tag("div")
    page_number_div.string = str(to_arabic_numerals(page_number))
    header.append(page_number_div)

    juz_number_div = BeautifulSoup(features="html.parser").new_tag("div")
    juz_number_div.string = f"ﰸ {to_arabic_numerals(juz_number)}"
    header.append(juz_number_div)

    return header


def add_controls_to_html(page_number):

    controls_div = BeautifulSoup(features="html.parser").new_tag("div")

    controls_inner_div = BeautifulSoup(features="html.parser").new_tag("div", **{"class": "controls"})

    if page_number > 1:
        prev_page_button = BeautifulSoup(features="html.parser").new_tag("button", **{"class": "btn", "id": "prevPage",
                                                                                      "onclick": f"window.location.href='{int(page_number - 1):03}.html'"})
        prev_page_button.string = "Previous Page"
        controls_inner_div.append(prev_page_button)

    next_ayah_button = BeautifulSoup(features="html.parser").new_tag("button", **{"class": "btn", "id": "nextAyah"})
    next_ayah_button.string = "Next V"
    controls_inner_div.append(next_ayah_button)

    next_word_button = BeautifulSoup(features="html.parser").new_tag("button", **{"class": "btn", "id": "nextWord"})
    next_word_button.string = "Next W"
    controls_inner_div.append(next_word_button)

    toggle_all_button = BeautifulSoup(features="html.parser").new_tag("button", **{"class": "btn", "id": "toggleAll"})
    toggle_all_button.string = "Toggle All"
    controls_inner_div.append(toggle_all_button)

    if page_number < 604:
        next_page_button = BeautifulSoup(features="html.parser").new_tag("button", **{"class": "btn", "id": "nextPage",
                                                                                      "onclick": f"window.location.href='{int(page_number + 1):03}.html'"})
        next_page_button.string = "Next Page"
        controls_inner_div.append(next_page_button)

    controls_div.append(controls_inner_div)

    return controls_div


surah_num_t = 0


def modify_html_with_pages(soup, pages_data, cursor_words, page_number):
    global surah_num_t
    page_container = soup.find("div", {
        "class": "page v4-tajweed theme-sepia",
        "data-controller": "tajweed-font",
        "id": "page"
    })

    if pages_data[0]["line_type"] == "surah_name":
        header = create_header(pages_data[0]["surah_number"], page_number, determine_juz_number(page_number))
    else:
        header = create_header(surah_num_t, page_number, determine_juz_number(page_number))

    page_container.insert(0, header)
    for page in pages_data:

        line_container = soup.new_tag("div", **{"class": "line-container", "data-line": str(page["line_number"])})
        line_type = page["line_type"]

        if line_type == "surah_name":
            line_div = create_surah_name_line(soup, page["line_number"], page["surah_number"])
            surah_num_t += 1
        elif line_type == "basmallah":
            line_div = create_bismillah_line(soup, page["line_number"])
        else:
            line_data = get_line_data(cursor_words, page["first_word_id"], page["last_word_id"])
            line_div = create_line_div(soup, line_data, page["line_number"])

        line_container.append(line_div)
        page_container.append(line_container)

    controls_div = add_controls_to_html(page_number)
    page_container.append(controls_div)


def create_surah_name_line(soup, line_number, surah_number):
    line_div = soup.new_tag("div", **{"class": "line line--surah-name", "id": f"line-{line_number}"})
    surah_name_div = soup.new_tag("div", **{"class": "surah-name"})
    surah_name_div.append(soup.new_tag("span", **{"class": "icon-surah icon-surah-surah"}))
    surah_name_div.append(soup.new_tag("span", **{"class": f"icon-surah icon-surah{surah_number}"}))
    line_div.append(surah_name_div)
    return line_div


def create_bismillah_line(soup, line_number):
    line_div = soup.new_tag("div", **{"class": "line line---bismillah", "id": f"line-{line_number}"})
    bismillah_div = soup.new_tag("div", **{"class": "bismillah text-center"})
    bismillah_div.string = "﷽"
    line_div.append(bismillah_div)
    return line_div


def process_page(page_number):
    with sqlite3.connect(DB_LAYOUT_PATH) as conn_layout, sqlite3.connect(DB_WORDS_PATH) as conn_words:
        cursor_layout = conn_layout.cursor()
        cursor_words = conn_words.cursor()
        pages_data = get_pages_data(cursor_layout, page_number)
        with open("index.html", "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")
        modify_html_with_pages(soup, pages_data, cursor_words, page_number)
        add_font_face(soup, f"pages/{int(page_number):03}.html", page_number)


if __name__ == "__main__":
    for page_number in tqdm(range(1, 605), desc="Processing Pages"):
        process_page(page_number)
