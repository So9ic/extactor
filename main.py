import requests
from bs4 import BeautifulSoup
import os
import time
import string
from keep_alive import keep_alive

keep_alive()

def get_last_processed_word():
    """Read the last processed word from tracking.txt"""
    try:
        if os.path.exists('tracking.txt'):
            with open('tracking.txt', 'r', encoding='utf-8') as f:
                return f.read().strip()
    except Exception as e:
        print(f"Error reading tracking.txt: {str(e)}")
    return None

def update_tracking_word(word):
    """Update tracking.txt with current word"""
    try:
        with open('tracking.txt', 'w', encoding='utf-8') as f:
            f.write(word)
    except Exception as e:
        print(f"Error updating tracking.txt: {str(e)}")

def read_words_from_file():
    """Read words from words.txt"""
    try:
        with open('words.txt', 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading words.txt: {str(e)}")
        return []

def entry_exists(word, pos, meaning):
    """Check if entry already exists in dictionary.txt"""
    try:
        if os.path.exists('dictionary.txt'):
            with open('dictionary.txt', 'r', encoding='utf-8') as f:
                entry = f"{word}: ({pos}) {meaning}"
                for line in f:
                    if line.strip() == entry.strip():
                        return True
    except Exception as e:
        print(f"Error checking dictionary.txt: {str(e)}")
    return False

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

def save_to_file(word, categorized_meanings):
    """Append new entries to dictionary.txt"""
    try:
        with open('dictionary.txt', 'a', encoding='utf-8') as f:
            for pos, meaning in categorized_meanings.items():
                meaning = ' '.join(meaning.split())
                if not entry_exists(word, pos, meaning):
                    f.write(f"{word}: ({pos}) {meaning}\n")
    except Exception as e:
        print(f"Error saving to dictionary.txt: {str(e)}")

def main():
    # Create dictionary.txt if it doesn't exist
    if not os.path.exists('dictionary.txt'):
        open('dictionary.txt', 'w', encoding='utf-8').close()

    # Read words from file
    words = read_words_from_file()
    if not words:
        print("No words found in words.txt")
        return

    # Get last processed word
    last_word = get_last_processed_word()
    start_index = 0

    # Find starting point
    if last_word:
        try:
            start_index = words.index(last_word)
            print(f"Resuming from word: {last_word}")
        except ValueError:
            print(f"Last processed word {last_word} not found in words.txt, starting from beginning")

    # Process words
    for word in words[start_index:]:
        print(f"Processing word: {word}")
        update_tracking_word(word)

        result = get_word_meanings(word)
        if result:
            found_word, categorized_meanings = result
            if categorized_meanings:
                save_to_file(found_word, categorized_meanings)
                print(f"Added {found_word} with {len(categorized_meanings)} parts of speech")
            else:
                print(f"No meanings found for {word}")

if __name__ == "__main__":
    main()
