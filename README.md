# SecureBankito 

Proof of Concept (PoC) de un sistema bancario seguro basado en **Domain-Driven Design (DDD) táctico**, **Microservicios** y **Security by Design**, implementando los modelos clásicos de control de acceso **Biba** (Integridad) y **Bell-LaPadula** (Confidencialidad) como reglas de negocio del dominio.

---

## Objetivo

Demostrar cómo los modelos formales de seguridad pueden integrarse directamente dentro de una arquitectura moderna de microservicios, garantizando restricciones de integridad y confidencialidad más allá de los mecanismos tradicionales de autenticación y autorización.

---

## Características Principales

* Arquitectura basada en microservicios.
* Domain-Driven Design (DDD) táctico.
* Autenticación mediante JWT.
* Implementación del modelo Biba para protección de integridad.
* Implementación del modelo Bell-LaPadula para protección de confidencialidad.
* Bases de datos desacopladas por contexto delimitado.
* Despliegue mediante Docker, Docker Compose y Kubernetes (Minikube).

---

## Arquitectura General

| Servicio              | Puerto | Responsabilidad                                | Modelo de Seguridad |
| --------------------- | ------ | ---------------------------------------------- | ------------------- |
| `iam-service`         | 8001   | Gestión de identidad y emisión de JWT          | N/A                 |
| `banking-service`     | 8002   | Gestión de cuentas y transferencias bancarias  | Biba                |
| `investments-service` | 8003   | Gestión de inversiones y activos de alto valor | Bell-LaPadula       |

### Niveles de Seguridad

#### Clasificación de Confidencialidad

```text
Bronce < Plata < Oro
```

#### Niveles de Integridad

```text
1 < 2 < 3
```

---

## Dominio de Investments

El contexto de `investments-service` modela la gestión de activos financieros de alto valor. Su preocupación principal no es la integridad de escritura, sino la **confidencialidad** de la información expuesta a cada sujeto.

### 1. Personas / Sujetos

En este dominio, un sujeto es un usuario autenticado que consume el servicio mediante un JWT emitido por `iam-service`. El servicio no administra identidades completas; únicamente interpreta el nivel de autorización del sujeto.

| Sujeto | Clearance | Acceso esperado |
| ------ | --------- | ---------------- |
| Usuario Bronce | `Bronce` | No puede leer activos clasificados como `Oro` |
| Usuario Plata | `Plata` | No puede leer activos clasificados como `Oro` |
| Usuario Oro | `Oro` | Puede leer activos `Oro` |

La etiqueta de confidencialidad se extrae del token y se valida antes de consultar la base de datos.

### 2. Procesos de Negocio

El flujo principal del dominio es la consulta de activos de inversión:

1. El cliente envía una petición autenticada al endpoint de inversiones.
2. El middleware decodifica el JWT y obtiene el `clearance` del sujeto.
3. El caso de uso aplica la regla Bell-LaPadula: **No Read Up**.
4. Si el clearance es insuficiente, el servicio responde `403 Forbidden`.
5. Si el clearance es válido, el repositorio devuelve los activos clasificados.

Este diseño asegura que la restricción de seguridad se aplique en la capa de aplicación y no solo en el controlador.

### 3. Tecnologías

El dominio de investments se implementa con las siguientes tecnologías:

| Capa | Tecnología | Uso |
| ---- | ---------- | --- |
| Backend | Python 3.12 + FastAPI | Exposición de endpoints y lógica HTTP |
| Dominio | DDD táctico | Entidades, value objects y servicios de dominio |
| Persistencia | PostgreSQL + SQLAlchemy | Almacenamiento de activos |
| Seguridad | JWT + PyJWT | Validación del clearance del sujeto |
| Contenerización | Docker | Empaquetado del servicio |
| Orquestación local | Docker Compose | Ejecución de servicios y base de datos |
| Orquestación en clúster | Kubernetes / Minikube | Despliegue declarativo del contexto de investments |

### 4. Regla aplicada en el dominio

En este contexto se aplica Bell-LaPadula con la restricción:

> **No Read Up**: un sujeto no puede leer información cuya clasificación sea superior a su clearance.

Esto se traduce en la práctica en que los activos de inversión se clasifican como `Oro`, y solo un sujeto con clearance `Oro` puede acceder a ellos.

---

## Estructura del Proyecto

```text
securebankito/

├── iam-service/
│   ├── app/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── Dockerfile
│   └── requirements.txt
│
├── banking-service/
│   ├── app/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── Dockerfile
│   └── requirements.txt
│
├── investments-service/
│   ├── app/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── Dockerfile
│   └── requirements.txt
│
├── k8s/
│   ├── iam/
│   ├── banking/
│   └── investments/
│
├── docker-compose.yml
└── README.md
```

---

## Modelos de Seguridad Implementados

### Biba — Integridad

Propiedad aplicada en `banking-service`:

> **No Write Up**

Un sujeto no puede modificar recursos cuyo nivel de integridad sea superior al suyo.

#### Ejemplo

```text
Usuario:
integrity_level = 1

Cuenta destino:
integrity_level = 3

Resultado:
403 Forbidden
```

---

### Bell-LaPadula — Confidencialidad

Propiedad aplicada en `investments-service`:

> **No Read Up**

Un sujeto no puede acceder a información clasificada por encima de su nivel de autorización.

#### Ejemplo

```text
Usuario:
clearance = Plata

Activo:
classification = Oro

Resultado:
403 Forbidden
```

---

## Contrato JWT

Todos los servicios consumen tokens emitidos por `iam-service`.

```json
{
  "sub": "user-uuid",
  "username": "julio",
  "clearance": "Oro",
  "integrity": 3,
  "exp": 1234567890
}
```

---

## Ejecución Local

### Docker Compose

```bash
git clone https://github.com/<usuario>/securebankito.git

cd securebankito

docker compose up --build
```

---

## Despliegue en Kubernetes

```bash
minikube start

kubectl apply -f k8s/

kubectl get pods

kubectl get services
```

---

## Escenarios de Validación

| Caso                      | Descripción                                       | Resultado Esperado |
| ------------------------- | ------------------------------------------------- | ------------------ |
| Integridad inválida       | Usuario nivel 1 intenta modificar recurso nivel 3 | `403 Forbidden`    |
| Confidencialidad inválida | Usuario Plata intenta leer recurso Oro            | `403 Forbidden`    |
| Acceso autorizado         | Usuario Oro nivel 3                               | `200 OK`           |

---

## Stack Tecnológico

### Backend

* Python 3.12
* FastAPI
* Pydantic
* SQLAlchemy

### Persistencia

* PostgreSQL

### Seguridad

* JWT
* PyJWT
* Bcrypt

### Infraestructura

* Docker
* Docker Compose
* Kubernetes
* Minikube

---

## Conceptos Aplicados

* Domain-Driven Design (DDD)
* Bounded Contexts
* Entities
* Value Objects
* Aggregates
* Application Services
* Repository Pattern
* Security by Design
* Bell-LaPadula Security Model
* Biba Integrity Model
* JWT Authentication
* Containerized Microservices

---


## Licencia

Este proyecto fue desarrollado con fines académicos y de investigación como prueba de concepto para la integración de modelos formales de seguridad en arquitecturas de microservicios.
