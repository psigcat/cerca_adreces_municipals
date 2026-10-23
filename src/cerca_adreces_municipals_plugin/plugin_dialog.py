from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt import uic

import os

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'plugin_dialog.ui'))


class CercaAdrecesMunicipalsDockWidget(QDockWidget, FORM_CLASS):  # noqa: D101

    def __init__(self, parent=None):

        """Constructor."""
        super(CercaAdrecesMunicipalsDockWidget, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
