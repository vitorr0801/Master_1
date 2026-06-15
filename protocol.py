# protocol.py
import json
import uuid as _uuid_mod


def encode_message(data):
    return (json.dumps(data) + "\n").encode()


def decode_message(data):
    return json.loads(data)


def _new_rid():
    return str(_uuid_mod.uuid4())


# ── Sprint 1: Heartbeat ───────────────────────────────────────────────────────
# Worker → Master: {"SERVER_UUID": "...", "TASK": "HEARTBEAT"}
# Master → Worker: {"SERVER_UUID": "...", "TASK": "HEARTBEAT", "RESPONSE": "ALIVE"}

def heartbeat(server_uuid):
    return {"SERVER_UUID": server_uuid, "TASK": "HEARTBEAT"}


def heartbeat_alive(server_uuid):
    return {"SERVER_UUID": server_uuid, "TASK": "HEARTBEAT", "RESPONSE": "ALIVE"}


# ── Sprint 2: Task Cycle ──────────────────────────────────────────────────────
# 2.1  Worker → Master  (presentation / work request)
#      {"WORKER": "ALIVE", "WORKER_UUID": "..."}
#      {"WORKER": "ALIVE", "WORKER_UUID": "...", "SERVER_UUID": "..."}  ← borrowed
# 2.2  Master → Worker  (has task)
#      {"TASK": "QUERY", "USER": "..."}
# 2.3  Master → Worker  (no task)
#      {"TASK": "NO_TASK"}
# 2.4  Worker → Master  (result)
#      {"STATUS": "OK"|"NOK", "TASK": "QUERY", "WORKER_UUID": "..."}
# 2.5  Master → Worker  (acknowledgement)
#      {"STATUS": "ACK", "WORKER_UUID": "..."}

def worker_alive(worker_uuid, original_master_uuid=None):
    msg = {"WORKER": "ALIVE", "WORKER_UUID": worker_uuid}
    if original_master_uuid:
        msg["SERVER_UUID"] = original_master_uuid
    return msg


def task_query(user):
    return {"TASK": "QUERY", "USER": user}


def task_no_task():
    return {"TASK": "NO_TASK"}


def task_status(status, worker_uuid):
    """status must be 'OK' or 'NOK'."""
    return {"STATUS": status, "TASK": "QUERY", "WORKER_UUID": worker_uuid}


def task_ack(worker_uuid):
    return {"STATUS": "ACK", "WORKER_UUID": worker_uuid}


# ── Sprint 3: Master-to-Master Negotiation ────────────────────────────────────
# All M2M messages carry:
#   "type"       – operation identifier (lowercase, as specified)
#   "request_id" – UUID v4 for correlating request/response
#   "payload"    – operation-specific data

def m2m_request_help(master_id, current_load, capacity, workers_needed, request_id=None):
    return {
        "type": "request_help",
        "request_id": request_id or _new_rid(),
        "payload": {
            "master_id": master_id,
            "current_load": current_load,
            "capacity": capacity,
            "workers_needed": workers_needed,
        },
    }


def m2m_response_accepted(request_id, workers_offered, worker_details):
    """worker_details: [{"id": "W1", "address": "ip:port"}, ...]"""
    return {
        "type": "response_accepted",
        "request_id": request_id,
        "payload": {
            "workers_offered": workers_offered,
            "worker_details": worker_details,
        },
    }


def m2m_response_rejected(request_id, reason="high_load"):
    """reason: 'high_load' | 'no_workers_available' | 'refused'"""
    return {
        "type": "response_rejected",
        "request_id": request_id,
        "payload": {"reason": reason},
    }


def m2m_command_redirect(new_master_address, request_id=None):
    """Master B → Worker B1: redirect to saturated master."""
    return {
        "type": "command_redirect",
        "request_id": request_id or _new_rid(),
        "payload": {"new_master_address": new_master_address},
    }


def m2m_register_temporary_worker(worker_id, original_master_address, request_id=None):
    """Worker B1 → Master A: present as borrowed worker."""
    return {
        "type": "register_temporary_worker",
        "request_id": request_id or _new_rid(),
        "payload": {
            "worker_id": worker_id,
            "original_master_address": original_master_address,
        },
    }


def m2m_command_release(original_master_address, request_id=None):
    """Master A → Worker B1: return to original master."""
    return {
        "type": "command_release",
        "request_id": request_id or _new_rid(),
        "payload": {"original_master_address": original_master_address},
    }


def m2m_notify_worker_returned(worker_id, request_id=None):
    """Master A → Master B: worker has been released."""
    return {
        "type": "notify_worker_returned",
        "request_id": request_id or _new_rid(),
        "payload": {"worker_id": worker_id},
    }


# ── Election helpers (legacy – kept for election.py / worker.py) ──────────────

def election_announce(worker_id, free_disk_bytes, ip, port):
    return {
        "type": "election_announce",
        "worker_id": worker_id,
        "free_disk": free_disk_bytes,
        "ip": ip,
        "port": port,
    }


def election_vote(voter_id, chosen_id):
    return {"type": "election_vote", "voter_id": voter_id, "chosen_id": chosen_id}


def election_result(new_master_id, new_master_ip, new_master_port):
    return {
        "type": "election_result",
        "new_master_id": new_master_id,
        "new_master_ip": new_master_ip,
        "new_master_port": new_master_port,
    }


def i_am_master(master_id, master_ip, master_port):
    return {
        "type": "i_am_master",
        "master_id": master_id,
        "master_ip": master_ip,
        "master_port": master_port,
    }


def election_bid(worker_id, free_space, ip, port):
    return {
        "type": "ELECTION_BID",
        "worker_id": worker_id,
        "free_space": free_space,
        "ip": ip,
        "port": port,
    }


def election_victory(worker_id, ip, port):
    return {
        "type": "ELECTION_VICTORY",
        "worker_id": worker_id,
        "ip": ip,
        "port": port,
    }