import requests
from requests.exceptions import ConnectionError
import json
import sqlite3
import os

class ApiError(Exception):
    """Custom exception for API errors."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message

# Get The amount of new Anki cards, used when Anki is not running
def new_card_count_offline(deck_name):
    # Use the %APPDATA% path and expand it to the full path
    anki_db_path = os.path.expandvars(r"%APPDATA%\Anki2\User 1\collection.anki2")

    # Connect to the Anki database
    conn = sqlite3.connect(anki_db_path)
    cursor = conn.cursor()

    # Get the deck ID from the deck name, forcing binary collation for name matching
    cursor.execute("SELECT id FROM decks WHERE name = ? COLLATE BINARY", (deck_name,))
    deck_id_row = cursor.fetchone()

    if deck_id_row:
        deck_id = deck_id_row[0]

        # Count the number of new cards in the specified deck
        cursor.execute("""
            SELECT COUNT(*)
            FROM cards
            WHERE did = ? AND queue = 0
        """, (deck_id,))
        new_card_count = cursor.fetchone()[0]

        conn.close()
        return new_card_count

    else:
        conn.close()
        raise ValueError(f"Deck '{deck_name}' not found.")

# Used when Anki is offline to get the totall number of cards in a deck
def total_card_count_offline(deck_name):
    # Use the %APPDATA% path and expand it to the full path
    anki_db_path = os.path.expandvars(r"%APPDATA%\Anki2\User 1\collection.anki2")

    # Connect to the Anki database
    conn = sqlite3.connect(anki_db_path)
    cursor = conn.cursor()

    # Get the deck ID from the deck name, forcing binary collation for name matching
    cursor.execute("SELECT id FROM decks WHERE name = ? COLLATE BINARY", (deck_name,))
    deck_id_row = cursor.fetchone()

    if deck_id_row:
        deck_id = deck_id_row[0]

        # Count the total number of cards in the specified deck
        cursor.execute("""
            SELECT COUNT(*)
            FROM cards
            WHERE did = ?
        """, (deck_id,))
        total_card_count = cursor.fetchone()[0]

        conn.close()
        return total_card_count

    else:
        conn.close()
        raise ValueError(f"Deck '{deck_name}' not found.")


# Used while Anki is running:
# Function to invoke AnkiConnect API
def invoke(action, params=None):
    return json.dumps({
        'action': action,
        'version': 6,
        'params': params
    })

# Function to get the number of new cards in a deck
def new_card_count_online(deck_name):
    try:
        
        # Request the card IDs for new cards in the deck
        payload = invoke('findCards', {'query': f'deck:"{deck_name}" is:new'})
        response = requests.post("http://localhost:8765", data=payload).json()
        
        # The number of new cards is the length of the list of card IDs
        if response.get('error') is None:
            new_card_count = len(response['result'])
            return new_card_count
        else:
            raise ApiError(f"API Error: {response['error']}")
    
    except ConnectionError as e:
        # Handle the connection error gracefully
        print(f"Error: Could not connect to AnkiConnect on localhost:8765. Please ensure Anki is running and AnkiConnect is enabled. \nDetailed error: {e}")
        return None
    
# Function to get the total number of cards in a deck
def total_card_count_online(deck_name):
    try:
        # Request the card IDs for all cards in the deck
        payload = invoke('findCards', {'query': f'deck:"{deck_name}"'})
        response = requests.post("http://localhost:8765", data=payload).json()
        
        # The total number of cards is the length of the list of card IDs
        if response.get('error') is None:
            total_card_count = len(response['result'])
            return total_card_count
        else:
            raise ApiError(f"API Error: {response['error']}")
    
    except ConnectionError as e:
        # Handle the connection error gracefully
        print(f"Error: Could not connect to AnkiConnect on localhost:8765. Please ensure Anki is running and AnkiConnect is enabled. \nDetailed error: {e}")
        return None

# This will be used to export all of the definitions, it will find the amount of a card type
def anki_card_count(deck_name, card_type, online):
    def get_card_count(func_online, func_offline):
        try:
            return func_online(deck_name) if online else func_offline(deck_name)
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    try:
        if card_type == 'new':
            new_cards = get_card_count(new_card_count_online, new_card_count_offline)
            return new_cards
        
        elif card_type == 'total':
            total_cards = get_card_count(total_card_count_online, total_card_count_offline)
            return total_cards
        
        elif card_type == 'seen':
            total_cards = get_card_count(total_card_count_online, total_card_count_offline)
            new_cards = get_card_count(new_card_count_online, new_card_count_offline)
            
            if total_cards is not None and new_cards is not None:
                return total_cards - new_cards
            else:
                raise ValueError("Could not compute learned cards due to failed API calls.")
        
        else:
            raise ValueError("Invalid card_type specified.")
    
    except Exception as e:
        print(f"Error: {e}")
        return None
