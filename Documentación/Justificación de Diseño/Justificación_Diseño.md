# Justificación de Diseño DDD

Documento que explica las decisiones de diseño Domain-Driven Design (DDD) para los tres microservicios del sistema. Detalla por qué ciertos elementos son **Value Objects**, por qué otros son **Entities**, y cómo se estructura cada Aggregate.

---

## Índice

1. [IAM-Service](#iam-service)
2. [Banking-Service](#banking-service)
3. [Investments-Service](#investments-service)
4. [Síntesis Comparativa](#síntesis-comparativa)

---

## IAM-Service

### Contexto

**Responsabilidad**: Gestión de identidad y acceso. Emitir JWT con etiquetas de seguridad (Bell-LaPadula + Biba) que otros dominios confían sin cuestionamiento.

### Estructura de Agregado

```
Agregado: Usuario (Aggregate Root)
├── Entity: Usuario 
├── VO: Credenciales
├── VO: NivelSeguridad
│   ├── Enum VO: ClearanceLevel
│   └── Enum VO: IntegrityLevel
└── Service: TokenService
```

---

### Decisiones de Diseño

#### **1. ¿Por qué `Usuario` es una Entity (Aggregate Root)?**

| Criterio | Justificación |
|----------|---------------|
| **Identidad única** | Tiene `id: UUID` que persiste aunque todos sus atributos cambien |
| **Ciclo de vida independiente** | Se crea, se modifica (desactivar, cambiar nivel), se elimina |
| **Igualdad por identidad** | Dos usuarios son iguales si tienen el mismo UUID, no por sus credenciales |
| **Trazabilidad** | Necesitamos auditar quién es cada usuario a lo largo del tiempo |
| **Responsabilidad clara** | Es el guardián del acceso a Credenciales y NivelSeguridad |

**Código de prueba**:
```python
usuario1 = Usuario(id=uuid1, credenciales=creds_A, nivel=nivel_oro)
usuario2 = Usuario(id=uuid1, credenciales=creds_B, nivel=nivel_plata)

# Son el MISMO usuario. La identidad lo define, no los atributos
assert usuario1 == usuario2  # True
```

---

#### **2. ¿Por qué `Credenciales` es un Value Object?**

| Criterio | Justificación |
|----------|---------------|
| **Sin identidad única** | No importa "qué" credencial, solo su contenido (username + hash) |
| **Inmutabilidad** | Nunca se modifica in-place; cambiar credenciales = crear nuevas |
| **Igualdad por valor** | Dos sets de credenciales son iguales si tienen mismo username + hash |
| **No ciclo de vida propio** | Solo existe como parte de Usuario; no se persiste/consulta independientemente |
| **Reutilizable** | Podría usarse en otros agregados sin problemas |

**Razón NO es Entity**:
- Si tuviéramos `id: UUID` para cada credencial, NO sería viable — nunca consultas por "credencial#12345", siempre por usuario
- El historial de cambios de credenciales pertenece al audit de Usuario, no a Credenciales

**Código**:
```python
cred1 = Credenciales(username="alice", hashed_password="...")
cred2 = Credenciales(username="alice", hashed_password="...")

assert cred1 == cred2  # True (igualdad por valor)

# No se puede hacer cred1.username = "juan" 
# Se debe crear nueva instancia
```

---

#### **3. ¿Por qué `NivelSeguridad` es un Value Object?**

| Criterio | Justificación |
|----------|---------------|
| **Sin identidad** | "Oro" es "Oro" en cualquier contexto; no hay "Oro#1" vs "Oro#2" |
| **Inmutabilidad crítica** | Las etiquetas de seguridad NUNCA deben cambiar in-place |
| **Comparabilidad** | Necesitamos comparar: `clearance >= clasificacion_objeto` |
| **Comportamiento autónomo** | Encapsula lógica Biba/Bell-LaPadula (`puede_leer`, `puede_escribir`) |
| **Composición de enums** | Es una combinación de dos conceptos relacionados (clearance + integrity) |

**Razón NO es Entity**:
- No hay timestamps de cuándo se asignó — es un valor que existe eternamente
- No consultamos "dame la entidad NivelSeguridad con id=123" — consultamos "dame el usuario de Alice"
- Es compartible entre múltiples usuarios sin confusión

**Código**:
```python
nivel_oro = NivelSeguridad(clearance=ClearanceLevel.ORO, integrity=IntegrityLevel.ALTO)

# Validar Bell-LaPadula
sujeto_clearance = NivelSeguridad(clearance=ClearanceLevel.PLATA, ...)
objeto_clasificacion = NivelSeguridad(clearance=ClearanceLevel.ORO, ...)

# Comprobación: puede el sujeto leer?
puede = sujeto_clearance.puede_leer(objeto_clasificacion)  # False (PLATA < ORO)
```

---

#### **4. ¿Por qué `ClearanceLevel` e `IntegrityLevel` son Enums?**

| Criterio | Justificación |
|----------|---------------|
| **Conjunto finito y predefinido** | Siempre BRONCE, PLATA, ORO — nunca habrá "DIAMANTE" sin código |
| **Sin estado** | Son constantes; no cambian durante la ejecución |
| **Ordenables** | Tienen significado: BRONCE < PLATA < ORO |
| **Type-safe** | El compilador/IDE rechaza `ClearanceLevel.INVALIDO` antes de ejecutar |

---

#### **5. ¿Por qué `TokenService` es un Domain Service?**

| Criterio | Justificación |
|----------|---------------|
| **No tiene identidad** | No es "TokenService#1" vs "TokenService#2" |
| **No tiene estado** | Stateless; solo coordina operaciones criptográficas |
| **Coordina entre objetos** | Toma un Usuario y emite su JWT — transversal |
| **Lógica que pertenece al dominio** | Pero NO al Aggregate (no es responsabilidad de Usuario emitir tokens) |

**Razón NO es Entity**:
- Un Usuario no "tiene" un TokenService
- Un TokenService puede servir a múltiples usuarios simultáneamente

**Razón NO es Value Object**:
- Aunque no tiene identidad, SÍ tiene comportamiento con estado criptográfico (secret_key, algorithm)
- No es "inmutable" en el sentido de que representa un valor; es un coordinador
---

## Banking-Service

### Contexto

**Responsabilidad**: Core bancario. Gestionar cuentas, transacciones, validar integridad (Biba) y mantener auditoría inmutable de cada movimiento.

### Estructura de Agregado

```
Agregado: CuentaBancaria (Aggregate Root)
├── Entity: CuentaBancaria 
├── Entity: Transaccion  (entidad interna, no root)
├── VO: Dinero
├── VO: EtiquetaSeguridad
│   └── Enum VO: IntegrityLevel
├── Enum VO: TipoTransaccion
├── Enum VO: EstadoTransaccion
├── Enum VO: Moneda
├── VO: ResultadoTransferencia
└── Service: ProcesadorTransferencias
```

---

### Decisiones de Diseño

#### **1. ¿Por qué `CuentaBancaria` es una Entity (Aggregate Root)?**

| Criterio | Justificación |
|----------|---------------|
| **Identidad única** | `id: UUID` que representa esa cuenta específica — referencia única en el sistema |
| **Ciclo de vida** | Se abre, recibe operaciones, se cierra — tiene historia |
| **Responsabilidad central** | Guardiana del saldo y del historial de transacciones |
| **Autoridad sobre sus datos** | Nadie puede modificar su saldo directamente; solo a través de `depositar()` o `retirar()` |
| **Asociación con sujeto real** | Pertenece a un `titular_id` (usuario del sistema) — identidad de negocio |

**Código de prueba**:
```python
cuenta_origen = CuentaBancaria(id=uuid_x, titular_id=usuario_alice, saldo=Dinero(1000, CRC))
cuenta_copia = CuentaBancaria(id=uuid_x, titular_id=usuario_bob, saldo=Dinero(500, CRC))

# Son la MISMA cuenta. El UUID lo define
assert cuenta_origen == cuenta_copia  # True

# El saldo, titular y titular_id no definen la igualdad, solo el ID
```

---

#### **2. ¿Por qué `Transaccion` es una Entity (pero NO Root)?**

| Criterio | Justificación |
|----------|---------------|
| **Identidad única** | `id: UUID` — cada transacción es un evento irrepetible en el tiempo |
| **Inmutabilidad** | Una vez creada, NUNCA se modifica — es un registro de auditoría |
| **Timestamp único** | Cada transacción ocurre en un momento específico del tiempo |
| **Contenedora de eventos** | Es el rastro de qué pasó: quién, qué, cuándo, con qué estado |

**PERO no es Aggregate Root porque**:
- Nunca se accede directamente: no consultas "dame Transaccion#123"
- Siempre se accede a través de CuentaBancaria: "dame el historial de la cuenta"
- No tiene responsabilidad sobre otras entidades
- Su ciclo de vida está ligado 100% a su CuentaBancaria

**Razón NO es Value Object**:
- Tiene identidad única (UUID) — dos transacciones diferentes aunque tengan mismo monto/tipo
- Tiene timestamp — es un evento en el tiempo, no un valor abstracto
- No es intercambiable — "la transacción del 2026-06-18 a las 10:30" es específica

**Código**:
```python
txn1 = Transaccion(id=uuid_a, monto=Dinero(100, CRC), timestamp=2026-06-18 10:30)
txn2 = Transaccion(id=uuid_b, monto=Dinero(100, CRC), timestamp=2026-06-18 10:30)

# SON DIFERENTES. Aunque el monto y timestamp sean iguales
assert txn1 != txn2  # True

# Una transacción nunca se modifica:
# txn1.estado = RECHAZADA  # ERROR
```

---

#### **3. ¿Por qué `Dinero` es un Value Object?**

| Criterio | Justificación |
|----------|---------------|
| **Sin identidad** | "100 CRC" es "100 CRC" — no hay "100 CRC#1" vs "100 CRC#2" |
| **Igualdad por valor** | Dos instancias con monto=100 y moneda=CRC son idénticas |
| **Inmutabilidad** | No puedes hacer `dinero.monto = 200`; debes crear nueva instancia |
| **Operaciones cerradas** | `sumar()`, `restar()`, `es_mayor_o_igual()` retornan nuevas instancias |
| **Tipo-seguro** | Encapsula la validación: no permitas Dinero negativo |
| **Usa Decimal, no float** | Previene errores de redondeo en dinero real |

**Razón NO es Entity**:
- No tiene ciclo de vida — existe solo como valor
- No necesita tracking en BD — se serializa como dos columnas (monto, moneda)
- Es un patrón de negocio: "dinero es un concepto sin identidad"

**Código**:
```python
dinero1 = Dinero(monto=Decimal("100.50"), moneda=Moneda.CRC)
dinero2 = Dinero(monto=Decimal("100.50"), moneda=Moneda.CRC)

assert dinero1 == dinero2  # True (igualdad por valor)

# Operaciones retornan nuevas instancias (inmutable)
dinero3 = dinero1.sumar(dinero2)  # Dinero(201.00, CRC)
assert dinero1.monto == Decimal("100.50")  # Sin cambios

# Type-safe:
try:
    dinero_invalido = Dinero(monto=Decimal("-50"), moneda=Moneda.CRC)
except ValueError:
    print("No se permite dinero negativo")
```

---

#### **4. ¿Por qué `EtiquetaSeguridad` es un Value Object?**

| Criterio | Justificación |
|----------|---------------|
| **Sin identidad** | "ALTO" es "ALTO" — no hay "ALTO#1" vs "ALTO#2" |
| **Concepto puro** | Representa un nivel de seguridad, no una "cosa del mundo real" |
| **Comparable** | Necesitamos: `proceso.integrity >= cuenta.integrity` (Biba) |
| **Inmutable** | Las etiquetas de seguridad NUNCA cambian in-place |
| **Reutilizable** | Misma lógica en Banking (Biba) y en Investments (Bell-LaPadula) |

**Razón NO es Entity**:
- No tiene ciclo de vida independiente
- No se persiste con ID — es un enum + metadata

---

#### **5. ¿Por qué `ResultadoTransferencia` es un Value Object?**

| Criterio | Justificación |
|----------|---------------|
| **Inmutable** | Una vez creada, encapsula el resultado final — no cambia |
| **Sin identidad** | No es "ResultadoTransferencia#123"; es el resultado de una operación |
| **Composición de datos** | Agrupa campos relacionados: exitosa, transacciones, mensaje |
| **Reutilizable** | Cualquier caller puede crear instancias |

**Razón es VO, no Entity**:
- No tiene ID
- No persiste en BD independientemente
- Es un DTO de salida mejorado — empieza en el Domain, no en la capa de aplicación

---

#### **6. ¿Por qué `TipoTransaccion`, `EstadoTransaccion`, `Moneda` son Enums?**

| Criterio | Justificación |
|----------|---------------|
| **Dominios cerrados** | No habrá nuevos tipos/estados sin cambio de código |
| **Type-safe** | `TipoTransaccion.DEPOSITO` vs string `"deposito"` sin riesgo de typos |
| **Comparables** | `if estado == EstadoTransaccion.EXITOSA` es más seguro que strings |

---

#### **7. ¿Por qué `ProcesadorTransferencias` es un Domain Service?**

| Criterio | Justificación |
|----------|---------------|
| **Orquesta entre agregados** | Coordina `cuenta_origen.retirar()` + `cuenta_destino.depositar()` |
| **Sin estado propio** | Stateless; no almacena datos de transferencias |
| **Sin identidad** | No hay "ProcesadorTransferencias#1" |
| **Lógica compleja** | Encapsula la atomicidad: si retiro falla, no toca destino |
| **No pertenece a un Aggregate** | Un Usuario no "tiene" un ProcesadorTransferencias |

**Razón NO es Entity**:
- No tiene ciclo de vida
- No se persiste

**Razón NO es Value Object**:
- Aunque no tiene identidad, tiene métodos con efectos secundarios (modificar cuentas)
- No es "intercambiable por valor" — es un coordinador específico de negocio
---

## Investments-Service

### Contexto

**Responsabilidad**: Gestión de activos de inversión de alto valor. Control de confidencialidad estricto (Bell-LaPadula). Solo lectura — no hay modificaciones ni historial de transacciones.

### Estructura de Agregado

```
Agregado: ActivoInversion (Aggregate Root)
├── Entity: ActivoInversion 
├── VO: EtiquetaConfidencialidad
│   └── Enum VO: NivelClearance
└── Service: VerificadorBellLaPadula
```

---

### Decisiones de Diseño

#### **1. ¿Por qué `ActivoInversion` es una Entity (Aggregate Root)?**

| Criterio | Justificación |
|----------|---------------|
| **Identidad única** | `id: UUID` — representa ese activo específico (ej. "Fondo Oro #001") |
| **Referencia en el sistema** | Otros dominios harán referencias a activos por ID |
| **Ciclo de vida** | Se crea (se incluye en el catálogo), se puede dar de baja |
| **Valor significativo** | Cada activo tiene valor financiero único — no son intercambiables |
| **Clasificación persistente** | Siempre ORO — es característica inmutable del activo |

**Código de prueba**:
```python
activo1 = ActivoInversion(id=uuid_x, nombre="Fondo Oro A", valor=Decimal("1000000"), clasificacion=ORO)
activo2 = ActivoInversion(id=uuid_x, nombre="Fondo Plata", valor=Decimal("500000"), clasificacion=PLATA)

# Son el MISMO activo. El ID define la identidad
assert activo1 == activo2  # True

# Aunque nombre, valor y clasificación difieran, la identidad es el ID
```

---

#### **2. ¿Por qué `EtiquetaConfidencialidad` es un Value Object?**

| Criterio | Justificación |
|----------|---------------|
| **Sin identidad** | "ORO" es "ORO" — no hay "ORO clasificación A" vs "ORO clasificación B" |
| **Comparabilidad** | Necesitamos: `usuario.clearance >= activo.clasificacion` (Bell-LaPadula) |
| **Inmutabilidad** | Una vez asignada a un activo, NUNCA cambia |
| **Composición conceptual** | Agrupa el concepto de "nivel de confidencialidad" |
| **Reutilizable** | Misma lógica en Banking (Biba) y aquí (Bell-LaPadula) |

**Razón NO es Entity**:
- No tiene ciclo de vida propio
- No se consulta directamente
- No tiene timestamps de creación/modificación
- Es un concepto abstracto, no una cosa del mundo real

**Código**:
```python
etiqueta_oro = EtiquetaConfidencialidad(nivel=NivelClearance.ORO)

# Validar Bell-LaPadula
usuario_clearance = EtiquetaConfidencialidad(nivel=NivelClearance.PLATA)
activo_clasificacion = EtiquetaConfidencialidad(nivel=NivelClearance.ORO)

# El usuario puede leer?
puede = usuario_clearance.puede_leer(activo_clasificacion)  # False (PLATA < ORO)
```

---

#### **3. ¿Por qué `NivelClearance` es un Enum?**

| Criterio | Justificación |
|----------|---------------|
| **Dominios finitos** | BRONCE, PLATA, ORO — constante para el negocio |
| **Ordenables** | 1 < 2 < 3 — comparables para Bell-LaPadula |
| **Type-safe** | Rechaza `NivelClearance.INVALIDO` en tiempo de compilación |

---

#### **4. ¿Por qué `VerificadorBellLaPadula` es un Domain Service?**

| Criterio | Justificación |
|----------|---------------|
| **Valida regla de seguridad** | Encapsula la lógica: "No Read Up" |
| **Stateless** | No almacena estado — solo ejecuta validación |
| **Sin identidad** | No hay "VerificadorBellLaPadula#1" |
| **Coordinador de política** | Toma decisiones de acceso entre sujeto (usuario) y objeto (activo) |

**Razón NO es Entity**:
- No tiene ciclo de vida
- No se persiste
- No se consulta por ID

**Razón NO es Value Object**:
- Tiene comportamiento con lógica de seguridad — no es un "valor"
- Es un guardián de política de dominio

---

## Síntesis Comparativa

### Tabla resumen

| Elemento | IAM | Banking | Investments | Razón |
|----------|-----|---------|-------------|-------|
| **Entities** | Usuario | CuentaBancaria, Transaccion | ActivoInversion | Tienen identidad única + ciclo de vida |
| **Aggregate Roots** | 1 (Usuario) | 1 (CuentaBancaria) | 1 (ActivoInversion) | Punto de entrada único al agregado |
| **Value Objects** | Credenciales, NivelSeguridad | Dinero, EtiquetaSeguridad, ResultadoTransferencia | EtiquetaConfidencialidad | Sin identidad, inmutables, intercambiables |
| **Enums** | ClearanceLevel, IntegrityLevel | TipoTransaccion, EstadoTransaccion, Moneda, IntegrityLevel | NivelClearance | Dominios finitos, type-safe |
| **Domain Services** | TokenService | ProcesadorTransferencias | VerificadorBellLaPadula | Coordinadores de lógica compleja |

---

### Matriz de decisiones

```
┌─────────────────────────────────┬────────────┬─────────────┬──────────┐
│ Consideraciones                 │ ¿Entity?   │ ¿VO?        │ ¿Service?│
├─────────────────────────────────┼────────────┼─────────────┼──────────┤
│ ¿Tiene identidad única?         │ SÍ         │ NO          │ NO       │
│ ¿Tiene ciclo de vida?           │ SÍ         │ NO          │ NO       │
│ ¿Es inmutable?                  │ NO         │ SÍ          │ N/A      │
│ ¿Igualdad por identidad?        │ SÍ         │ Por valor   │ N/A      │
│ ¿Se persiste directamente?      │ SÍ         │ Embebido    │ NO       │
│ ¿Coordina entre objetos?        │ NO         │ NO          │ SÍ       │
│ ¿Tiene estado?                  │ SÍ         │ N/A         │ NO       │
└─────────────────────────────────┴────────────┴─────────────┴──────────┘
```

---

### Antipatrones evitados

| Antipatrón | Solución correcta | Servicio |
|---|---|---|
| Crear Entity para cada concepto | Value Objects para etiquetas de seguridad | Todo |
| Pasar strings en lugar de Enums | TipoTransaccion, EstadoTransaccion como Enums | Banking |
| Usar float para dinero | Decimal con VO Dinero | Banking |
| Confundir Domain Service con Repository | ProcesadorTransferencias vs ActivoInversionRepository | Banking |
| Permitir mutación de agregados | Transaccion frozen, Dinero immutable | Banking |
| Exponer Entity interna al controller | ResultadoTransferencia como VO de salida | Banking |

---
