import requests
from bs4 import BeautifulSoup
import time
import string
from github import Github
import json

class GitHubHandler:
    def __init__(self, token, owner, repo):
        self.github = Github(token)
        self.repo = self.github.get_user(owner).get_repo(repo)

    def get_file_content(self, filename):
        """Get file content from GitHub"""
        try:
            file_content = self.repo.get_contents(filename)
            return file_content.decoded_content.decode('utf-8'), file_content.sha
        except Exception as e:
            print(f"Error reading {filename} from GitHub: {str(e)}")
            return None, None

    def update_file(self, filename, content, sha):
        """Update file content on GitHub"""
        try:
            self.repo.update_file(
                filename,
                f"Update {filename}",
                content,
                sha
            )
            return True
        except Exception as e:
            print(f"Error updating {filename} on GitHub: {str(e)}")
            return False

def get_last_processed_word(github_handler):
    """Read the last processed word from tracking.txt"""
    content, _ = github_handler.get_file_content('tracking.txt')
    return content.strip() if content else None

def update_tracking_word(github_handler, word):
    """Update tracking.txt with current word"""
    _, sha = github_handler.get_file_content('tracking.txt')
    return github_handler.update_file('tracking.txt', word, sha)

def read_words_from_file(github_handler):
    """Read words from words.txt"""
    content, _ = github_handler.get_file_content('words.txt')
    return [line.strip() for line in content.split('\n') if line.strip()] if content else []

def entry_exists(github_handler, word, pos, meaning):
    """Check if entry already exists in dictionary.txt"""
    content, _ = github_handler.get_file_content('dictionary.txt')
    if content:
        entry = f"{word}: ({pos}) {meaning}"
        return any(line.strip() == entry.strip() for line in content.split('\n'))
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

def save_to_file(github_handler, word, categorized_meanings):
    """Append new entries to dictionary.txt"""
    content, sha = github_handler.get_file_content('dictionary.txt')
    new_entries = []
    
    for pos, meaning in categorized_meanings.items():
        meaning = ' '.join(meaning.split())
        if not entry_exists(github_handler, word, pos, meaning):
            new_entries.append(f"{word}: ({pos}) {meaning}")
    
    if new_entries:
        if content:
            updated_content = content + '\n' + '\n'.join(new_entries)
        else:
            updated_content = '\n'.join(new_entries)
        return github_handler.update_file('dictionary.txt', updated_content, sha)
    return False

def main():
    # GitHub configuration
    GITHUB_TOKEN = "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"  # Replace with your actual token
    GITHUB_REPO_OWNER = "So9ic"
    GITHUB_REPO_NAME = "extactor"
    
    # Initialize GitHub handler
    github_handler = GitHubHandler(GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME)

    # Read words from file
    print("Reading words from GitHub...")
    words = read_words_from_file(github_handler)
    if not words:
        print("No words found in words.txt")
        return

    # Get last processed word
    last_word = get_last_processed_word(github_handler)
    start_index = 0

    # Find starting point
    if last_word:
        try:
            start_index = words.index(last_word) + 1  # Start from next word
            print(f"Resuming from word: {last_word}")
        except ValueError:
            print(f"Last processed word {last_word} not found in words.txt, starting from beginning")

    # Process words
    for word in words[start_index:]:
        print(f"Processing word: {word}")
        update_tracking_word(github_handler, word)

        result = get_word_meanings(word)
        if result:
            found_word, categorized_meanings = result
            if categorized_meanings:
                if save_to_file(github_handler, found_word, categorized_meanings):
                    print(f"Added {found_word} with {len(categorized_meanings)} parts of speech")
                else:
                    print(f"No new meanings added for {word}")
            else:
                print(f"No meanings found for {word}")
        
        # Add a delay to avoid rate limiting
        time.sleep(2)

if __name__ == "__main__":
    main()
