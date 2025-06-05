from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Any, Tuple

import pandas as pd


@dataclass
class DataPoint:
    """Represents a single data point from any source"""
    timestamp: datetime
    subject_id: str
    x: float
    y: float
    z: float = 0.0


class DataAdapter(ABC):
    """Abstract base class for data adapters"""

    @abstractmethod
    def initialize(self, **kwargs) -> None:
        """Initialize the data source connection/file"""
        pass

    @abstractmethod
    def get_data_stream(self) -> Iterator[DataPoint]:
        """Return an iterator that yields DataPoint objects"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up resources"""
        pass

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()


@dataclass
class EyeTrackingCSVAdapter(DataAdapter):
    """Adapter for reading eye tracking data from CSV files"""

    file_path: Path
    eye: str = "Left"
    scale_factor: float = 1.0
    clip_range: Optional[Tuple[float, float]] = None

    # Derived attributes
    x_column: str = field(init=False)
    y_column: str = field(init=False)
    subject_id: str = field(init=False)
    df: Optional[pd.DataFrame] = field(init=False, default=None)

    def __post_init__(self):
        """Initialize derived attributes"""
        self.file_path = Path(self.file_path)
        self.x_column = f"{self.eye}-X"
        self.y_column = f"{self.eye}-Y"

    def initialize(self, **kwargs) -> None:
        """Load the CSV file"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")

        # For CSV we use the filename as the subject_id if it's not set already
        self.subject_id = kwargs.get("subject_id", self.file_path.stem)

        # Read CSV with proper datetime parsing
        self.df = pd.read_csv(
            self.file_path,
            parse_dates=['Time'],
            date_format='ISO8601'
        )

        # Verify required columns exist
        required_columns = ['Time', self.x_column, self.y_column]
        missing_columns = [col for col in required_columns if col not in self.df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Remove duplicate timestamps if any
        self.df = self.df.drop_duplicates(subset=['Time'], keep='first')

        # Sort by time
        self.df = self.df.sort_values('Time')

        # Clamp values is clip_range is specified
        if self.clip_range is not None:
            self.df[self.x_column] = self.df[self.x_column].clip(*self.clip_range)
            self.df[self.y_column] = self.df[self.y_column].clip(*self.clip_range)

    def get_data_stream(self) -> Iterator[DataPoint]:
        """Yield data points from the CSV"""
        if self.df is None:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")

        for _, row in self.df.iterrows():
            # Skip rows with NaN values
            if pd.isna(row[self.x_column]) or pd.isna(row[self.y_column]):
                continue

            yield DataPoint(
                timestamp=row['Time'].to_pydatetime(),
                subject_id=self.subject_id,
                x=row[self.x_column] * self.scale_factor,
                y=row[self.y_column] * self.scale_factor,
                z=0.0  # Eye tracking is 2D
            )

    def close(self) -> None:
        """Clean up resources"""
        self.df = None


@dataclass
class LSLAdapter(DataAdapter):
    """Adapter for reading data from LSL (Lab Streaming Layer) streams"""

    stream_name: str
    eye: str = "Left"
    scale_factor: float = 1.0

    # LSL-specific attributes
    inlet: Any = field(init=False, default=None)
    stream_info: Any = field(init=False, default=None)
    x_index: int = field(init=False)
    y_index: int = field(init=False)

    def __post_init__(self):
        """Initialize column indices based on eye selection"""
        self.x_index = 2 if self.eye == "Left" else 4  # Left-X or Right-X
        self.y_index = 3 if self.eye == "Left" else 5  # Left-Y or Right-Y

    def initialize(self, timeout: float = 5.0, **kwargs) -> None:
        """Connect to LSL stream"""
        try:
            from pylsl import StreamInlet, resolve_stream
        except ImportError:
            raise ImportError("pylsl not installed. Install with: pip install pylsl")

        # Resolve the stream
        print(f"Looking for LSL stream '{self.stream_name}'...")
        streams = resolve_stream('name', self.stream_name, timeout=timeout)

        if not streams:
            raise RuntimeError(f"No LSL stream found with name '{self.stream_name}'")

        # Create inlet
        self.inlet = StreamInlet(streams[0])
        self.stream_info = self.inlet.info()
        print(f"Connected to stream: {self.stream_info.name()}")

    def get_data_stream(self) -> Iterator[DataPoint]:
        """Yield data points from the LSL stream"""
        if self.inlet is None:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")

        while True:
            # Pull sample from LSL
            sample, timestamp = self.inlet.pull_sample(timeout=1.0)

            if sample is None:
                continue

            # Convert LSL timestamp to datetime
            # LSL timestamps are seconds since Unix epoch
            dt = datetime.fromtimestamp(timestamp)

            try:
                yield DataPoint(
                    timestamp=dt,
                    subject_id=f"{self.eye}_eye",
                    x=sample[self.x_index] * self.scale_factor,
                    y=sample[self.y_index] * self.scale_factor,
                    z=0.0
                )
            except IndexError:
                print(f"Warning: Sample has unexpected format: {sample}")
                continue

    def close(self) -> None:
        """Close LSL connection"""
        if self.inlet:
            self.inlet.close_stream()
            self.inlet = None
