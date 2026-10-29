import configparser
import json
import logging
import typing
from pathlib import Path

import qgis_plugin_tools
from qgis.core import (
    Qgis,
    QgsBlockingNetworkRequest,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeedback,
    QgsField,
    QgsGeometry,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication, QMetaType, Qt, QUrl, QUrlQuery
from qgis.PyQt.QtGui import QAction, QIcon
from qgis.PyQt.QtNetwork import QNetworkRequest
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

API_URL = "https://eines.icgc.cat/geocodificador/autocompletar"
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
        plugin_name = self.get_metadata_parameter(self.plugin_dir, "general", "name")
        if plugin_name is None:
            self.plugin_name = "Cerca Adreces Municipals"
        else:
            self.plugin_name = plugin_name

    def initGui(self) -> None:  # noqa: N802
        """Init gui."""
        global iface  # noqa: PLW0602

        self._teardown_loggers = custom_logging.setup_loggers(
            cerca_adreces_municipals_plugin.__name__,
            qgis_plugin_tools.__name__,
            message_log_name=self.plugin_name,
        )

        if hasattr(iface, "initializationCompleted"):
            iface.initializationCompleted.connect(self.iface_initialization_completed)

        if bool(env.IS_DEVELOPMENT_MODE):
            self.iface_initialization_completed()

        img_folder = Path(self.plugin_dir) / "resources" / "icons"
        icon_path = Path(img_folder) / "CercaLocal.png"
        self.action = QAction(
            QIcon(str(icon_path)), self.plugin_name, self.iface.mainWindow()
        )
        self.action.setObjectName("CercaAdrecesMunicipals")
        self.action.setWhatsThis(self.plugin_name)
        self.action.setStatusTip(self.plugin_name)
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
        self.ui.searchButton.clicked.connect(self.do_search)

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
        self.ui.searchButton.clicked.disconnect(self.do_search)
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

        grup = bas.findGroup(self.plugin_name)
        if grup is not None:
            for fill in grup.children():
                layer_id = fill.dump().split(" = ")[-1].strip()
                instance.removeMapLayer(layer_id)
            bas.removeChildNode(grup)

        canvas = self.iface.mapCanvas()
        if canvas:
            canvas.refresh()

    def do_search(self) -> None:
        """Fer cerca."""
        self.ui.progressBar.show()
        self.ui.progressBar.setValue(10)
        self.update_progress()

        # connect to API and perform do_search
        poblacio: str = self.ui.cb_poblacio.currentText()
        carrer: str = self.ui.cb_carrer.currentText()
        portal: str = self.ui.cb_portal.currentText()

        if poblacio == "" and carrer == "" and portal == "":
            self.ui.messageBar.pushMessage(
                "Warning",
                "Has de omplir al menys un camp.",
                level=Qgis.MessageLevel.Warning,
                duration=5,
            )
            self.ui.progressBar.hide()
            return

        address_str = carrer + " " + portal + "," + poblacio
        address = self.get_json(
            {
                "text": address_str,
                "size": 1,
                "layers": "address",
            }
        )

        if len(address["features"]) == 0:
            self.ui.messageBar.pushMessage(
                "Warning",
                f"Adreça {address_str} no trobat",
                level=Qgis.MessageLevel.Warning,
                duration=5,
            )
        else:
            self.add_geojson_to_memory(address, "Adreça " + address_str)

        self.ui.progressBar.hide()

    def get_json(
        self,
        params: dict | None = None,
        authcfg: str | None = None,
        feedback: QgsFeedback | None = None,
    ) -> dict:
        """Get JSON from API."""
        self.update_progress()
        q = QUrl(API_URL)
        if params:
            query = QUrlQuery()
            for k, v in params.items():
                query.addQueryItem(k, str(v))
            q.setQuery(query)

        request = QNetworkRequest(q)
        request.setRawHeader(b"Accept", b"application/json")
        LOGGER.info("Geocodificador API amb %s", q.toString())

        blocking = QgsBlockingNetworkRequest()
        if authcfg:
            blocking.setAuthCfg(authcfg)
        code = blocking.get(request, False, feedback)
        reply = blocking.reply()
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        self.update_progress()

        if code != QgsBlockingNetworkRequest.ErrorCode.NoError:
            msg = f"HTTP {status}: {blocking.errorMessage()}"
            raise RuntimeError(msg)
        self.update_progress()
        return json.loads(reply.content().data().decode("utf-8"))

    def add_geojson_to_memory(
        self, geojson_dict: dict, layer_name: str = "Addresses"
    ) -> QgsVectorLayer | None:
        """Add JSON as memory layer to canvas."""
        self.update_progress()
        layer = QgsVectorLayer("Point?crs=epsg:4326", layer_name, "memory")
        provider = layer.dataProvider()

        if not geojson_dict.get("features"):
            return None

        # Setup attributes
        first_props = geojson_dict["features"][0]["properties"]
        fields = []

        for key, value in first_props.items():
            field = QgsField()  # ty: ignore[missing-argument, unused-ignore-comment]
            field.setName(key)

            if isinstance(value, int):
                field.setType(QMetaType.Type.Int)
            elif isinstance(value, float):
                field.setType(QMetaType.Type.Double)
            else:
                field.setType(QMetaType.Type.QString)

            fields.append(field)

        if provider is not None:
            provider.addAttributes(fields)
        layer.updateFields()

        # Parse features and extract the bbox
        qgs_features = []
        target_extent = None

        for feat_data in geojson_dict["features"]:
            feat = QgsFeature(layer.fields())

            # Build geometry
            coords = feat_data["geometry"]["coordinates"]
            geom = QgsGeometry.fromPointXY(QgsPointXY(coords[0], coords[1]))
            feat.setGeometry(geom)

            target_extent = self.extract_bbox(target_extent, feat_data["properties"])

            # Populate attributes
            for i, field in enumerate(layer.fields().toList()):
                self.update_progress()
                val = feat_data["properties"].get(field.name())
                if isinstance(val, (dict, list)):
                    val = json.dumps(val)
                feat.setAttribute(i, val)

            qgs_features.append(feat)

        if provider is not None:
            provider.addFeatures(qgs_features)
        layer.updateExtents()
        self.add_layer_to_canvas(layer, target_extent)

        return layer

    def extract_bbox(
        self, extent: QgsRectangle | None, properties: dict
    ) -> QgsRectangle | None:
        """Extract the bbox from the addendum dictionary."""
        self.update_progress()
        if extent is None and "addendum" in properties:
            addendum = properties["addendum"]
            if "bbox" in addendum:
                # Split "2.819,41.982,2.822,41.982" into floats
                xmin, ymin, xmax, ymax = map(float, addendum["bbox"].split(","))
                extent = QgsRectangle(xmin, ymin, xmax, ymax)

        return extent

    def add_layer_to_canvas(
        self, layer: QgsVectorLayer, target_extent: QgsRectangle | None
    ) -> None:
        """Add layer to map canvas and zoom to the extracted bounding box."""
        self.update_progress()
        instance = QgsProject.instance()
        if instance:
            instance.addMapLayer(layer, addToLegend=False)

            layer_group = self.get_layer_group(self.plugin_name)
            if layer_group is not None:
                layer_group = self.create_group(self.plugin_name)

            if layer_group is not None:
                layer_group.addChildNode(QgsLayerTreeLayer(layer))

        canvas = iface.mapCanvas()
        if target_extent and iface and canvas is not None and instance:
            # Check if project CRS matches the layer's EPSG:4326 or transform the bbox.
            canvas_crs = canvas.mapSettings().destinationCrs()
            if canvas_crs != layer.crs():
                transform = QgsCoordinateTransform()  # ty: ignore[missing-argument, unused-ignore-comment]
                transform.setSourceCrs(layer.crs())
                transform.setDestinationCrs(canvas_crs)
                transform.setContext(instance.transformContext())
                target_extent = transform.transformBoundingBox(target_extent)

            # Apply extent to canvas with a buffer so the point isn't touching the edge
            target_extent.scale(1.1)
            canvas.setExtent(target_extent)
            canvas.refresh()

    def get_layer_group(self, layer_group_name: str) -> QgsLayerTreeGroup | None:
        """Get layer group inside another group, false if it doesn't exist."""
        instance = QgsProject.instance()
        if instance is None:
            return None

        root = instance.layerTreeRoot()
        if root is None:
            return None

        for group in root.findGroups():
            if group.name() == layer_group_name:
                return group
        return None

    def create_group(self, group_name: str) -> QgsLayerTreeGroup | None:
        """Create layer group."""
        instance = QgsProject.instance()
        if instance is None:
            return None

        root = instance.layerTreeRoot()
        if root is None:
            return None

        return root.addGroup(group_name)
