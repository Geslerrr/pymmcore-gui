from __future__ import annotations

import json
from typing import TYPE_CHECKING

import h5py
import numpy as np
from useq import Channel, MDAEvent, MDASequence

from pymmcore_gui._hdf5_writer import HDF5MDAWriter
from pymmcore_gui._qt.QtWidgets import QWidget
from pymmcore_gui.actions.widget_actions import create_mda_widget

if TYPE_CHECKING:
    from pathlib import Path

    from pymmcore_plus import CMMCorePlus
    from pytest import MonkeyPatch
    from pytestqt.qtbot import QtBot


def _summary(shape: tuple[int, ...], dtype: str) -> dict:
    return {
        "image_infos": [
            {
                "camera_label": "Camera",
                "plane_shape": shape,
                "dtype": dtype,
            }
        ],
        "devices": [],
    }


def test_hdf5_writer_preserves_generic_mda_frames(tmp_path: Path) -> None:
    path = tmp_path / "time-series.h5"
    sequence = MDASequence(time_plan={"interval": 1, "loops": 2})
    writer = HDF5MDAWriter(path)
    writer.sequenceStarted(sequence, _summary((2, 3), "uint16"))

    expected = []
    for index in range(2):
        frame = np.full((2, 3), index + 7, dtype=np.uint16)
        expected.append(frame)
        writer.frameReady(
            frame,
            MDAEvent(index={"t": index}),
            {"runner_time_ms": index * 10, "exposure_ms": 1.0},
        )
    writer.sequenceFinished(sequence)

    with h5py.File(path, "r") as h5_file:
        data = h5_file["entry/data/frames"]
        assert data.shape == (2, 2, 3)
        assert data.dtype == np.dtype("uint16")
        np.testing.assert_array_equal(data[...], np.stack(expected))
        np.testing.assert_array_equal(h5_file["entry/data/valid"][...], [True, True])
        assert json.loads(data.attrs["axes"]) == ["t", "y", "x"]
        records = h5_file["entry/metadata/frame_records"]
        assert len(records) == 2
        assert json.loads(records[0])["metadata"]["exposure_ms"] == 1.0
        assert h5_file["entry"].attrs["status"] == "complete"


def test_hdf5_writer_stores_spectral_grid_and_stage_axes(tmp_path: Path) -> None:
    path = tmp_path / "spectral-map.h5"
    sequence = MDASequence(grid_plan={"rows": 2, "columns": 3})
    positions = list(sequence.grid_plan)
    writer = HDF5MDAWriter(path)
    writer.sequenceStarted(sequence, _summary((1, 4), "uint16"))

    expected = np.empty((2, 3, 4), dtype=np.uint16)
    for index, position in enumerate(positions):
        row, column = int(position.row), int(position.col)
        spectrum = np.array([[index, index + 1, index + 2, index + 3]], dtype=np.uint16)
        expected[row, column] = spectrum[0]
        event = MDAEvent(index={"g": index}, x_pos=position.x, y_pos=position.y)
        writer.frameReady(spectrum, event, {"runner_time_ms": index})
    writer.sequenceFinished(sequence)

    with h5py.File(path, "r") as h5_file:
        data = h5_file["entry/data/spectra"]
        assert data.shape == (2, 3, 4)
        assert data.dtype == np.dtype("uint16")
        np.testing.assert_array_equal(data[...], expected)
        assert json.loads(data.attrs["axes"]) == ["scan_y", "scan_x", "pixel"]
        np.testing.assert_array_equal(
            h5_file["entry/axes/scan_x_um"][...],
            [positions[column].x for column in range(3)],
        )
        np.testing.assert_array_equal(
            h5_file["entry/axes/scan_y_um"][...],
            [positions[row * 3].y for row in range(2)],
        )
        np.testing.assert_array_equal(
            h5_file["entry/axes/pixel"][...], np.arange(4, dtype=np.uint32)
        )
        assert h5_file["entry/axes/scan_x_um"].attrs["units"] == "um"
        assert h5_file["entry/axes/scan_y_um"].attrs["units"] == "um"
        assert np.all(h5_file["entry/data/valid"][...])
        first_record = json.loads(h5_file["entry/metadata/frame_records"][0])
        assert first_record["index"] == {"g": 0}
        assert first_record["event"]["x_pos"] == positions[0].x
        assert first_record["event"]["y_pos"] == positions[0].y


def test_hdf5_writer_marks_canceled_acquisition(tmp_path: Path) -> None:
    path = tmp_path / "canceled.h5"
    sequence = MDASequence()
    writer = HDF5MDAWriter(path)
    writer.sequenceStarted(sequence, _summary((1, 2), "uint16"))
    writer.sequenceCanceled(sequence)
    assert writer._file is None
    writer.sequenceFinished(sequence)

    with h5py.File(path, "r") as h5_file:
        assert h5_file["entry"].attrs["status"] == "canceled"


def test_hdf5_option_is_available_in_mda_save_widget(
    qtbot: QtBot,
) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    widget = create_mda_widget(parent)

    combo = widget.save_info._writer_combo
    assert combo.findText("hdf5") >= 0

    combo.setCurrentText("hdf5")
    widget.save_info.save_name.setText("spectral-map")
    widget.save_info.save_name.editingFinished.emit()
    assert widget.save_info.save_name.text() == "spectral-map.h5"


def test_mda_widget_routes_hdf5_output_to_writer(
    qtbot: QtBot,
    tmp_path: Path,
    mmcore: CMMCorePlus,
    monkeypatch: MonkeyPatch,
) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    widget = create_mda_widget(parent)
    widget.save_info.setChecked(True)
    widget.save_info._writer_combo.setCurrentText("hdf5")
    routed: list[object] = []
    monkeypatch.setattr(
        mmcore,
        "run_mda",
        lambda *args, **kwargs: routed.append(kwargs["output"]),
    )

    path = tmp_path / "routed.h5"
    widget.execute_mda(path)

    assert len(routed) == 1
    assert isinstance(routed[0], HDF5MDAWriter)
    assert routed[0].path == path


def test_hdf5_writer_with_demo_camera_mda(mmcore: CMMCorePlus, tmp_path: Path) -> None:
    path = tmp_path / "demo-acquisition.h5"
    sequence = MDASequence(channels=[Channel(config="FITC", exposure=1)])
    writer = HDF5MDAWriter(path)

    mmcore.run_mda(sequence, output=writer, block=True)

    with h5py.File(path, "r") as h5_file:
        data = h5_file["entry/data/frames"]
        assert data.shape == (1, 512, 512)
        assert data.dtype == np.dtype("uint16")
        assert len(h5_file["entry/metadata/frame_records"]) == 1
        assert h5_file["entry/data/valid"][...].all()
        assert json.loads(data.attrs["axes"]) == ["c", "y", "x"]
        assert h5_file["entry"].attrs["status"] == "complete"
