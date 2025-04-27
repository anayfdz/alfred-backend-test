# Alfred Backend Test - API de Servicio de Domicilios

Este proyecto implementa una API REST con Django REST Framework para asignar servicios de domicilio al conductor disponible más cercano.

## Funcionalidades

*   Gestiona Direcciones y Conductores.
*   Permite a clientes autenticados solicitar un servicio basado en su latitud/longitud.
*   Asigna automáticamente el conductor disponible más cercano.
*   Calcula el tiempo estimado de llegada basado en la distancia Haversine y una velocidad promedio asumida.
*   Permite a conductores/usuarios autenticados marcar servicios como completados.
*   Provee endpoints CRUD autenticados para gestionar Direcciones y Conductores.
*   Incluye sembrado de datos (seeding) para configuración inicial.
*   Incluye autenticación de API basada en Token.
*   Entorno Dockerizado usando Docker Compose.

## Requisitos

*   Docker
*   Docker Compose

## Primeros Pasos (Docker)

1.  **Clonar el repositorio:**
    ```bash
    git clone <url_repositorio>
    cd alfred-backend-test
    ```

2.  **Construir y Ejecutar con Docker Compose:**
    Este comando construirá la imagen de la aplicación Django, iniciará el contenedor de la base de datos PostgreSQL, ejecutará migraciones, sembrará datos iniciales, y iniciará el servidor de desarrollo de Django.
    ```bash
    docker-compose up --build
    ```
    *   **Nota:** La primera vez que ejecutes esto, o después de eliminar el volumen de la base de datos, podrías necesitar crear un superusuario manualmente *dentro del contenedor en ejecución* si necesitas iniciar sesión en el admin o deseas un usuario específico para acceder a la API inicialmente:
        ```bash
        docker-compose exec web python manage.py createsuperuser
        ```

3.  **Obtener Token de Autenticación:**
    Para interactuar con los endpoints protegidos de la API, primero necesitas un token de autenticación. Realiza una petición POST a `/api-token-auth/` con el nombre de usuario y contraseña de un usuario válido (ej., el superusuario que creaste).

    Ejemplo usando `curl`:
    ```bash
    curl -X POST http://localhost:8000/api-token-auth/ -d "username=<tu_usuario>&password=<tu_contraseña>"
    ```
    La respuesta será un objeto JSON conteniendo el token:
    ```json
    { "token": "<tu_token_de_autenticacion>" }
    ```

4.  **Acceder a la API (con Autenticación):**
    Incluye el token obtenido en la cabecera (header) `Authorization` para todas las peticiones subsiguientes a los endpoints de la API.

    Ejemplo usando `curl` para listar conductores:
    ```bash
    curl -H "Authorization: Token <tu_token_de_autenticacion>" http://localhost:8000/api/drivers/
    ```

    **Endpoints de la API (requieren Autenticación):**
    *   **Conductores:** `http://localhost:8000/api/drivers/` (GET, POST)
    *   **Detalle Conductor:** `http://localhost:8000/api/drivers/<id_conductor>/` (GET, PUT, PATCH, DELETE)
    *   **Direcciones:** `http://localhost:8000/api/addresses/` (GET, POST)
    *   **Detalle Dirección:** `http://localhost:8000/api/addresses/<id_direccion>/` (GET, PUT, PATCH, DELETE)
    *   **Solicitar Servicio (POST):** `http://localhost:8000/api/services/request/`
        *   Cuerpo (JSON): `{ "latitude": <float>, "longitude": <float> }`
    *   **Completar Servicio (PATCH):** `http://localhost:8000/api/services/<id_servicio>/complete/`
        *   Cuerpo (JSON): `{ "status": "COMPLETED" }`

5.  **Detener los servicios:**
    Presiona `Ctrl+C` en la terminal donde `docker-compose up` se está ejecutando, luego ejecuta:
    ```bash
    docker-compose down
    ```
    Para eliminar también el volumen de la base de datos (borra todos los datos):
    ```bash
    docker-compose down -v
    ```

## Estructura del Proyecto

*   `api/`: App de Django que contiene modelos, serializadores, vistas, URLs, tests y comandos de gestión.
*   `delivery_service/`: Directorio principal del proyecto Django (settings, URLs principales).
*   `manage.py`: Script de gestión de Django.
*   `requirements.txt`: Dependencias de Python.
*   `Dockerfile`: Define el contenedor de la aplicación Django.
*   `docker-compose.yml`: Orquesta los servicios web y de base de datos.
*   `README.md`: Este archivo.

## Despliegue Conceptual en la Nube (Ejemplo AWS)

Desplegar esta aplicación en un proveedor cloud como AWS típicamente involucraría los siguientes servicios:

1.  **Orquestación de Contenedores (Amazon ECS o EKS):**
    *   **ECS (Elastic Container Service):** Servicio nativo de orquestación de contenedores de AWS. Más simple para empezar comparado con EKS.
    *   **EKS (Elastic Kubernetes Service):** Servicio gestionado de Kubernetes. Ofrece más flexibilidad y potencia pero tiene una curva de aprendizaje más pronunciada.
    *   **Elección:** ECS con tipo de lanzamiento Fargate es a menudo un buen punto de partida para aplicaciones Django, ya que Fargate abstrae la gestión de servidores.
    *   **Proceso:** El `Dockerfile` se usaría para construir una imagen enviada a **Amazon ECR (Elastic Container Registry)**. Una Definición de Tarea (Task Definition) de ECS especificaría esta imagen, requisitos de CPU/memoria, variables de entorno (para conexión a BD, `SECRET_KEY` de Django, `DEBUG=False`, `ALLOWED_HOSTS`), y mapeos de puertos. Un Servicio ECS gestionaría instancias en ejecución de esta tarea, potencialmente detrás de un **Application Load Balancer (ALB)** para distribución de tráfico y terminación SSL.

2.  **Base de Datos (Amazon RDS):**
    *   **Servicio:** Usar Amazon RDS (Relational Database Service) para PostgreSQL.
    *   **Beneficios:** Servicio gestionado que maneja backups, parches, escalado y alta disponibilidad.
    *   **Configuración:** Crear una instancia RDS para PostgreSQL. Configurar grupos de seguridad para permitir conexiones solo desde las tareas ECS/ALB (dentro de la VPC).
    *   **Conexión:** La Definición de Tarea de ECS proporcionaría el endpoint de RDS, usuario, contraseña y nombre de la base de datos como variables de entorno al contenedor Django.

3.  **Redes (VPC, Grupos de Seguridad, ALB):**
    *   **VPC (Virtual Private Cloud):** Proporciona aislamiento de red.
    *   **Grupos de Seguridad:** Actúan como firewalls controlando el tráfico hacia RDS y tareas ECS.
    *   **ALB (Application Load Balancer):** Distribuye el tráfico HTTP/S entrante entre las tareas ECS, maneja chequeos de salud (health checks), y puede gestionar certificados SSL (**AWS Certificate Manager - ACM**).

4.  **Archivos Estáticos (Amazon S3 & CloudFront - Opcional pero Recomendado):**
    *   Aunque esta API no sirve archivos estáticos directamente al usuario actualmente, una aplicación Django en producción típicamente lo haría.
    *   Usar librerías como `django-storages` para recolectar y servir archivos estáticos (CSS, JS) y potencialmente archivos subidos por usuarios desde un **bucket S3**.
    *   Usar **Amazon CloudFront** (CDN) delante de S3 para una entrega más rápida globalmente.

**Consideraciones de Escalabilidad y Seguridad:**

*   **Escalabilidad:**
    *   Los Servicios ECS pueden configurarse para auto-escalar basados en utilización de CPU/memoria o número de peticiones vía el ALB.
    *   Las instancias RDS pueden escalarse verticalmente (tipos de instancia más grandes) u horizontalmente (réplicas de lectura para cargas de trabajo pesadas en lectura, aunque no directamente aplicable a esta simple estructura de API).
*   **Seguridad:**
    *   Ejecutar contenedores como usuarios no-root.
    *   Usar grupos de seguridad para restringir el acceso de red (mínimo privilegio).
    *   Almacenar información sensible (contraseña BD, `SECRET_KEY`) de forma segura, ej., usando **AWS Secrets Manager** o Parameter Store, inyectados como variables de entorno en las tareas ECS.
    *   Establecer `DEBUG=False` en producción.
    *   Configurar `ALLOWED_HOSTS` correctamente.
    *   Implementar autenticación/autorización adecuada para los endpoints de la API (**TokenAuthentication** usada aquí).
    *   Actualizar regularmente las dependencias y las imágenes base de Docker.
    *   Considerar mecanismos de expiración y refresco de tokens para seguridad mejorada en producción.
