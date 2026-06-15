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
MASTER_ID = "Master_A"

# Neighbor masters for M2M negotiation (Sprint 3).
# MAX_NEIGHBOR_MASTERS = 1: nesta etapa apenas 1 master vizinho é permitido.
MAX_NEIGHBOR_MASTERS = 1
NEIGHBOR_MASTERS = [
    {"master_id": "Master_B", "ip": "10.62.206.21", "port": 10000}
]

# --- CONFIGURAÇÕES DE ELEIÇÃO ---
ELECTION_PORT = 5020
MAX_HEARTBEAT_FAILS = 4
ELECTION_TIMEOUT = 5

ELECTION_SERVER_PORT = 5030
ELECTION_MASTER_PORT = MASTER_PORT
HEARTBEAT_FAIL_THRESHOLD = MAX_HEARTBEAT_FAILS

# Sprint 4: Supervisor metrics reporting
SUPERVISOR_HOST = "nuted-ia.dev"
SUPERVISOR_PORT = 443
SUPERVISOR_TLS = True
SUPERVISOR_SNI = "nuted-ia.dev"
SUPERVISOR_REPORT_INTERVAL = 10   # seconds between performance_report sends

SERVER_UUID = "MASTER_13"          
HOSTNAME    = "MASTER_13.farm.local"