import os
from bs4 import BeautifulSoup, NavigableString
from lxml import etree
import re

def extract_verse_info(soup):
    verses = []
    current_verse_id = None
    current_verse_text = []
    indentation = " "  # Define the desired indentation
    chapter_number_pattern = re.compile(r'^\d+\s+')  # Pattern to match chapter numbers

    def flush_current_verse():
        nonlocal current_verse_id, current_verse_text
        if current_verse_id is not None and current_verse_text:
            # Join text, ensuring consistent indentation
            full_text = ''.join(current_verse_text).strip()
            # Remove chapter numbers from the beginning of the text
            full_text = re.sub(chapter_number_pattern, '', full_text)
            verses.append((current_verse_id, full_text))
            current_verse_text = []

    for p_tag in soup.find_all('p', class_=["bi", "ei", "sl"]):
        is_sl_class = "sl" in p_tag.get('class', [])
        for content in p_tag.children:
            if isinstance(content, NavigableString):
                if is_sl_class:
                    # Directly append text with indentation for 'sl' class
                    current_verse_text.append(indentation + content.strip())
                else:
                    # Append non-'sl' class text without additional indentation
                    current_verse_text.append(content.strip())
            elif content.name == 'span' and 'di' in content.get('class', []):
                flush_current_verse()
                current_verse_id = content.text.replace('v', '').strip()
            elif content.name == 'br' and is_sl_class:
                # For 'br' tags within 'sl' class paragraphs, start a new line with indentation
                current_verse_text.append('\n' + indentation)

    flush_current_verse()  # Ensure to flush the last verse
    return verses



def parse_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
    h3_tag = soup.find('h3')
    if h3_tag:
        book_title = h3_tag.text.strip()
        verses = extract_verse_info(soup)
        return book_title, verses
    return None, []

def build_zefania_xml(directory_path, output_path):
    xmlns = "http://www.zefania.de/zefaniaxml"
    # Define namespace mapping
    nsmap = {
        None: "http://www.w3.org/2001/XMLSchema-instance"  # Default namespace
    }
    xsi_schema_location = "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation"
    
    # Create the root element with namespaces
    xml_root = etree.Element("XMLBIBLE", 
                             attrib={xsi_schema_location: "zef2005.xsd"},
                             biblename="Bible Name", 
                             status="v", 
                             version="2.0.1.18", 
                             type="x-bible", 
                             revision="0")
    
    # Add INFORMATION element with sub-elements
    information = etree.SubElement(xml_root, "INFORMATION")
    etree.SubElement(information, "title").text = "Your Title"
    etree.SubElement(information, "description").text = "Your Description"
    etree.SubElement(information, "publisher").text = "Your Publisher"
    etree.SubElement(information, "date").text = "Your Year"
    etree.SubElement(information, "format").text = "Zefania XML Bible Markup Language"
    etree.SubElement(information, "language").text = "Your Language"
    books = {}

    book_number = 1  # Initialize book number counter

    for filename in sorted(os.listdir(directory_path)):
        if filename.endswith(".html"):
            book_title, verses = parse_html_file(os.path.join(directory_path, filename))
            if book_title:
                # Dynamically generate bsname from the first three letters of book_title
                bsname = book_title[:3]
                
                # Use book_number as the bnumber for the BIBLEBOOK tag
                if book_title not in books:
                    current_book = etree.SubElement(xml_root, "BIBLEBOOK", bnumber=str(book_number), bname=book_title, bsname=bsname)
                    books[book_title] = {"book_element": current_book, "last_chapter": 0}
                    book_number += 1  # Increment book number for the next book
                
                # Assume a new chapter for every file; adjust this logic if files represent something else
                books[book_title]["last_chapter"] += 1
                chapter_number = books[book_title]["last_chapter"]
                chapter_element = etree.SubElement(books[book_title]["book_element"], "CHAPTER", cnumber=str(chapter_number))
                
                for verse_id, verse_text in verses:
                    # Correctly parse and assign verse numbers and text
                    etree.SubElement(chapter_element, "VERS", vnumber=verse_id).text = verse_text

    tree = etree.ElementTree(xml_root)
    tree.write(output_path, encoding='utf-8', xml_declaration=True, pretty_print=True)


directory_path = r'OPS'  # Update this path, ePub html file collection location
output_path = 'bible_output.xml'
build_zefania_xml(directory_path, output_path)
