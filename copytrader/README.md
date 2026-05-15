# MT5 CopyTrader

Sistema de copytrading para MetaTrader 5 Docker.

## Inicio Rápido

```bash
# Iniciar todos los contenedores
docker compose -f docker-compose.copytrader.yaml up -d

# Ver logs del copytrader
docker logs -f copytrader

# Ver estado de la API
curl http://localhost:8180/health
```

## Configuración Inicial (Primera Vez)

**IMPORTANTE**: En el primer inicio, MT5 muestra un asistente de configuración de cuenta que bloquea la conexión programática. Debes completar el login manualmente UNA VEZ a través de VNC:

### Paso 1: Acceder a VNC

- **Master**: http://localhost:3100 (usuario: `admin`, contraseña: `admin`)
- **Slave**: http://localhost:3101 (usuario: `admin`, contraseña: `admin`)

### Paso 2: Completar el Asistente de Cuenta

En cada sesión VNC:

1. En el diálogo "Open an Account", selecciona **"Connect to an existing trading account"**
2. Busca el servidor del broker (ej: `Weltrade-Demo`)
3. Ingresa las credenciales:
   - **Master**: Login `19713030`, Password según configuración
   - **Slave**: Login `19713032`, Password según configuración
4. Haz clic en "Finish"

### Paso 3: Verificar Conexión

Una vez configuradas las cuentas, reinicia los contenedores:

```bash
docker compose -f docker-compose.copytrader.yaml restart
```

El copytrader debería conectarse automáticamente.

## Verificación

```bash
# Ver estado del sistema
curl http://localhost:8180/health

# Ver cuentas conectadas
curl http://localhost:8180/accounts

# Ver posiciones activas
curl http://localhost:8180/positions
```

## Configuración

Edita `copytrader/config/copytrader.yaml` para:

- Cambiar credenciales de las cuentas
- Agregar más cuentas slave
- Configurar modo de lotaje (exact, fixed, multiplier, proportional)
- Ajustar intervalos de polling

## Arquitectura

```
┌─────────────────────────────┐
│   CopyTrader Orchestrator   │ ← Python service
│   - Monitorea master        │
│   - Ejecuta en slaves       │
│   - API REST :8180          │
└──────────┬──────────────────┘
           │ RPyC (puerto 8001)
     ┌─────┴─────┬─────────────┐
     ▼           ▼             ▼
┌─────────┐ ┌─────────┐   ┌─────────┐
│ Master  │ │ Slave 1 │   │ Slave N │
│ VNC:3100│ │ VNC:3101│   │ VNC:310N│
└─────────┘ └─────────┘   └─────────┘
```

## Operaciones Soportadas

- **Apertura**: Se copian nuevas posiciones del master a los slaves
- **Cierre**: Se cierran las posiciones correspondientes en los slaves
- **Modificación SL/TP**: Se actualizan en los slaves
- **Cierre parcial**: Se cierra proporcionalmente en los slaves

## Modos de Lotaje

| Modo | Descripción |
|------|-------------|
| `exact` | Mismo lote que el master |
| `fixed` | Lote fijo configurado |
| `multiplier` | Lote master × multiplicador |
| `proportional` | Proporcional al balance (slave/master) |
