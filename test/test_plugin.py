from typing import TYPE_CHECKING

import pytest
from qgis.PyQt.QtWidgets import QMessageBox

from cerca_adreces_municipals_plugin import classFactory

if TYPE_CHECKING:
    from collections.abc import Iterator
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture
    from qgis.gui import QgisInterface

    from cerca_adreces_municipals_plugin.plugin import PainterPlugin


@pytest.fixture(autouse=True)
def mock_message_box_ok(mocker: "MockerFixture") -> "MagicMock":
    return mocker.patch.object(
        QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok
    )


@pytest.fixture
def plugin_loaded(qgis_iface: "QgisInterface") -> "Iterator[PainterPlugin]":
    plugin = classFactory(qgis_iface)
    plugin.initGui()

    yield plugin

    plugin.unload()


def test_plugin_loads_without_errors(
    mock_message_box_ok: "MagicMock", plugin_loaded: "PainterPlugin"
) -> None:
    mock_message_box_ok.assert_called_once()

    # TODO: assert components initialized etc.
    # assert plugin_loaded.toolbar is not None
