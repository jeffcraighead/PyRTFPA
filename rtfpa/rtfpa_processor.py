import os
from dataclasses import field, dataclass
from tkinter import filedialog
from colorama import init, Fore, Style
import pandas
import pandas as pd
from typing import Optional, Dict, List, Callable
from pathlib import Path

import tkinter as tk

from data_adapters import DataAdapter, EyeTrackingCSVAdapter
from rtfpa import RTFPA, RunningD


@dataclass
class ProcessingConfig:
    """Configuration for RTFPA processing"""
    min_multiplier: float = 0.5
    max_multiplier: float = 10.0
    constrain_to_plane: bool = True
    velocity_mode: bool = False
    path_timeout: int = 60
    max_points: Optional[int] = None
    progress_callback: Optional[Callable[[int, Optional[int]], None]] = None


@dataclass
class RTFPAProcessor:
    """Main processor that uses data adapters to calculate fractal dimensions"""

    config: ProcessingConfig = field(default_factory=ProcessingConfig)
    rtfpa: RTFPA = field(init=False)
    results: Dict[str, List[RunningD]] = field(init=False, default_factory=dict)

    def __post_init__(self):
        """Initialize RTFPA with configuration"""
        self.rtfpa = RTFPA(self.config.min_multiplier, self.config.max_multiplier)
        self.rtfpa.set_plane_constraint(self.config.constrain_to_plane)
        self.rtfpa.set_velocity_mode(self.config.velocity_mode)
        self.rtfpa.set_timeout(self.config.path_timeout)

    def process_data(self, adapter: DataAdapter) -> list[str]:
        """
        Process data from an adapter

        Args:
            adapter: Data adapter to use

        Returns:
            Dictionary mapping subject_id to final RunningD object
        """
        point_count = 0

        for data_point in adapter.get_data_stream():
            # Process the point
            running_d = self.rtfpa.new_reading(
                subject_id=data_point.subject_id,
                x=data_point.x,
                y=data_point.y,
                z=data_point.z,
                timestamp=data_point.timestamp
            )

            # Store results
            if data_point.subject_id not in self.results:
                self.results[data_point.subject_id] = []
            if running_d is not None: # append the running_d object each time we have a new path (thus a new running_d).
                self.results[data_point.subject_id].append(running_d)

            point_count += 1

            # Progress callback
            if self.config.progress_callback:
                self.config.progress_callback(point_count, self.config.max_points)

            # Check max points
            if self.config.max_points and point_count >= self.config.max_points:
                break

        return [*self.results] # return a list of subject_id strings since these are the keys to self.results

    def get_time_series(self, subject_id: str) -> pd.DataFrame:
        """
        Get time series data for a subject

        Returns:
            DataFrame with columns: timestamp, D, steps, path_length
        """
        if subject_id not in self.results:
            return pd.DataFrame()

        data = []
        for rd in self.results[subject_id]:
            data.append({
                'subject_id': rd.subject_id,
                'start_timestamp': rd.start_timestamp,
                'end_timestamp': rd.end_timestamp,
                'D': rd.D,
                'steps': rd.number_of_steps,
                'path_length': round(rd.real_path_length,3),
                'mean_step_size': round(rd.mean_step_size,3)
            })

        return pd.DataFrame(data)


@dataclass
class ProcessingResult:
    """Results from processing a dataset"""
    subject_id: str
    time_series: pd.DataFrame = field(default_factory=pd.DataFrame)


# Helper functions for common use cases
def process_csv_file(
    file_path: Path,
    eye: str = "Left",
    x_scale_factor: float = 1.0,
    y_scale_factor: float = 1.0,
    config: Optional[ProcessingConfig] = None
) -> Dict[str, ProcessingResult]:
    """
    Convenience function to process a CSV file

    Args:
        file_path: Path to CSV file
        eye: Which eye to use
        scale_factor: Scaling factor for coordinates
        config: Processing configuration

    Returns:
        Dictionary of processing results by subject
    """
    if config is None:
        config = ProcessingConfig()

    processor = RTFPAProcessor(config)

    with EyeTrackingCSVAdapter(file_path, eye, x_scale_factor, y_scale_factor, (0.0, 1.0)) as adapter:
        adapter.initialize()
        subject_ids = processor.process_data(adapter)

        # Create ProcessingResult objects
        results = {}
        # TODO - need to change the items in the ProcessingResult object. We don't care about most of those.
        for subject_id in subject_ids:
            results[subject_id] = ProcessingResult(subject_id=subject_id, time_series=processor.get_time_series(subject_id))

        return results


def select_data_root() -> str:
    # Create (and hide) the root window
    root = tk.Tk()
    root.withdraw()

    # Code that pops a dialog box to choose file we wish to work on
    # Make sure dialogs pop up in front
    root.attributes('-topmost', True)
    root.update()

    print("Chose the folder that contains ESUEvents.csv files.")
    # Show the standard file-open dialog
    events_path = filedialog.askdirectory(
        title="Select a folder that contains the CSV events file",
    )
    print("You selected:", events_path)

    # Clean up the hidden root window
    root.destroy()

    return events_path

# Iterate through a directory and subdirectories and process any file that is named ESUEvents.edf
def process_directory_tree(directory_path):
    for dirpath, dirnames, filenames in os.walk(directory_path):
        for filename in filenames:
            if "eyepose_events.csv" in filename:
                file_path = Path(os.path.normpath(os.path.join(dirpath, filename)))
                try:
                    process_file(file_path)
                except pandas.errors.EmptyDataError:
                    print(f"{Fore.RED}No data found in {file_path}, skipping.{Style.RESET_ALL}")


def process_file(file_path):
    config = ProcessingConfig(
        min_multiplier=0.5,
        max_multiplier=10.0,
        constrain_to_plane=True,
        velocity_mode=False,
        path_timeout=15,
        progress_callback=lambda current, total: print(f"Progress: {current}") if current % 100 == 0 else None
    )

    results = process_csv_file(
        file_path,
        eye="Left",
        x_scale_factor=1920.0,  # Scale to screen pixels
        y_scale_factor=1080.0,
        config=config
    )

    # Display results
    for subject_id, result in results.items():
        print(f"\n{subject_id}:")
        print(f"Number of Paths {len(result.time_series)}")

        # Save time series
        output_file_path = f"{str(file_path)[:-3]}_analysis.csv"
        result.time_series.to_csv(output_file_path, index=False)

# Example usage
if __name__ == "__main__":
    data_root_path = Path(select_data_root())
    process_directory_tree(data_root_path)






    # Example 2: Process LSL stream with minimal configuration
    # processor = RTFPAProcessor()  # Uses default config
    #
    # with LSLAdapter("EyeTracker", "Left") as adapter:
    #     adapter.initialize()
    #     results = processor.process_data(adapter)
