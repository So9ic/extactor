import requests
from bs4 import BeautifulSoup
import requests
import os

# GitHub configuration
GITHUB_USERNAME = "So9ic"
GITHUB_REPO = "extactor"
GITHUB_TOKEN = "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"
BASE_URL = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_file_content(file_name):
    """Fetch file content from GitHub repository."""
    url = f"{BASE_URL}/{file_name}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        content = response.json()["content"]
        return requests.utils.unquote(content).encode("latin1").decode("utf-8")
    elif response.status_code == 404:
        return None
    else:
        print(f"Error fetching {file_name}: {response.status_code}, {response.text}")
        return None

def upload_file(file_name, content, message="Update file"):
    """Upload or update a file in the GitHub repository."""
    url = f"{BASE_URL}/{file_name}"
    existing_content = get_file_content(file_name)
    data = {
        "message": message,
        "content": requests.utils.quote(content.encode("utf-8")),
        "branch": "main"
    }
    if existing_content:
        # Get the SHA for updating the file
        sha = requests.get(url, headers=HEADERS).json()["sha"]
        data["sha"] = sha

    response = requests.put(url, headers=HEADERS, json=data)
    if response.status_code in [200, 201]:
        print(f"{file_name} uploaded successfully.")
    else:
        print(f"Error uploading {file_name}: {response.status_code}, {response.text}")

def get_last_processed_word():
    """Retrieve the last processed word from GitHub."""
    content = get_file_content("tracking.txt")
    return content.strip() if content else None

def update_tracking_word(word):
    """Update tracking.txt with the last processed word."""
    upload_file("tracking.txt", word, message=f"Updated tracking word to {word}")

def read_words_from_file():
    """Retrieve words from words.txt stored in GitHub."""
    content = get_file_content("words.txt")
    return [line.strip() for line in content.splitlines()] if content else []

def entry_exists(word, pos, meaning):
    """Check if an entry exists in dictionary.txt."""
    content = get_file_content("dictionary.txt")
    if content:
        entry = f"{word}: ({pos}) {meaning}"
        return entry in content
    return False

def save_to_file(word, categorized_meanings):
    """Save word and its meanings to dictionary.txt."""
    content = get_file_content("dictionary.txt")
    existing_data = content + "\n" if content else ""
    new_entries = []
    for pos, meaning in categorized_meanings.items():
        if not entry_exists(word, pos, meaning):
            new_entries.append(f"{word}: ({pos}) {meaning}")
    updated_content = existing_data + "\n".join(new_entries)
    upload_file("dictionary.txt", updated_content, message="Updated dictionary.txt")

def extract_first_meaning_from_li(li_element):
    """Extract only the first meaning from a list item."""
    try:
        span = li_element.find('span', class_='HGU9YJqWX_GVHkeeJhSH')
        if span:
            meaning_div = span.find('div', class_='NZKOFkdkcvYgD3lqOIJw')
            if meaning_div:
                inner_div = meaning_div.find('div')
                if inner_div:
                    return inner_div.get_text(strip=True)
    except Exception as e:
        print(f"Error extracting meaning: {str(e)}")
    return None

def get_word_meanings(word):
    """Fetch word meanings from dictionary.com."""
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
