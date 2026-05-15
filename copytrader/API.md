# CopyTrader API Documentation

Base URL: `http://localhost:8180`

## Overview

REST API for monitoring and controlling the MetaTrader 5 CopyTrader service.

---

## Health Endpoints

### GET /health
Health check - returns basic service status.

**Response:**
```json
{
  "status": "healthy",
  "running": true,
  "master_connected": true,
  "slaves_connected": 1,
  "slaves_total": 1,
  "active_mappings": 0
}
```

### GET /status
Detailed service status including all accounts.

**Response:**
```json
{
  "running": true,
  "master": {
    "connected": true,
    "state": {
      "name": "master-weltrade",
      "role": "master",
      "balance": 10000.0,
      "equity": 10000.0,
      "positions_count": 0,
      "error_count": 0,
      "last_error": null
    }
  },
  "slaves": {
    "slave-weltrade": {
      "connected": true,
      "state": { ... }
    }
  },
  "active_mappings": 0
}
```

### GET /ready
Kubernetes-style readiness check.

**Response:**
```json
{
  "ready": true
}
```

---

## Account Endpoints

### GET /accounts
List all connected accounts (master + slaves).

**Response:**
```json
{
  "master": {
    "name": "master-weltrade",
    "role": "master",
    "host": "mt5-master",
    "port": 8001,
    "connected": true,
    "balance": 10000.0,
    "equity": 10000.0,
    "positions_count": 0,
    "error_count": 0,
    "last_error": null
  },
  "slaves": [
    {
      "name": "slave-weltrade",
      "role": "slave",
      "host": "mt5-slave1",
      "port": 8001,
      "connected": true,
      "balance": 10000.0,
      "equity": 10000.0,
      "positions_count": 0,
      "error_count": 0,
      "last_error": null
    }
  ]
}
```

### GET /accounts/{name}
Get specific account information.

**Parameters:**
- `name`: Account name (e.g., "master", "slave-weltrade")

### POST /accounts/{name}/reconnect
Attempt to reconnect a disconnected account.

**Parameters:**
- `name`: Account name to reconnect

**Response:**
```json
{
  "account": "slave-weltrade",
  "action": "reconnect",
  "success": true
}
```

---

## Slave Management Endpoints

### GET /accounts/slaves
List all slave accounts with detailed configuration.

**Response:**
```json
[
  {
    "name": "slave-weltrade",
    "host": "mt5-slave1",
    "port": 8001,
    "enabled": true,
    "connected": true,
    "lot_mode": "proportional",
    "lot_value": 1.0,
    "max_lot": 10.0,
    "min_lot": 0.01,
    "magic_number": 123456,
    "invert_trades": false,
    "max_slippage": 20,
    "symbols_filter": null,
    "state": {
      "name": "slave-weltrade",
      "role": "slave",
      "connected": true,
      "balance": 10000.0,
      "equity": 10000.0,
      "positions_count": 0,
      "error_count": 0,
      "last_error": null
    }
  }
]
```

### POST /accounts/slaves
Add a new slave account dynamically.

**Request Body:**
```json
{
  "name": "new-slave",
  "host": "mt5-slave2",
  "port": 8001,
  "login": 19713033,
  "password": "password123",
  "server": "Weltrade-Demo",
  "enabled": true,
  "lot_mode": "proportional",
  "lot_value": 1.0,
  "max_lot": 10.0,
  "min_lot": 0.01,
  "symbols_filter": null,
  "magic_number": 123456,
  "invert_trades": false,
  "max_slippage": 20
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| name | string | Yes | - | Unique name for the slave account |
| host | string | Yes | - | Hostname or IP of the MT5 container |
| port | int | No | 8001 | RPyC port |
| login | int | No | null | MT5 account login number |
| password | string | No | null | MT5 account password |
| server | string | No | null | MT5 server name |
| enabled | bool | No | true | Whether to enable immediately |
| lot_mode | string | No | "exact" | Lot calculation mode |
| lot_value | float | No | 1.0 | Lot value (depends on lot_mode) |
| max_lot | float | No | 10.0 | Maximum lot size |
| min_lot | float | No | 0.01 | Minimum lot size |
| symbols_filter | array | No | null | Symbols to copy (null = all) |
| magic_number | int | No | 123456 | Magic number for orders |
| invert_trades | bool | No | false | Invert trade direction |
| max_slippage | int | No | 20 | Maximum slippage in points |

**Lot Modes:**
- `exact`: Copy the same lot size as master
- `fixed`: Use a fixed lot size (lot_value = lot size)
- `multiplier`: Multiply master lot by factor (lot_value = multiplier)
- `proportional`: Scale based on balance ratio (lot_value = not used, calculates automatically)

**Response (201 Created):**
```json
{
  "success": true,
  "name": "new-slave",
  "connected": true,
  "state": {
    "name": "new-slave",
    "role": "slave",
    "connected": true,
    "balance": 10000.0,
    "equity": 10000.0,
    "positions_count": 0,
    "error_count": 0,
    "last_error": null
  }
}
```

### DELETE /accounts/slaves/{name}
Remove a slave account.

**Parameters:**
- `name`: Name of the slave to remove
- `close_positions` (query, optional): If true, close all open positions before removing

**Example:**
```
DELETE /accounts/slaves/slave-weltrade?close_positions=true
```

**Response:**
```json
{
  "success": true,
  "name": "slave-weltrade",
  "message": "Slave 'slave-weltrade' removed successfully"
}
```

### PUT /accounts/slaves/{name}
Update slave account configuration.

**Request Body (all fields optional):**
```json
{
  "lot_mode": "multiplier",
  "lot_value": 2.0,
  "max_lot": 5.0,
  "min_lot": 0.1,
  "symbols_filter": ["EURUSD", "GBPUSD"],
  "magic_number": 999999,
  "invert_trades": true,
  "max_slippage": 10
}
```

**Response:**
```json
{
  "success": true,
  "name": "slave-weltrade",
  "message": "Slave 'slave-weltrade' configuration updated"
}
```

### POST /accounts/slaves/{name}/enable
Enable a slave account and connect it.

**Response:**
```json
{
  "success": true,
  "name": "slave-weltrade",
  "connected": true,
  "state": { ... }
}
```

### POST /accounts/slaves/{name}/disable
Disable a slave account (stop copying trades to it).

**Parameters:**
- `close_positions` (query, optional): If true, close all open positions

**Example:**
```
POST /accounts/slaves/slave-weltrade/disable?close_positions=true
```

**Response:**
```json
{
  "success": true,
  "name": "slave-weltrade",
  "message": "Slave 'slave-weltrade' disabled",
  "positions_closed": true
}
```

---

## Position Endpoints

### GET /positions
List all active position mappings (master -> slave).

**Response:**
```json
{
  "total": 1,
  "mappings": {
    "256202570": [
      {
        "master_ticket": 256202570,
        "slave_ticket": 256202573,
        "slave_name": "slave-weltrade",
        "symbol": "EURUSD",
        "master_volume": 0.01,
        "slave_volume": 0.01,
        "status": "open"
      }
    ]
  }
}
```

### GET /positions/master/{ticket}
Get mappings for a specific master position.

**Parameters:**
- `ticket`: Master position ticket number

### GET /positions/stats
Get position statistics summary.

**Response:**
```json
{
  "total_master_positions": 1,
  "total_slave_positions": 1,
  "positions_by_slave": {
    "slave-weltrade": 1
  },
  "positions_by_symbol": {
    "EURUSD": 1
  }
}
```

---

## Configuration File

Configuration is loaded from `/app/config/copytrader.yaml` at startup:

```yaml
master:
  name: "master-weltrade"
  host: "mt5-master"
  port: 8001
  login: 19713030
  password: "Nu&5V+h2"
  server: "Weltrade-Demo"

slaves:
  - name: "slave-weltrade"
    host: "mt5-slave1"
    port: 8001
    login: 19713032
    password: "+8zHS&5u"
    server: "Weltrade-Demo"
    enabled: true
    lot_mode: "proportional"
    lot_value: 1.0
    max_lot: 10.0
    min_lot: 0.01
    magic_number: 123456
    max_slippage: 20

settings:
  polling_interval_ms: 500
  retry_attempts: 3
```

**Note:** Slaves can also be added dynamically via API. Dynamic slaves are not persisted to the config file.

---

## Error Responses

All endpoints may return error responses:

```json
{
  "detail": "Account 'unknown' not found"
}
```

HTTP Status Codes:
- `200` - Success
- `201` - Created (for POST /accounts/slaves)
- `400` - Bad request (invalid parameters)
- `404` - Resource not found
- `500` - Internal server error

---

## Usage Examples

### Add a new slave via curl

```bash
curl -X POST http://localhost:8180/accounts/slaves \
  -H "Content-Type: application/json" \
  -d '{
    "name": "slave2",
    "host": "mt5-slave2",
    "port": 8001,
    "login": 19713033,
    "password": "mypassword",
    "server": "Weltrade-Demo",
    "lot_mode": "proportional",
    "enabled": true
  }'
```

### Disable a slave and close positions

```bash
curl -X POST "http://localhost:8180/accounts/slaves/slave2/disable?close_positions=true"
```

### Update slave lot settings

```bash
curl -X PUT http://localhost:8180/accounts/slaves/slave2 \
  -H "Content-Type: application/json" \
  -d '{
    "lot_mode": "fixed",
    "lot_value": 0.1,
    "max_lot": 1.0
  }'
```

### Remove a slave

```bash
curl -X DELETE "http://localhost:8180/accounts/slaves/slave2?close_positions=true"
```
