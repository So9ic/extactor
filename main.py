import requests
import base64

# Constants
GITHUB_USERNAME = "So9ic"
GITHUB_REPO = "extactor"
GITHUB_TOKEN = "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"
BASE_URL = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents"
WORDS_FILE_URL = "https://raw.githubusercontent.com/So9ic/extactor/refs/heads/main/words.txt"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}


def get_last_processed_word():
    """Retrieve the last processed word from tracking.txt"""
    url = f"{BASE_URL}/tracking.txt"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        content = response.json()
        file_content = base64.b64decode(content['content']).decode("utf-8").strip()
        return file_content
    elif response.status_code == 404:
        print("tracking.txt not found. Starting fresh.")
        return None
    else:
        print(f"Error fetching tracking.txt: {response.status_code}, {response.text}")
        return None


def update_tracking_word(word):
    """Update tracking.txt with the current word"""
    url = f"{BASE_URL}/tracking.txt"
    try:
        response = requests.get(url, headers=HEADERS)
        sha = response.json().get('sha') if response.status_code == 200 else None

        data = {
            "message": f"Update tracking word to {word}",
            "content": base64.b64encode(word.encode("utf-8")).decode("utf-8"),
            "sha": sha,
        }
        put_response = requests.put(url, headers=HEADERS, json=data)
        if put_response.status_code not in [200, 201]:
            print(f"Error updating tracking.txt: {put_response.status_code}, {put_response.text}")
    except Exception as e:
        print(f"Error updating tracking.txt: {str(e)}")


def read_words_from_file():
    """Fetch the words from the raw URL"""
    try:
        response = requests.get(WORDS_FILE_URL)
        response.raise_for_status()
        return [line.strip() for line in response.text.splitlines() if line.strip()]
    except requests.RequestException as e:
        print(f"Error fetching words.txt: {str(e)}")
        return []


def save_to_file(word, categorized_meanings):
    """Append new entries to dictionary.txt"""
    url = f"{BASE_URL}/dictionary.txt"
    try:
        response = requests.get(url, headers=HEADERS)
        sha = response.json().get('sha') if response.status_code == 200 else None

        # Prepare the new content
        existing_content = ""
        if response.status_code == 200:
            existing_content = base64.b64decode(response.json()['content']).decode("utf-8")

        new_entries = []
        for pos, meaning in categorized_meanings.items():
            meaning = ' '.join(meaning.split())
            new_entries.append(f"{word}: ({pos}) {meaning}\n")

        new_content = existing_content + ''.join(new_entries)

        # Upload the updated content
        data = {
            "message": f"Add/update dictionary entry for {word}",
            "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
            "sha": sha,
        }
        put_response = requests.put(url, headers=HEADERS, json=data)
        if put_response.status_code not in [200, 201]:
            print(f"Error updating dictionary.txt: {put_response.status_code}, {put_response.text}")
    except Exception as e:
        print(f"Error saving to dictionary.txt: {str(e)}")


def get_word_meanings(word):
    """Scrape dictionary.com for word meanings"""
    url = f"https://www.dictionary.com/browse/{word}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        from bs4 import BeautifulSoup
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


def main():
    words = read_words_from_file()
    if not words:
        print("No words found in words.txt")
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
                save_to_file(found_word, categorized_meanings)
                print(f"Added {found_word} with {len(categorized_meanings)} parts of speech")
            else:
                print(f"No meanings found for {word}")


if __name__ == "__main__":
    main()
