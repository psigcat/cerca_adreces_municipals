from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from qgis.PyQt.QtWidgets import QMessageBox

from cerca_adreces_municipals_plugin import classFactory

if TYPE_CHECKING:
    from collections.abc import Iterator
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture
    from qgis.gui import QgisInterface

    from cerca_adreces_municipals_plugin.plugin import CercaAdrecesMunicipals


@pytest.fixture(autouse=True)
def mock_message_box_ok(mocker: "MockerFixture") -> "MagicMock":
    return mocker.patch.object(
        QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok
    )


@pytest.fixture
def plugin_loaded(qgis_iface: "QgisInterface") -> "Iterator[CercaAdrecesMunicipals]":
    plugin = classFactory(qgis_iface)
    plugin.initGui()

    yield plugin

    plugin.unload()


def test_plugin_loads_without_errors(
    mock_message_box_ok: "MagicMock", plugin_loaded: "CercaAdrecesMunicipals"
) -> None:
    mock_message_box_ok.assert_called_once()

    # TODO: assert components initialized etc.
    # assert plugin_loaded.toolbar is not None


def test_run_shows_ui(plugin_loaded: "CercaAdrecesMunicipals") -> None:
    """Test that the run method makes the UI visible[cite: 3]."""
    plugin_loaded.ui.setVisible(False)
    assert not plugin_loaded.ui.isVisible()

    plugin_loaded.run()
    assert plugin_loaded.ui.isVisible()


def test_update_progress_increment(plugin_loaded: "CercaAdrecesMunicipals") -> None:
    """Test progress bar increments normally[cite: 3]."""
    plugin_loaded.ui.progressBar.setValue(50)
    plugin_loaded.update_progress()
    assert plugin_loaded.ui.progressBar.value() == 51


def test_update_progress_rollover(plugin_loaded: "CercaAdrecesMunicipals") -> None:
    """Test progress bar resets to 0 when exceeding 99[cite: 3]."""
    plugin_loaded.ui.progressBar.setValue(100)
    plugin_loaded.update_progress()
    assert plugin_loaded.ui.progressBar.value() == 1


def test_search_shows_and_hides_progress(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test that the search method toggles the progress bar[cite: 3]."""
    mock_show = mocker.patch.object(plugin_loaded.ui.progressBar, "show")
    mock_hide = mocker.patch.object(plugin_loaded.ui.progressBar, "hide")

    plugin_loaded.search()

    mock_show.assert_called_once()
    mock_hide.assert_called_once()


def test_show_message_box(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test that show_message_box executes a QMessageBox without blocking[cite: 3]."""
    mock_exec = mocker.patch.object(QMessageBox, "exec")

    # Test Warning branch[cite: 3]
    plugin_loaded.show_message_box("W", "Test Warning")
    mock_exec.assert_called_once()

    # Test Critical branch[cite: 3]
    plugin_loaded.show_message_box("C", "Test Critical")
    assert mock_exec.call_count == 2

    # Test Default (Information) branch[cite: 3]
    plugin_loaded.show_message_box("I", "Test Info")
    assert mock_exec.call_count == 3


def test_get_metadata_parameter_missing_file(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture", tmp_path: Path
) -> None:
    """Test get_metadata_parameter when the file does not exist[cite: 3]."""
    mock_show_message = mocker.patch.object(plugin_loaded, "show_message_box")

    # Use tmp_path fixture from pytest to provide a safe, empty directory
    result = plugin_loaded.get_metadata_parameter(tmp_path, file="nonexistent.txt")

    assert result is None
    mock_show_message.assert_called_once_with(
        "W", f"Couldn'f find metadata file: {tmp_path / 'nonexistent.txt'}"
    )


def test_delete_layers(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test delete_layers logic by mocking the QgsProject instance[cite: 3]."""
    # Mock the QgsProject singleton to prevent actual QGIS project modification during tests
    mock_project = mocker.patch("cerca_adreces_municipals_plugin.plugin.QgsProject")
    mock_instance = mock_project.instance.return_value
    mock_root = mock_instance.layerTreeRoot.return_value
    mock_group = mock_root.findGroup.return_value

    # Provide a fake child layer to simulate deletion loop[cite: 3]
    mock_child = mocker.MagicMock()
    mock_child.dump.return_value = "layer_name = mock_id_123"
    mock_group.children.return_value = [mock_child]

    plugin_loaded.delete_layers()

    mock_root.findGroup.assert_called_once_with("Cerca Local")
    mock_instance.removeMapLayer.assert_called_once_with("mock_id_123")
    mock_root.removeChildNode.assert_called_once_with(mock_group)
