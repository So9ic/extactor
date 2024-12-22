import requests
from bs4 import BeautifulSoup
import os
import time
import string
import base64
import json

# GitHub configuration
GITHUB_TOKEN = "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"  # Replace with your new token
GITHUB_USERNAME = "So9ic"
GITHUB_REPO = "extactor"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}"

def get_file_from_github(filename):
    """Read file content from GitHub"""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(f"{GITHUB_API_BASE}/contents/{filename}", headers=headers)
        if response.status_code == 200:
            content = base64.b64decode(response.json()["content"]).decode("utf-8")
            return content, response.json()["sha"]
        return None, None
    except Exception as e:
        print(f"Error reading {filename} from GitHub: {str(e)}")
        return None, None

def update_file_on_github(filename, content, sha=None):
    """Update file content on GitHub"""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    data = {
        "message": f"Update {filename}",
        "content": base64.b64encode(content.encode()).decode(),
    }
    
    if sha:
        data["sha"] = sha
    
    try:
        response = requests.put(f"{GITHUB_API_BASE}/contents/{filename}", 
                             headers=headers, 
                             data=json.dumps(data))
        return response.status_code == 200 or response.status_code == 201
    except Exception as e:
        print(f"Error updating {filename} on GitHub: {str(e)}")
        return False

def get_last_processed_word():
    """Read the last processed word from tracking.txt on GitHub"""
    content, _ = get_file_from_github("tracking.txt")
    return content.strip() if content else None

def update_tracking_word(word):
    """Update tracking.txt on GitHub"""
    _, sha = get_file_from_github("tracking.txt")
    update_file_on_github("tracking.txt", word, sha)

def read_words_from_file():
    """Read words from words.txt URL"""
    try:
        response = requests.get("https://raw.githubusercontent.com/So9ic/extactor/refs/heads/main/words.txt")
        response.raise_for_status()
        return [line.strip() for line in response.text.splitlines() if line.strip()]
    except Exception as e:
        print(f"Error reading words.txt: {str(e)}")
        return []

def entry_exists(word, pos, meaning, current_content):
    """Check if entry already exists in dictionary content"""
    entry = f"{word}: ({pos}) {meaning}"
    return entry in current_content

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
    """Append new entries to dictionary.txt on GitHub"""
    content, sha = get_file_from_github("dictionary.txt")
    current_content = content if content else ""
    
    new_entries = []
    for pos, meaning in categorized_meanings.items():
        meaning = ' '.join(meaning.split())
        if not entry_exists(word, pos, meaning, current_content):
            new_entries.append(f"{word}: ({pos}) {meaning}\n")
    
    if new_entries:
        updated_content = current_content + ''.join(new_entries)
        update_file_on_github("dictionary.txt", updated_content, sha)

def main():
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
            start_index = words.index(last_word) + 1  # Start from next word
            print(f"Resuming from after word: {last_word}")
        except ValueError:
            print(f"Last processed word {last_word} not found in words.txt, starting from beginning")

    # Process words
    for word in words[start_index:]:
        print(f"Processing word: {word}")
        update_tracking_word(word)
        
        # Add small delay to avoid hitting rate limits
        time.sleep(1)

        result = get_word_meanings(word)
        if result:
            found_word, categorized_meanings = result
            if categorized_meanings:
                save_to_file(found_word, categorized_meanings)
                print(f"Added {found_word} with {len(categorized_meanings)} parts of speech")
            else:
                print(f"No meanings found for {word}")
        
        # Add small delay between words
        time.sleep(1)

if __name__ == "__main__":
    main()
