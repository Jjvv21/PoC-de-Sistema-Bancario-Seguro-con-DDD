from __future__ import annotations

from app.domain.entities import ActivoInversion
from app.domain.services import VerificadorBellLaPadula, PermisoDenegadoError
from app.domain.value_objects import EtiquetaConfidencialidad, NivelClearance
from app.infrastructure.repository import ActivoInversionRepository


class ListarActivosUseCase:
    """
    Caso de uso: lista todos los activos de inversión.
    Valida Bell-LaPadula ANTES de tocar el repositorio —
    si el clearance es insuficiente, ni siquiera se consulta la BD.
    """

    def __init__(self, repository: ActivoInversionRepository) -> None:
        self._repository = repository
        self._verificador = VerificadorBellLaPadula()

    def ejecutar(self, clearance_usuario: EtiquetaConfidencialidad) -> list[ActivoInversion]:
        clasificacion_dominio = EtiquetaConfidencialidad(nivel=NivelClearance.ORO)
        self._verificador.validar_lectura(clearance_usuario, clasificacion_dominio)
        return self._repository.listar_todos()