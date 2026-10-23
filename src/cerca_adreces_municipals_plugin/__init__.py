
import typing
from qgis.utils import plugins


if typing.TYPE_CHECKING:
    from cerca_adreces_municipals_plugin.plugin import CercaAdrecesMunicipals


def classFactory(_) -> "CercaAdrecesMunicipals":  # noqa: ANN001, N802
    """Class factory."""
    from cerca_adreces_municipals_plugin.plugin import CercaAdrecesMunicipals  # noqa: PLC0415

    return CercaAdrecesMunicipals()


def get_instance() -> "CercaAdrecesMunicipals | None":
    """Get instance."""
    return plugins.get(__name__)
