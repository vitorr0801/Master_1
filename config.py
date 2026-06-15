# config.py
MASTER_PORT = 10000
BUFFER_SIZE = 4096
THRESHOLD = 10              # saturation: queue depth above this triggers request_help
RELEASE_THRESHOLD = 6       # hysteresis: queue depth below this triggers worker return
REQUEST_INTERVAL = 0.5      # seconds between simulated task arrivals (rapido para demo)
TASK_PROCESS_TIME = 3       # max seconds a worker spends on a task (random 1..N)
WORKER_HEARTBEAT_INTERVAL = 30  # seconds between worker heartbeats (Sprint 1)
LOG_SEPARATOR = "======================================="

# Unique identifier for this Master node
MASTER_ID = "Master_1"

# Neighbor masters for M2M negotiation (Sprint 3).
# MAX_NEIGHBOR_MASTERS = 1: nesta etapa apenas 1 master vizinho é permitido.
MAX_NEIGHBOR_MASTERS = 4
NEIGHBOR_MASTERS = [
    {"master_id": "Master_2", "ip": "10.62.217.24", "port": 10000},
    {"master_id": "Master_3", "ip": "10.62.217.219", "port": 10000},
    {"master_id": "Master_4", "ip": "10.62.217.216", "port": 10000},
    {"master_id": "Master_5", "ip": "10.62.217.39", "port": 10000}
]

# --- CONFIGURAÇÕES DE ELEIÇÃO ---
ELECTION_PORT = 5020
MAX_HEARTBEAT_FAILS = 4
ELECTION_TIMEOUT = 5

ELECTION_SERVER_PORT = 5030
ELECTION_MASTER_PORT = MASTER_PORT
HEARTBEAT_FAIL_THRESHOLD = MAX_HEARTBEAT_FAILS

# Sprint 4: Supervisor metrics reporting
SUPERVISOR_HOST = "10.62.217.45"
SUPERVISOR_PORT = 8000
SUPERVISOR_TLS = False
SUPERVISOR_SNI = "10.62.217.45"
SUPERVISOR_REPORT_INTERVAL = 10   # seconds between performance_report sends

SERVER_UUID = "Master_1"          
HOSTNAME    = "MASTER_1.farm.local"