import os
import time
import subprocess
from anki_new_cards import ApiError, anki_card_count
from pypresence import Presence, exceptions

class AnkiDiscordIntegration:
    def __init__(self, deck_name, client_id, state, details, large_image, small_image, attempt_reconnect=True):
        self.deck_name = deck_name
        self.client_id = client_id
        self.state = state
        self.details = details
        self.large_image = large_image
        self.small_image = small_image
        self.attempt_reconnect = attempt_reconnect
        self.rpc = Presence(self.client_id)
        self.process = None
        self.total_cards = None
        self.learned_cards = None
        self.new_cards = None

    def initial_card_check(self):
        try:
            self.total_cards = anki_card_count(self.deck_name, 'total', False)
            if self.total_cards is None:
                raise ValueError("Could not retrieve total cards.")

            self.new_cards = anki_card_count(self.deck_name, 'new', False)
            if self.new_cards is None:
                raise ValueError("Could not retrieve new cards.")

            self.learned_cards = self.total_cards - self.new_cards
            print(f"Total Cards: {self.total_cards} \nNew Cards: {self.new_cards} \nLearned Cards: {self.learned_cards}")
        except Exception as e:
            print(f"Error during card check: {e}")
            self.total_cards, self.learned_cards, self.new_cards = None, None, None

    def start_anki(self):
        user_profile = os.getenv('USERPROFILE')
        application_path = os.path.join(user_profile, 'AppData', 'Local', 'Programs', 'Anki', 'anki.exe')
        self.process = subprocess.Popen(application_path)
        print("Anki started...")

    def update_discord(self):
        try:
            updated_new_cards = anki_card_count(self.deck_name, 'new', True)
            if updated_new_cards is not None:
                self.learned_cards = self.total_cards - updated_new_cards

            self.rpc.update(details=self.details,
                            state=self.state,
                            party_size=[self.learned_cards, self.total_cards],
                            large_image=self.large_image,
                            small_image=self.small_image)
            print("Discord status updated...")
        except ApiError:
            print("API Error during Discord update.")
        except exceptions.PipeClosed:
            print("Discord Pipe closed. Attempting to reconnect...")
            return "closed"

    def reconnect_loop(self):
        while self.process.poll() is None:
            try:
                self.rpc.connect()
                print("Reconnected to Discord.")
                break
            except Exception:
                print("Reconnection failed. Retrying in 30 seconds...")
                time.sleep(30)

    def run(self):
        self.initial_card_check()
        self.start_anki()

        try:
            self.rpc.connect()
            print("Connected to Discord.")
        except:
            self.reconnect_loop()

        try:
            if self.process.poll() is None:
                while True:
                    discord_state = self.update_discord()
                    if discord_state == "closed":
                        self.reconnect_loop()
                    else:
                        time.sleep(15)

                    if self.process.poll() is not None:
                        break
        finally:
            try:
                self.rpc.close()
                print("Discord connection closed.")
            except AssertionError:
                print("No active Discord connection to close.")

if __name__ == "__main__":
    config = {
        'deck_name': 'RTK 6th Edition',
        'client_id': '1274521090223374357',
        'state': 'Learned:',
        'details': 'Learning Japanese Kanji',
        'large_image': 'https://media.tenor.com/mxdQY5HWAJgAAAAi/anki.gif',
        'small_image': 'https://media.tenor.com/1mmqCqoZsdQAAAAj/facebook-emoji.gif',
    }

    anki_discord = AnkiDiscordIntegration(**config)
    anki_discord.run()
    print("Anki has been closed. Exiting script.")