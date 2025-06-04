import sys
import signal
import threading
import time
import argparse
import configparser
import os
from typing import Optional
from enum import Enum


#
# This is a AI conversion of the main program for the C# version. Untested and probably lots need to be adjusted/removed.
#

class CtrlTypes(Enum):
    """Control message types for handler routine"""
    CTRL_C_EVENT = 0
    CTRL_BREAK_EVENT = 1
    CTRL_CLOSE_EVENT = 2
    CTRL_LOGOFF_EVENT = 5
    CTRL_SHUTDOWN_EVENT = 6

class UbiServicesNotAvailableException(Exception):
    """Exception raised when Ubisense services are not available"""
    pass

class FractalTracker:
    """Main FractalTracker program class"""

    # Class variables
    input_filename: Optional[str] = None
    type_filter: str = ""
    debug: bool = False
    version: str = "0.99i"
    output_filename: str = "fmhi_data_0.99.sqlite"
    quit: bool = False
    rh: Optional['ReadingHandler'] = None
    ut: Optional['UbiTracker'] = None
    ulr: Optional['UbiLogReader'] = None
    min_mult: float = 0.5
    max_mult: float = 10.0
    velocity_mode: bool = False

    @classmethod
    def main(cls, args: list[str]) -> None:
        """Main program entry point"""
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, cls.ctrl_msg_handler)
        signal.signal(signal.SIGTERM, cls.ctrl_msg_handler)

        print(f"FractalTracker {cls.version}")
        print("Copyright Dr. Jeffrey Craighead 2008,2011")
        print("--------------\n")

        # Process command line arguments
        cls.process_args(args)

        # Display multiplier settings
        print(f"Using minMult={cls.min_mult:.1f} and maxMult={cls.max_mult:.1f}\n")

        # Create reading handler
        cls.rh = ReadingHandler(cls.output_filename)

        # Check if using input log file or listening for messages
        if cls.input_filename is None:
            # Listen for messages from Ubisense services
            while not cls.quit and cls.ut is None:
                try:
                    cls.ut = UbiTracker(cls.rh, cls.min_mult, cls.max_mult)
                except UbiServicesNotAvailableException as e:
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(str(e))
                    print("Error Initializing UbiTracker - Services Must Be Down! Waiting.\n")
                    cls.ut = None
                    time.sleep(5)
        else:
            # Process log file
            cls.ulr = UbiLogReader(cls.rh, cls.min_mult, cls.max_mult)
            cls.quit = cls.ulr.process_log_file(cls.input_filename)

        # Wait until program is done or user quits
        while not cls.quit:
            time.sleep(0.01)

        print("Program Complete")
        cls.rh.clean_up_and_quit()
        if hasattr(cls.rh, 'log_thread') and cls.rh.log_thread:
            cls.rh.log_thread.join()

        sys.exit(0)

    @classmethod
    def ctrl_msg_handler(cls, signum, frame) -> None:
        """Handle control messages for graceful shutdown"""
        print("Quitting Now")
        if cls.ulr is not None:
            cls.ulr.quit()
            cls.quit = True
        elif cls.ut is not None:
            cls.quit = True
        else:
            sys.exit(0)

    @classmethod
    def process_args(cls, args: list[str]) -> None:
        """Process command line arguments and configuration file"""

        # First, try to read from config file
        cls._process_config_file()

        # Then process command line arguments (these override config)
        parser = argparse.ArgumentParser(
            description='FractalTracker - Real time fractal path analysis',
            add_help=False
        )

        parser.add_argument('-log', dest='log_file',
                          help='Read from a Ubisense Logger log file')
        parser.add_argument('-o', dest='output_file',
                          help='Write sqlite database to specified filename')
        parser.add_argument('-minmult', type=float, dest='min_mult',
                          help='Set minimum multiplier for RTFPA algorithm')
        parser.add_argument('-maxmult', type=float, dest='max_mult',
                          help='Set maximum multiplier for RTFPA algorithm')
        parser.add_argument('-v', action='store_true', dest='velocity_mode',
                          help='Use Update Rate Invariant Mode')
        parser.add_argument('-type', dest='type_filter',
                          help='Only record tags with specified type')
        parser.add_argument('-debug', action='store_true',
                          help='Display additional debug information')
        parser.add_argument('-?', '?', action='help',
                          help='Show this help message')

        parsed_args = parser.parse_args(args[1:])

        # Apply command line arguments
        if parsed_args.log_file:
            cls.input_filename = parsed_args.log_file
            print(f"Reading from log file: {cls.input_filename}\n")

        if parsed_args.output_file:
            cls.output_filename = parsed_args.output_file
            print(f"Writing to log file: {cls.output_filename}\n")

        if parsed_args.min_mult is not None:
            cls.min_mult = parsed_args.min_mult

        if parsed_args.max_mult is not None:
            cls.max_mult = parsed_args.max_mult

        if parsed_args.velocity_mode:
            cls.velocity_mode = True
            print("Using Update Rate Invariant Mode.\n")

        if parsed_args.type_filter:
            cls.type_filter = parsed_args.type_filter
            print(f"Only recording tags with type: {cls.type_filter}\n")

        if parsed_args.debug:
            cls.debug = True
            print("DEBUG MODE\n")

    @classmethod
    def _process_config_file(cls) -> None:
        """Process configuration file if it exists"""
        config_file = 'fractaltracker.ini'  # You can adjust the config filename

        if os.path.exists(config_file):
            config = configparser.ConfigParser()
            config.read(config_file)

            if 'Settings' in config:
                settings = config['Settings']

                if 'log' in settings:
                    cls.input_filename = settings['log']
                    print(f"Reading from log file: {cls.input_filename}\n")

                if 'o' in settings:
                    cls.output_filename = settings['o']
                    print(f"Writing to log file: {cls.output_filename}\n")

                if 'minmult' in settings:
                    cls.min_mult = float(settings['minmult'])

                if 'maxmult' in settings:
                    cls.max_mult = float(settings['maxmult'])

                if 'v' in settings and settings.getboolean('v'):
                    cls.velocity_mode = True
                    print("Using Update Rate Invariant Mode.\n")

                if 'type' in settings:
                    cls.type_filter = settings['type']
                    print(f"Only recording tags with type: {cls.type_filter}\n")

                if 'debug' in settings and settings.getboolean('debug'):
                    cls.debug = True
                    print("DEBUG MODE\n")


# Placeholder classes - you'll need to implement these based on your other source files
class ReadingHandler:
    def __init__(self, output_filename: str):
        self.output_filename = output_filename
        self.log_thread: Optional[threading.Thread] = None
        # Initialize database connection, etc.

    def clean_up_and_quit(self):
        # Clean up resources
        pass

class UbiTracker:
    def __init__(self, reading_handler: ReadingHandler, min_mult: float, max_mult: float):
        self.rh = reading_handler
        self.min_mult = min_mult
        self.max_mult = max_mult
        # Initialize Ubisense connection
        # Raise UbiServicesNotAvailableException if services are down

class UbiLogReader:
    def __init__(self, reading_handler: ReadingHandler, min_mult: float, max_mult: float):
        self.rh = reading_handler
        self.min_mult = min_mult
        self.max_mult = max_mult
        self.should_quit = False

    def process_log_file(self, filename: str) -> bool:
        # Process the log file
        # Return True when done
        return True

    def quit(self):
        self.should_quit = True


if __name__ == "__main__":
    FractalTracker.main(sys.argv)
