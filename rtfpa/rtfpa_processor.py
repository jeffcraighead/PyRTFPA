from dataclasses import field, dataclass
import pandas as pd
from typing import Optional, Dict, List, Callable
from pathlib import Path
from data_adapters import DataAdapter, EyeTrackingCSVAdapter
from rtfpa import RTFPA, RunningD


@dataclass
class ProcessingConfig:
    """Configuration for RTFPA processing"""
    min_mult: float = 0.5
    max_mult: float = 10.0
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
        self.rtfpa = RTFPA(self.config.min_mult, self.config.max_mult)
        self.rtfpa.set_plane_constraint(self.config.constrain_to_plane)
        self.rtfpa.set_velocity_mode(self.config.velocity_mode)
        self.rtfpa.set_timeout(self.config.path_timeout)

    def process_data(self, adapter: DataAdapter) -> Dict[str, RunningD]:
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
            if running_d.number_of_steps == 0: # append the running_d object each time we have a new path (thus a new running_d).
                self.results[data_point.subject_id].append(running_d)

            point_count += 1

            # Progress callback
            if self.config.progress_callback:
                self.config.progress_callback(point_count, self.config.max_points)

            # Check max points
            if self.config.max_points and point_count >= self.config.max_points:
                break

        # Return final RunningD for each subject
        return {
            subject_id: readings[-1]
            for subject_id, readings in self.results.items()
            if readings
        }

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
                'path_length': rd.real_path_length,
                'mean_step_size': rd.mean_step_size
            })

        return pd.DataFrame(data)


@dataclass
class ProcessingResult:
    """Results from processing a dataset"""
    subject_id: str
    final_d: float
    total_steps: int
    path_length: float
    time_series: pd.DataFrame = field(default_factory=pd.DataFrame)


# Helper functions for common use cases
def process_csv_file(
    file_path: Path,
    eye: str = "Left",
    scale_factor: float = 1.0,
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

    with EyeTrackingCSVAdapter(file_path, eye, scale_factor, (0.0, 1.0)) as adapter:
        adapter.initialize()
        final_results = processor.process_data(adapter)

        # Create ProcessingResult objects
        results = {}
        for subject_id, final_rd in final_results.items():
            results[subject_id] = ProcessingResult(
                subject_id=subject_id,
                final_d=final_rd.D,
                total_steps=final_rd.number_of_steps,
                path_length=final_rd.real_path_length,
                time_series=processor.get_time_series(subject_id)
            )

        return results


# Example usage
if __name__ == "__main__":
    # Example 1: Process CSV file with custom configuration
    config = ProcessingConfig(
        min_mult=0.5,
        max_mult=10.0,
        constrain_to_plane=True,
        velocity_mode=False,
        progress_callback=lambda current, total: print(f"Progress: {current}") if current % 100 == 0 else None
    )

    results = process_csv_file(
        Path("../data/060930011.110425.085748.ESUEvents.eyepose_events.csv"),
        eye="Left",
        scale_factor=1920.0,  # Scale to screen pixels
        config=config
    )

    # Display results
    for subject_id, result in results.items():
        print(f"\n{subject_id}:")
        print(f"  Final D: {result.final_d:.4f}")
        print(f"  Total steps: {result.total_steps}")
        print(f"  Path length: {result.path_length:.4f}")

        # Save time series
        result.time_series.to_csv(f"{subject_id}_analysis.csv", index=False)

    # Example 2: Process LSL stream with minimal configuration
    # processor = RTFPAProcessor()  # Uses default config
    #
    # with LSLAdapter("EyeTracker", "Left") as adapter:
    #     adapter.initialize()
    #     results = processor.process_data(adapter)
