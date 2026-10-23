import pytest
from qgis.core import QgsProject

"""
!!! IMPORTANT !!!
DO NOT import anything that imports qgis.utils.iface
(or some module that imports other module that imports it) in conftest root!
Importing those modules in fixtures is OK.

The same goes with cerca_adreces_municipals_plugin.env.py.
"""


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variables for tests."""
    monkeypatch.setenv("IS_DEVELOPMENT_MODE", "yes")


@pytest.fixture(autouse=True)
def _reset_session_state(
    qgis_new_project: None,
) -> None:
    if project_instance := QgsProject.instance():
        project_instance.clear()
