import os
import logging
import typing
import configparser

import qgis_plugin_tools
from qgis.PyQt.QtCore import Qt, QEvent
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtGui import QAction, QIcon
from qgis.core import QgsProject
from qgis.utils import iface as utils_iface
from qgis_plugin_tools.tools import custom_logging
from qgis_plugin_tools.tools.decorations import log_if_fails

import cerca_adreces_municipals_plugin
from cerca_adreces_municipals_plugin import env
from cerca_adreces_municipals_plugin.plugin_dialog import CercaAdrecesMunicipalsDockWidget

if typing.TYPE_CHECKING:
    from qgis.gui import QgisInterface

LOGGER = logging.getLogger(__name__)

iface = typing.cast("QgisInterface", utils_iface)


class CercaAdrecesMunicipals:
    """QGIS Plugin Implementation."""

    def __init__(self) -> None:
        self._teardown_loggers = lambda: None

        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action_name = '&CercaAdrecesMunicipals'
        self.toolbar = self.iface.addToolBar(self.action_name)
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

        img_folder = os.path.join(self.plugin_dir, "resources/icons")
        icon_path = os.path.join(img_folder, "CercaLocal.png")
        self.action = QAction(QIcon(icon_path), "Cerca Adreces Municipals", self.iface.mainWindow())
        self.action.setObjectName("CercaAdrecesMunicipals")
        self.action.setWhatsThis("Cerca Adreces Municipals")
        self.action.setStatusTip("Cerca Adreces Municipals")
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.action_name, self.action)

        self.ui = CercaAdrecesMunicipalsDockWidget(self.iface.mainWindow())
        self.iface.mainWindow().addDockWidget(Qt.LeftDockWidgetArea, self.ui)
        self.ui.Progres.hide()
        self.ui.setVisible(False)

        self.ui.Esborrar.setIcon(QIcon(os.path.join(img_folder, 'Paperera.png')))
        self.ui.Esborrar.clicked.connect(self.Esborrar)
        self.ui.Cercar.setIcon(QIcon(os.path.join(img_folder, 'CercaLocal.png')))
        self.ui.Cercar.clicked.connect(self.Search)

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
        self.ui.Esborrar.clicked.disconnect(self.Esborrar)
        self.ui.Cercar.clicked.disconnect(self.Search)
        del self.toolbar


    @log_if_fails
    def iface_initialization_completed(self) -> None:
        """Run additional setup for the plugin.

        Executed after initializationCompleted signal is emitted.
        """
        # TODO: Replace with actual functionality  # noqa: TD003
        # QMessageBox.information(
        #     iface.mainWindow(),
        #     "Message",
        #     "Hello world",
        # )


    def get_metadata_parameter(self, folder, section="general", parameter="version", file="metadata.txt"):
        """ Get parameter value from Metadata """

        # Check if metadata file exists
        metadata_file = os.path.join(folder, file)
        if not os.path.exists(metadata_file):
            self.Missatge(f"Couldn'f find metadata file: {metadata_file}")
            return None

        value = None
        try:
            metadata = configparser.ConfigParser()
            metadata.read(metadata_file)
            value = metadata.get(section, parameter)
        except Exception as e:
            self.Missatge(e)
        finally:
            return value


    def Missatge(self,av,t):
        """ Finestra missatges """

        m = QMessageBox()
        if av == "W":
            m.setIcon(QMessageBox.Warning)
            z = "Atenció"
        elif av == "C":
            m.setIcon(QMessageBox.Critical)
            z = "Error"
        else:
            m.setIcon(QMessageBox.Information)
            z = "Avís"
        m.setWindowTitle(z)
        m.setText(t)
        m.setStandardButtons(QMessageBox.Ok)
        b = m.button(QMessageBox.Ok)
        b.setText("Segueix")
        m.exec_()


    def Progress(self):
        """ Barra de progrés """

        if self.ui.Progres.value() > 99:
            self.ui.Progres.setValue(0)
        self.ui.Progres.setValue(self.ui.Progres.value() + 1)
        QCoreApplication.processEvents()


    def run(self):

        if self.ui and not self.ui.isVisible():
            self.ui.show()
        return


    def Esborrar(self):
        """ Esborrar capes creades """

        bas = QgsProject.instance().layerTreeRoot()
        grup = bas.findGroup("Cerca Local")
        if not grup is None:
            for fill in grup.children():
                id = fill.dump().split("=")[-1].strip()
                QgsProject.instance().removeMapLayer(id)
            bas.removeChildNode(grup)
        self.iface.mapCanvas().refresh()


    def eventFilter(self,o,e):
        """ Si Return/Enter fer cerca """

        if e.type() == QEvent.KeyPress:
            if e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter:
                self.Search()
        return False


    def Search(self):
        """ Fer cerca """

        self.ui.Progres.show()
        self.ui.Progres.setValue(10)
        self.Progress()

        # connect to API and perform search


        self.ui.Progres.hide()
