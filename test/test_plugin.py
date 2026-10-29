from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from qgis.core import Qgis, QgsBlockingNetworkRequest, QgsRectangle
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


def test_run_shows_ui(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test that the run method makes the UI visible[cite: 3]."""
    # Force the UI to report that it is hidden[cite: 3]
    mocker.patch.object(plugin_loaded.ui, "isVisible", return_value=False)

    # Spy on the show method to see if it gets called[cite: 3]
    mock_show = mocker.patch.object(plugin_loaded.ui, "show")

    plugin_loaded.run()

    # Assert that plugin.run() successfully triggered the UI to show[cite: 3]
    mock_show.assert_called_once()


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

    plugin_loaded.do_search()

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

    mock_root.findGroup.assert_called_once_with("Cerca Adreces Municipals")
    mock_instance.removeMapLayer.assert_called_once_with("mock_id_123")
    mock_root.removeChildNode.assert_called_once_with(mock_group)


def test_get_metadata_parameter_success(
    plugin_loaded: "CercaAdrecesMunicipals", tmp_path: Path
) -> None:
    """Test get_metadata_parameter when the file exists and is valid[cite: 8]."""
    # Create a fake metadata.txt file in the temporary pytest directory[cite: 8]
    metadata_file = tmp_path / "metadata.txt"
    metadata_file.write_text("[general]\nversion=2.5.0\nname=Test Plugin")

    # Read the version parameter[cite: 8]
    version = plugin_loaded.get_metadata_parameter(tmp_path)
    assert version == "2.5.0"

    # Read the name parameter[cite: 8]
    name = plugin_loaded.get_metadata_parameter(tmp_path, parameter="name")
    assert name == "Test Plugin"


def test_do_search_empty_inputs(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test that do_search stops and shows a warning if all inputs are empty[cite: 8]."""
    # Mock the UI combo boxes to return empty strings[cite: 8]
    mocker.patch.object(plugin_loaded.ui.cb_poblacio, "currentText", return_value="")
    mocker.patch.object(plugin_loaded.ui.cb_carrer, "currentText", return_value="")
    mocker.patch.object(plugin_loaded.ui.cb_portal, "currentText", return_value="")

    # Spy on the messageBar to ensure it gets called[cite: 8]
    mock_push_message = mocker.patch.object(plugin_loaded.ui.messageBar, "pushMessage")

    plugin_loaded.do_search()

    mock_push_message.assert_called_once_with(
        "Warning",
        "Has de omplir al menys un camp.",
        level=Qgis.MessageLevel.Warning,
        duration=5,
    )


def test_do_search_no_results(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test that do_search shows a warning if the API returns no features[cite: 8]."""
    # Mock inputs so it passes the empty check[cite: 8]
    mocker.patch.object(
        plugin_loaded.ui.cb_poblacio, "currentText", return_value="Sabadell"
    )
    mocker.patch.object(plugin_loaded.ui.cb_carrer, "currentText", return_value="Major")
    mocker.patch.object(plugin_loaded.ui.cb_portal, "currentText", return_value="1")

    # Mock the API call to return an empty features list[cite: 8]
    mocker.patch.object(plugin_loaded, "get_json", return_value={"features": []})

    mock_push_message = mocker.patch.object(plugin_loaded.ui.messageBar, "pushMessage")

    plugin_loaded.do_search()

    mock_push_message.assert_called_once_with(
        "Warning",
        "Adreça Major 1,Sabadell no trobat",
        level=Qgis.MessageLevel.Warning,
        duration=5,
    )


def test_extract_bbox(plugin_loaded: "CercaAdrecesMunicipals") -> None:
    """Test the extraction of a bounding box from the addendum dictionary[cite: 8]."""
    properties = {"addendum": {"bbox": "2.819,41.982,2.822,41.983"}}

    # Call extract_bbox with no existing extent[cite: 8]
    result = plugin_loaded.extract_bbox(None, properties)

    assert isinstance(result, QgsRectangle)
    assert result.xMinimum() == 2.819
    assert result.yMinimum() == 41.982
    assert result.xMaximum() == 2.822
    assert result.yMaximum() == 41.983


def test_get_layer_group_and_create(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test retrieving and creating layer groups in the QgsProject[cite: 8]."""
    mock_project = mocker.patch("cerca_adreces_municipals_plugin.plugin.QgsProject")
    mock_instance = mock_project.instance.return_value
    mock_root = mock_instance.layerTreeRoot.return_value

    # Setup mock group for finding[cite: 8]
    mock_group = mocker.MagicMock()
    mock_group.name.return_value = "Test Group"
    mock_root.findGroups.return_value = [mock_group]

    # Test getting an existing group[cite: 8]
    result = plugin_loaded.get_layer_group("Test Group")
    assert result == mock_group

    # Test getting a non-existent group[cite: 8]
    result_none = plugin_loaded.get_layer_group("Missing Group")
    assert result_none is None

    # Test creating a group[cite: 8]
    mock_root.addGroup.return_value = mock_group
    created = plugin_loaded.create_group("New Group")
    mock_root.addGroup.assert_called_once_with("New Group")
    assert created == mock_group


def test_do_search_success(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test successful search pipeline triggering add_geojson_to_memory[cite: 9]."""
    mocker.patch.object(
        plugin_loaded.ui.cb_poblacio, "currentText", return_value="Sabadell"
    )
    mocker.patch.object(plugin_loaded.ui.cb_carrer, "currentText", return_value="Major")
    mocker.patch.object(plugin_loaded.ui.cb_portal, "currentText", return_value="1")

    # Mock get_json to return a valid fake GeoJSON response[cite: 9]
    fake_geojson = {"features": [{"properties": {"test": 1}}]}
    mocker.patch.object(plugin_loaded, "get_json", return_value=fake_geojson)

    # Spy on add_geojson_to_memory to ensure it gets called[cite: 9]
    mock_add_geojson = mocker.patch.object(plugin_loaded, "add_geojson_to_memory")

    plugin_loaded.do_search()

    mock_add_geojson.assert_called_once_with(fake_geojson, "Adreça Major 1,Sabadell")


def test_get_json_success(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test successful API network request and JSON decoding."""
    # Patch methods on the class instead of patching the whole class
    # so we don't accidentally overwrite the ErrorCode enums.
    mocker.patch.object(
        QgsBlockingNetworkRequest,
        "get",
        return_value=QgsBlockingNetworkRequest.ErrorCode.NoError,
    )

    # Construct the chained mock for reply.content().data().decode()
    mock_reply = mocker.MagicMock()
    mock_reply.attribute.return_value = 200

    mock_data = mocker.MagicMock()
    mock_data.decode.return_value = '{"features": [{"fake": "data"}]}'
    mock_reply.content.return_value.data = mocker.MagicMock(return_value=mock_data)

    mocker.patch.object(QgsBlockingNetworkRequest, "reply", return_value=mock_reply)

    result = plugin_loaded.get_json({"text": "Sabadell"})

    assert result == {"features": [{"fake": "data"}]}


def test_get_json_network_error(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test that get_json raises a RuntimeError on HTTP failure."""
    mocker.patch.object(
        QgsBlockingNetworkRequest,
        "get",
        return_value=QgsBlockingNetworkRequest.ErrorCode.TimeoutError,
    )
    mocker.patch.object(
        QgsBlockingNetworkRequest, "errorMessage", return_value="Connection timed out"
    )

    mock_reply = mocker.MagicMock()
    mock_reply.attribute.return_value = 408
    mocker.patch.object(QgsBlockingNetworkRequest, "reply", return_value=mock_reply)

    with pytest.raises(RuntimeError) as exc_info:
        plugin_loaded.get_json({"text": "test"})

    assert "HTTP 408: Connection timed out" in str(exc_info.value)


def test_add_geojson_to_memory_empty(plugin_loaded: "CercaAdrecesMunicipals") -> None:
    """Test layer creation aborts safely when no features are present[cite: 9]."""
    result = plugin_loaded.add_geojson_to_memory({"features": []})
    assert result is None


def test_add_geojson_to_memory_success(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test parsing a valid GeoJSON dictionary into QgsVectorLayer fields and features[cite: 9]."""
    geojson = {
        "features": [
            {
                "geometry": {"coordinates": [2.10, 41.54]},
                "properties": {
                    "int_field": 10,
                    "float_field": 15.5,
                    "str_field": "Test String",
                    "dict_field": {"nested": "value"},
                    "addendum": {"bbox": "2.1,41.5,2.2,41.6"},
                },
            }
        ]
    }

    # Block the actual addition to canvas to keep this test isolated[cite: 9]
    mock_add_layer = mocker.patch.object(plugin_loaded, "add_layer_to_canvas")

    layer = plugin_loaded.add_geojson_to_memory(geojson, "Test Output Layer")

    assert layer is not None
    assert layer.name() == "Test Output Layer"
    assert layer.isValid()
    assert layer.featureCount() == 1

    # Check if field types were parsed correctly[cite: 9]
    fields = layer.fields()
    assert fields.indexOf("int_field") != -1
    assert fields.indexOf("float_field") != -1
    assert fields.indexOf("str_field") != -1

    mock_add_layer.assert_called_once()


def test_add_layer_to_canvas(
    plugin_loaded: "CercaAdrecesMunicipals", mocker: "MockerFixture"
) -> None:
    """Test adding the vector layer to the QgsProject and map canvas extent handling[cite: 9]."""
    # Mock project, canvas, and iface to prevent QGIS UI crashes during tests[cite: 9]
    mock_project = mocker.patch("cerca_adreces_municipals_plugin.plugin.QgsProject")
    mock_instance = mock_project.instance.return_value

    mock_iface = mocker.patch("cerca_adreces_municipals_plugin.plugin.iface")
    mock_canvas = mock_iface.mapCanvas.return_value

    # Create fake layer and target extent[cite: 9]
    mock_layer = mocker.MagicMock()
    mock_layer.crs.return_value = "EPSG:4326"

    # Simulate matching CRSs to bypass the transform branch[cite: 9]
    mock_canvas.mapSettings().destinationCrs.return_value = "EPSG:4326"
    mock_extent = mocker.MagicMock()

    plugin_loaded.add_layer_to_canvas(mock_layer, mock_extent)

    # Verify canvas zoom and layer registration occurred[cite: 9]
    mock_instance.addMapLayer.assert_called_once_with(mock_layer, addToLegend=False)
    mock_extent.scale.assert_called_once_with(1.1)
    mock_canvas.setExtent.assert_called_once_with(mock_extent)
    mock_canvas.refresh.assert_called_once()
