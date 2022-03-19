#!/usr/bin/env python3

import sys
import logging
from PyQt5.QtWidgets import QApplication
from nile.arguments import get_arguments
from nile.downloading import manager
from nile.utils.config import Config
from nile.utils.search import calculate_distance
from nile.api import authorization, session, library
from nile.gui import webview
from nile.models import manifest
from nile import constants,version, codename

class CLI:
    def __init__(
        self, session_manager, config_manager, logger, arguments, unknown_arguments
    ):
        self.config = config_manager
        self.session = session_manager
        self.auth_manager = authorization.AuthenticationManager(
            self.session, self.config
        )
        self.library_manager = library.Library(self.config, self.session)
        self.arguments = arguments
        self.logger = logger
        self.unknown_arguments = unknown_arguments
        if self.auth_manager.is_token_expired():
            self.auth_manager.refresh_token()

    def handle_auth(self):
        if self.arguments.login:
            if not self.auth_manager.is_logged_in():
                self.auth_manager.login()
                return True
            else:
                self.logger.error("You are already logged in")
                return False
        elif self.arguments.logout:
            self.auth_manager.logout()
            return False
        self.logger.error("Specify auth action, use --help")

    def sort_by_title(self, element):
        return element["product"]["title"]

    def handle_library(self):
        cmd = self.arguments.sub_command

        if cmd == "list":
            games_list = ""
            games = self.config.get("library")
            games.sort(key=self.sort_by_title)
            for game in games:
                games_list += f'\033[1;32m{game["product"]["title"]} \033[1;0mGENRES: {game["product"]["productDetail"]["details"]["genres"]}\n'

            games_list += f"\n*** TOTAL {len(games)} ***\n"
            print(games_list)

        elif cmd == "sync":
            if not self.auth_manager.is_logged_in():
                self.logger.error("User not logged in")
                sys.exit(1)
            self.library_manager.sync()

    def handle_install(self):
        games = self.config.get("library")
        games.sort(key=self.sort_by_title)
        matching_games = []
        self.logger.info(f"Searching for {self.arguments.title}")
        for game in games:
            if (
                calculate_distance(
                    game["product"]["title"].lower(), self.arguments.title.lower()
                )
                >= constants.FUZZY_SEARCH_RATIO
            ):
                matching_games.append(game)

        self.logger.debug(f"Matched query with: {[matching_games[i]['product']['title'] for i in range(len(matching_games))]}")

        if len(matching_games) > 1:
            self.logger.error("Matched more than one game! Interactive picker is coming soon")
            return
        if len(matching_games) == 0:
            self.logger.error("Couldn't find what you are looking for")
            return
        self.logger.info(f"Found: {matching_games[0]['product']['title']}")
        self.download_manager = manager.DownloadManager(self.config, self.library_manager, self.session, matching_games[0])
        self.download_manager.download()

    def test(self):
        print("TEST")


def main():
    qApp = QApplication(sys.argv)
    arguments, unknown_arguments = get_arguments()
    if arguments.version:
        print(version, codename)
        return 0
    debug_mode = "-d" in unknown_arguments or "--debug" in arguments
    logging_level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=logging_level, format="%(levelname)s [%(name)s]:\t %(message)s"
    )
    logger = logging.getLogger("CLI")

    config_manager = Config()
    session_manager = session.APIHandler(config_manager)
    cli = CLI(session_manager, config_manager, logger, arguments, unknown_arguments)

    command = arguments.command

    # Always use return qApp.exec()
    # If you spawn gui stuff
    # When running in CLI this can be ignored

    if command == "auth":
        # If spawned a gui method use qApplication exec to wait
        if cli.handle_auth():
            return qApp.exec()

    elif command == "library":
        cli.handle_library()
    elif command == "test":
        cli.test()
    elif command == "install":
        cli.handle_install()
    return 0


if __name__ == "__main__":
    sys.exit(main())
