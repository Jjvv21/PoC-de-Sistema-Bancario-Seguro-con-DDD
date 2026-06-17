from __future__ import annotations
from app.domain.value_objects import EtiquetaConfidencialidad


class VerificadorBellLaPadula:
    """
    Domain Service: aplica la regla de confidencialidad Bell-LaPadula.
    No tiene estado propio — solo encapsula la lógica de validación
    que coordina el clearance del usuario con la clasificación del recurso.
    """

    def validar_lectura(
        self,
        clearance_usuario: EtiquetaConfidencialidad,
        clasificacion_activo: EtiquetaConfidencialidad,
    ) -> None:
        """
        No Read Up: lanza excepción si el usuario intenta leer
        un activo cuya clasificación supera su clearance.
        """
        if not clearance_usuario.puede_leer(clasificacion_activo):
            raise PermisoDenegadoError(
                f"Violación Bell-LaPadula: clearance '{clearance_usuario.nivel.value}' "
                f"no puede leer activos clasificados como '{clasificacion_activo.nivel.value}'"
            )


class PermisoDenegadoError(Exception):
    pass