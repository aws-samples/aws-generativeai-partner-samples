"""payment-service: a small FastAPI app used to demo Elastic Observability + AWS DevOps Agent.

Telemetry (traces, logs, metrics) is produced by EDOT Python auto-instrumentation
(`opentelemetry-instrument`); this module only uses the standard logging module.

Fault injection
---------------
POST /admin/fault {"mode": "pool_exhaustion"} shrinks the DB connection pool to
2 connections (no overflow, 2s checkout timeout) and makes every payment hold
its connection for HOLD_SECONDS. Under normal load requests queue for a
connection and fail with SQLAlchemy "QueuePool limit ... timed out" -> HTTP 503.
CPU and memory stay flat, which is the point of the scenario.
POST /admin/fault {"mode": "none"} restores the healthy pool.
"""

from __future__ import annotations

import logging
import os
import random
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, TimeoutError as PoolTimeoutError

DB_URL = os.getenv("DB_URL", "sqlite:///./payments.db")
HOST_NAME = os.getenv("HOST_NAME", os.uname().nodename)

HEALTHY_POOL = {"pool_size": 10, "max_overflow": 5, "pool_timeout": 5}
FAULT_POOL = {"pool_size": 2, "max_overflow": 0, "pool_timeout": 2}
HOLD_SECONDS = float(os.getenv("FAULT_HOLD_SECONDS", "1.5"))

log = logging.getLogger("payment_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="payment-service")

_state_lock = threading.Lock()
_state: dict = {"mode": os.getenv("FAULT_MODE", "none"), "engine": None}


def _build_engine(mode: str) -> Engine:
    pool = FAULT_POOL if mode == "pool_exhaustion" else HEALTHY_POOL
    kwargs = dict(pool)
    if DB_URL.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(DB_URL, pool_pre_ping=True, **kwargs)

    if engine.dialect.name == "sqlite":
        # Give SQLite a sleep() so slow queries look like real slow DB spans.
        @event.listens_for(engine, "connect")
        def _register_sleep(dbapi_conn, _):  # noqa: ANN001
            dbapi_conn.create_function("sleep", 1, lambda s: time.sleep(s) or 0)

    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS payments ("
            " id VARCHAR(36) PRIMARY KEY, amount NUMERIC(10,2), currency VARCHAR(3),"
            " status VARCHAR(16), host VARCHAR(64), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        ))
    log.info("db pool configured mode=%s pool_size=%s max_overflow=%s pool_timeout=%s",
             mode, pool["pool_size"], pool["max_overflow"], pool["pool_timeout"])
    return engine


def _engine() -> Engine:
    with _state_lock:
        if _state["engine"] is None:
            _state["engine"] = _build_engine(_state["mode"])
        return _state["engine"]


def _sleep_sql(engine: Engine) -> str:
    return "SELECT pg_sleep(:s)" if engine.dialect.name == "postgresql" else "SELECT sleep(:s)"


class PaymentRequest(BaseModel):
    amount: float
    currency: str = "USD"


class FaultRequest(BaseModel):
    mode: str  # "none" | "pool_exhaustion"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "host": HOST_NAME, "fault_mode": _state["mode"]}


@app.post("/payments", status_code=201)
def create_payment(req: PaymentRequest) -> dict:
    engine = _engine()
    payment_id = str(uuid.uuid4())
    # Simulated fraud-check / ledger query; slow when the fault is active.
    hold = HOLD_SECONDS if _state["mode"] == "pool_exhaustion" else random.uniform(0.005, 0.03)
    try:
        with engine.begin() as conn:
            conn.execute(text(_sleep_sql(engine)), {"s": hold})
            conn.execute(
                text("INSERT INTO payments (id, amount, currency, status, host) "
                     "VALUES (:id, :amount, :currency, 'approved', :host)"),
                {"id": payment_id, "amount": req.amount, "currency": req.currency, "host": HOST_NAME},
            )
    except PoolTimeoutError as exc:
        pool = engine.pool
        log.error(
            "Database connection timeout: connection pool exhausted "
            "(pool_size=%s, checked_out=%s, overflow=%s) payment_id=%s: %s",
            pool.size(), pool.checkedout(), pool.overflow(), payment_id, exc,
        )
        raise HTTPException(status_code=503, detail="database connection pool exhausted") from exc
    except OperationalError as exc:
        log.error("Database operational error payment_id=%s: %s", payment_id, exc)
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    log.info("payment approved payment_id=%s amount=%.2f currency=%s", payment_id, req.amount, req.currency)
    return {"id": payment_id, "status": "approved", "host": HOST_NAME}


@app.get("/payments/{payment_id}")
def get_payment(payment_id: str) -> dict:
    with _engine().connect() as conn:
        row = conn.execute(text("SELECT id, amount, currency, status, host FROM payments WHERE id = :id"),
                           {"id": payment_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="payment not found")
    return dict(row)


@app.post("/admin/fault")
def set_fault(req: FaultRequest) -> dict:
    if req.mode not in ("none", "pool_exhaustion"):
        raise HTTPException(status_code=400, detail="mode must be 'none' or 'pool_exhaustion'")
    with _state_lock:
        old = _state["engine"]
        _state["mode"] = req.mode
        _state["engine"] = _build_engine(req.mode)
    if old is not None:
        old.dispose()
    log.warning("fault mode changed to %s on host %s", req.mode, HOST_NAME)
    return {"host": HOST_NAME, "fault_mode": req.mode}
