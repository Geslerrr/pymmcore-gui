from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import h5py
import numpy as np

if TYPE_CHECKING:
    from useq import MDAEvent, MDASequence


class HDF5MDAWriter:
    """Incrementally write MDA frames and metadata to one HDF5 file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._file: h5py.File | None = None
        self._data: h5py.Dataset | None = None
        self._valid: h5py.Dataset | None = None
        self._records: h5py.Dataset | None = None
        self._sequence_axes: tuple[str, ...] = ()
        self._grid_map: dict[int, tuple[int, int]] = {}
        self._is_spectral_grid = False
        self._x_coords: h5py.Dataset | None = None
        self._y_coords: h5py.Dataset | None = None

    def sequenceStarted(self, sequence: MDASequence, metadata: dict) -> None:
        """Create datasets from the sequence shape and camera summary metadata."""
        image_info = metadata["image_infos"][0]
        frame_shape = tuple(int(x) for x in image_info["plane_shape"])
        dtype = np.dtype(image_info["dtype"])

        sizes = sequence.sizes
        axes = tuple(
            str(axis)
            for axis in sequence.axis_order
            if int(sizes.get(str(axis), 0)) > 0
        )
        axis_sizes = {str(axis): int(size) for axis, size in sizes.items() if size > 0}
        self._sequence_axes = axes

        self.path.parent.mkdir(parents=True, exist_ok=True)
        h5_file = h5py.File(self.path, "x")
        self._file = h5_file
        entry = h5_file.create_group("entry")
        entry.attrs["schema"] = "pymmcore-gui-mda-hdf5"
        entry.attrs["schema_version"] = "1.0"
        entry.attrs["status"] = "acquiring"

        metadata_group = entry.create_group("metadata")
        metadata_group.create_dataset(
            "summary_json",
            data=json.dumps(metadata, default=_json_default),
            dtype=h5py.string_dtype("utf-8"),
        )
        self._records = metadata_group.create_dataset(
            "frame_records",
            shape=(0,),
            maxshape=(None,),
            chunks=(128,),
            dtype=h5py.string_dtype("utf-8"),
        )

        data_group = entry.create_group("data")
        map_axes: tuple[str, ...] = ()
        shape_axes = axes
        shape = tuple(axis_sizes[axis] for axis in axes) + frame_shape
        valid_shape = tuple(axis_sizes[axis] for axis in axes)

        grid_plan = sequence.grid_plan
        if (
            grid_plan is not None
            and len(frame_shape) == 2
            and frame_shape[0] == 1
            and "g" in axes
        ):
            grid_positions = list(grid_plan)
            if grid_positions and all(
                pos.row is not None and pos.col is not None for pos in grid_positions
            ):
                n_rows = max(int(pos.row) for pos in grid_positions) + 1
                n_columns = max(int(pos.col) for pos in grid_positions) + 1
                self._grid_map = {
                    index: (int(pos.row), int(pos.col))
                    for index, pos in enumerate(grid_positions)
                }
                shape_axes = tuple(
                    replacement
                    for axis in axes
                    for replacement in (
                        ("scan_y", "scan_x") if axis == "g" else (axis,)
                    )
                )
                shape = (
                    *tuple(
                        size
                        for axis in axes
                        for size in (
                            (n_rows, n_columns) if axis == "g" else (axis_sizes[axis],)
                        )
                    ),
                    frame_shape[-1],
                )
                valid_shape = tuple(shape[: len(shape_axes)])
                map_axes = (
                    *tuple(
                        replacement
                        for axis in axes
                        for replacement in (
                            ("scan_y", "scan_x") if axis == "g" else (axis,)
                        )
                    ),
                    "pixel",
                )
                self._is_spectral_grid = True

                axes_group = entry.create_group("axes")
                pixel_axis = axes_group.create_dataset(
                    "pixel", data=np.arange(frame_shape[-1], dtype=np.uint32)
                )
                pixel_axis.attrs["units"] = "pixel"
                x_coords = axes_group.create_dataset(
                    "scan_x_um", shape=(n_columns,), dtype=np.float64, fillvalue=np.nan
                )
                y_coords = axes_group.create_dataset(
                    "scan_y_um", shape=(n_rows,), dtype=np.float64, fillvalue=np.nan
                )
                self._x_coords = x_coords
                self._y_coords = y_coords
                x_coords.attrs["units"] = "um"
                y_coords.attrs["units"] = "um"

        chunks = tuple(1 for _ in shape_axes) + shape[len(shape_axes) :]
        data = data_group.create_dataset(
            "spectra" if self._is_spectral_grid else "frames",
            shape=shape,
            dtype=dtype,
            chunks=chunks or None,
            fillvalue=0,
        )
        self._data = data
        self._valid = data_group.create_dataset(
            "valid",
            shape=valid_shape,
            dtype=np.bool_,
            chunks=tuple(1 for _ in valid_shape) or None,
            fillvalue=False,
        )
        frame_axes = (
            ("y", "pixel")
            if len(frame_shape) == 2 and frame_shape[0] == 1
            else ("y", "x")
            if len(frame_shape) == 2
            else ("y", "x", "component")
        )
        data.attrs["axes"] = json.dumps(map_axes or (*shape_axes, *frame_axes))
        data.attrs["camera_label"] = str(image_info.get("camera_label", ""))

    def frameReady(self, image: np.ndarray, event: MDAEvent, metadata: dict) -> None:
        """Write one frame at the sequence index reported by the MDA event."""
        h5_file = self._file
        data = self._data
        valid = self._valid
        records = self._records
        if h5_file is None or data is None or valid is None or records is None:
            raise RuntimeError("HDF5 writer received a frame before sequenceStarted")

        frame = np.asarray(image)
        if self._is_spectral_grid:
            grid_index = int(event.index["g"])
            row, column = self._grid_map[grid_index]
            data_index = tuple(
                idx
                for axis in self._sequence_axes
                for idx in (
                    (row, column) if axis == "g" else (int(event.index.get(axis, 0)),)
                )
            )
            data[data_index] = frame.reshape(-1)
            valid[data_index] = True
            x_coords = self._x_coords
            y_coords = self._y_coords
            if x_coords is not None and event.x_pos is not None:
                x_coords[column] = event.x_pos
            if y_coords is not None and event.y_pos is not None:
                y_coords[row] = event.y_pos
        else:
            data_index = tuple(
                int(event.index.get(axis, 0)) for axis in self._sequence_axes
            )
            data[data_index] = frame
            valid[data_index] = True

        record = {"index": dict(event.index), "event": event, "metadata": metadata}
        records.resize((len(records) + 1,))
        records[-1] = json.dumps(record, default=_json_default)

    def sequenceCanceled(self, sequence: MDASequence) -> None:
        """Mark canceled acquisitions in the HDF5 metadata."""
        self._close_file(status="canceled")

    def sequenceFinished(self, sequence: MDASequence) -> None:
        """Flush and close the file after the last frame has been delivered."""
        self._close_file()

    def _close_file(self, status: str | None = None) -> None:
        """Flush, annotate, and close the active file if one exists."""
        h5_file = self._file
        if h5_file is not None:
            if status is not None:
                h5_file["entry"].attrs["status"] = status
            elif h5_file["entry"].attrs["status"] == "acquiring":
                h5_file["entry"].attrs["status"] = "complete"
            h5_file.flush()
            h5_file.close()
            self._file = None
            self._data = None
            self._valid = None
            self._records = None


def _json_default(value: Any) -> Any:
    """Convert common NumPy and useq metadata values to JSON-compatible values."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return str(value)
