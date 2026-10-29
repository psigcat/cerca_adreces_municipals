import configparser
import logging
import typing
from pathlib import Path

import qgis_plugin_tools
from qgis.core import QgsProject
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtGui import QAction, QIcon
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.utils import iface as utils_iface
from qgis_plugin_tools.tools import custom_logging
from qgis_plugin_tools.tools.decorations import log_if_fails

import cerca_adreces_municipals_plugin
from cerca_adreces_municipals_plugin import env
from cerca_adreces_municipals_plugin.plugin_dialog import (
    CercaAdrecesMunicipalsDockWidget,
)

if typing.TYPE_CHECKING:
    from qgis.gui import QgisInterface

LOGGER = logging.getLogger(__name__)

iface = typing.cast("QgisInterface", utils_iface)


class CercaAdrecesMunicipals:
    """QGIS Plugin Implementation."""

    def __init__(self) -> None:
        self._teardown_loggers = lambda: None

        self.iface = iface
        self.plugin_dir = Path(__file__).parent
        self.action_name = "&CercaAdrecesMunicipals"
        self.toolbar = self.iface.addToolBar(self.action_name)
        if self.toolbar:
            self.toolbar.setObjectName(self.action_name)

    def initGui(self) -> None:  # noqa: N802
        """Init gui."""
        global iface  # noqa: PLW0602

        self._teardown_loggers = custom_logging.setup_loggers(
            cerca_adreces_municipals_plugin.__name__,
            qgis_plugin_tools.__name__,
            message_log_name="Cerca Adreces Municipals",
        )

        if hasattr(iface, "initializationCompleted"):
            iface.initializationCompleted.connect(self.iface_initialization_completed)

        if bool(env.IS_DEVELOPMENT_MODE):
            self.iface_initialization_completed()

        img_folder = Path(self.plugin_dir) / "resources" / "icons"
        icon_path = Path(img_folder) / "CercaLocal.png"
        self.action = QAction(
            QIcon(str(icon_path)), "Cerca Adreces Municipals", self.iface.mainWindow()
        )
        self.action.setObjectName("CercaAdrecesMunicipals")
        self.action.setWhatsThis("Cerca Adreces Municipals")
        self.action.setStatusTip("Cerca Adreces Municipals")
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.action_name, self.action)

        self.ui = CercaAdrecesMunicipalsDockWidget(self.iface.mainWindow())
        self.iface.mainWindow().addDockWidget(  # ty: ignore[unresolved-attribute]
            Qt.DockWidgetArea.LeftDockWidgetArea, self.ui
        )
        self.ui.progressBar.hide()
        self.ui.setVisible(False)

        self.ui.deleteButton.setIcon(QIcon(str(Path(img_folder) / "Paperera.png")))
        self.ui.deleteButton.clicked.connect(self.delete_layers)
        self.ui.searchButton.setIcon(QIcon(str(Path(img_folder) / "CercaLocal.png")))
        self.ui.searchButton.clicked.connect(self.search)

        # Get plugin version from metadata
        version = self.get_metadata_parameter(self.plugin_dir)
        self.ui.setWindowTitle(f"CercaAdrecesMunicipals {version}")

        LOGGER.info("Plugin initialized")

    def unload(self) -> None:
        """Unload plugin."""
        self._teardown_loggers()
        self._teardown_loggers = lambda: None

        self.iface.removePluginMenu(self.action_name, self.action)
        self.iface.removeToolBarIcon(self.action)
        self.ui.deleteButton.clicked.disconnect(self.delete_layers)
        self.ui.searchButton.clicked.disconnect(self.search)
        del self.toolbar

    @log_if_fails
    def iface_initialization_completed(self) -> None:
        """Run additional setup for the plugin.

        Executed after initializationCompleted signal is emitted.
        """
        # TODO: Replace with actual functionality  # noqa: TD003
        QMessageBox.information(
            iface.mainWindow(),
            "Message",
            "Hello world",
        )

    def get_metadata_parameter(
        self,
        folder: Path,
        section: str = "general",
        parameter: str = "version",
        file: str = "metadata.txt",
    ) -> str | None:
        """Get parameter value from Metadata."""
        # Check if metadata file exists
        metadata_file = Path(folder) / file
        if not Path.exists(metadata_file):
            self.show_message_box("W", f"Couldn'f find metadata file: {metadata_file}")
            return None

        value = None
        try:
            metadata = configparser.ConfigParser()
            metadata.read(metadata_file)
            value = metadata.get(section, parameter)
        except FileNotFoundError as e:
            self.show_message_box("C", str(e))

        return value

    def show_message_box(self, av: str, t: str) -> None:
        """Finestra show_message_boxs."""
        m = QMessageBox()
        if av == "W":
            m.setIcon(QMessageBox.Icon.Warning)
            z = "Atenció"
        elif av == "C":
            m.setIcon(QMessageBox.Icon.Critical)
            z = "Error"
        else:
            m.setIcon(QMessageBox.Icon.Information)
            z = "Avís"
        m.setWindowTitle(z)
        m.setText(t)
        m.setStandardButtons(QMessageBox.StandardButton.Ok)
        b = m.button(QMessageBox.StandardButton.Ok)
        if b:
            b.setText("Segueix")
        m.exec()

    def update_progress(self) -> None:
        """Barra de progrés."""
        max_progress = 99
        if self.ui.progressBar.value() > max_progress:
            self.ui.progressBar.setValue(0)
        self.ui.progressBar.setValue(self.ui.progressBar.value() + 1)
        QCoreApplication.processEvents()

    def run(self) -> None:
        """Run method."""
        if self.ui and not self.ui.isVisible():
            self.ui.show()

    def delete_layers(self) -> None:
        """Delete capes creades."""
        instance = QgsProject.instance()
        if instance is None:
            return

        bas = instance.layerTreeRoot()
        if bas is None:
            return

        grup = bas.findGroup("Cerca Local")
        if grup is not None:
            for fill in grup.children():
                layer_id = fill.dump().split(" = ")[-1].strip()
                instance.removeMapLayer(layer_id)
            bas.removeChildNode(grup)

        canvas = self.iface.mapCanvas()
        if canvas:
            canvas.refresh()

    def search(self) -> None:
        """Fer cerca."""
        self.ui.progressBar.show()
        self.ui.progressBar.setValue(10)
        self.update_progress()

        # connect to API and perform search

        self.ui.progressBar.hide()
