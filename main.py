import mysql.connector
import requests
from bs4 import BeautifulSoup
import time
import string

# Database connection
db = mysql.connector.connect(
    host="srv1473.hstgr.io",
    user="u565640325_so9ic",
    password="fM&eW~c?2Y",
    database="u565640325_wtf"
)
cursor = db.cursor()

# Create tables if they don't exist
def setup_database():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INT AUTO_INCREMENT PRIMARY KEY,
            word VARCHAR(255) UNIQUE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dictionary (
            id INT AUTO_INCREMENT PRIMARY KEY,
            word VARCHAR(255),
            pos VARCHAR(50),
            meaning TEXT,
            UNIQUE KEY word_pos (word, pos)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracking (
            id INT PRIMARY KEY DEFAULT 1,
            last_word VARCHAR(255)
        )
    """)
    db.commit()

def get_last_processed_word():
    cursor.execute("SELECT last_word FROM tracking WHERE id = 1")
    result = cursor.fetchone()
    return result[0] if result else None

def update_tracking_word(word):
    cursor.execute("""
        INSERT INTO tracking (id, last_word) 
        VALUES (1, %s) 
        ON DUPLICATE KEY UPDATE last_word = %s
    """, (word, word))
    db.commit()

def read_words_from_file():
    cursor.execute("SELECT word FROM words")
    return [row[0] for row in cursor.fetchall()]

def entry_exists(word, pos, meaning):
    cursor.execute("""
        SELECT 1 FROM dictionary 
        WHERE word = %s AND pos = %s AND meaning = %s
    """, (word, pos, meaning))
    return cursor.fetchone() is not None

def extract_first_meaning_from_li(li_element):
    """Extract only the first meaning from a list item."""
    try:
        span = li_element.find('span', class_='HGU9YJqWX_GVHkeeJhSH')
        if span:
            meaning_div = span.find('div', class_='NZKOFkdkcvYgD3lqOIJw')
            if meaning_div:
                inner_div = meaning_div.find('div')
                if inner_div:
                    meaning = inner_div.get_text(strip=True)
                    return meaning
    except Exception as e:
        print(f"Error extracting meaning: {str(e)}")
    return None

def get_word_meanings(word):
    url = f"https://www.dictionary.com/browse/{word}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        word_element = soup.find('h1')
        if not word_element or word_element.text.strip().lower() != word.lower():
            print(f"Word not found: {word}")
            return None

        sections = soup.find_all('section', class_='uLEIc6UAEiaBDDj6qSnO')

        categorized_meanings = {}
        for section in sections:
            pos_header = section.find('h2')
            if pos_header:
                pos = pos_header.text.strip()

                meaning_list = section.find('ol', class_='lpwbZIOD86qFKLHJ2ZfQ E53FcpmOYsLLXxtj5omt')
                if meaning_list:
                    first_li = meaning_list.find('li', recursive=False)
                    if first_li:
                        meaning = extract_first_meaning_from_li(first_li)
                        if meaning and meaning.strip():
                            categorized_meanings[pos] = meaning

        return word, categorized_meanings

    except requests.RequestException as e:
        print(f"Error fetching {word}: {str(e)}")
        return None

def save_to_database_and_file(word, categorized_meanings):
    """Save to both database and generate txt file"""
    # Save to database
    for pos, meaning in categorized_meanings.items():
        meaning = ' '.join(meaning.split())
        if not entry_exists(word, pos, meaning):
            cursor.execute("""
                INSERT IGNORE INTO dictionary (word, pos, meaning)
                VALUES (%s, %s, %s)
            """, (word, pos, meaning))
    db.commit()

    # Export entire database to txt file
    cursor.execute("SELECT word, pos, meaning FROM dictionary ORDER BY word")
    results = cursor.fetchall()
    
    # Replace this path with your Hostinger path
    with open('dictionary.txt', 'w', encoding='utf-8') as f:
        for word, pos, meaning in results:
            f.write(f"{word}: ({pos}) {meaning}\n")

def main():
    setup_database()
    
    words = read_words_from_file()
    if not words:
        print("No words found in database")
        return

    last_word = get_last_processed_word()
    start_index = 0

    if last_word:
        try:
            start_index = words.index(last_word)
            print(f"Resuming from word: {last_word}")
        except ValueError:
            print(f"Last processed word {last_word} not found, starting from beginning")

    for word in words[start_index:]:
        print(f"Processing word: {word}")
        update_tracking_word(word)

        result = get_word_meanings(word)
        if result:
            found_word, categorized_meanings = result
            if categorized_meanings:
                save_to_database_and_file(found_word, categorized_meanings)
                print(f"Added {found_word} with {len(categorized_meanings)} parts of speech")
            else:
                print(f"No meanings found for {word}")

if __name__ == "__main__":
    try:
        main()
    finally:
        cursor.close()
        db.close()
