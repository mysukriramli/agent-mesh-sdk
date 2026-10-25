import os
import re
import json
import uuid
import math
import hashlib
import urllib.request
from datetime import datetime, timezone
import duckdb
from wasmtime import Store, Module, Instance

MESH_REGISTRY_URL = "https://mysukriramli.github.io/agent-blackboard/agent-mesh.json"
VECTOR_DIM = 128
PROJECTION_SEED = 42

class AgentMeshKernel:
    """Zero-overhead autonomous data plane client for multi-agent swarms."""

    def __init__(self, registry_url: str = MESH_REGISTRY_URL):
        self.registry_url = registry_url
        self.mesh_config = self._load_mesh_config()
        self.wasm_cache = {}

    def _load_mesh_config(self) -> dict:
        req = urllib.request.Request(self.registry_url, headers={"User-Agent": "AgentMeshKernel/4.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return {}

    # 1. Zero-Token Semantic Search (Hamming Distance over Parquet)
    def search_vector_fabric(self, query: str, top_k: int = 5) -> list[dict]:
        parquet_url = "https://mysukriramli.github.io/quantized-vector-fabric/vectors.parquet"
        tokens = re.findall(r"\w+", query.lower())
        if not tokens:
            return []

        raw_dense = [0.0] * VECTOR_DIM
        for token in tokens:
            for i in range(VECTOR_DIM):
                h_in = f"{PROJECTION_SEED}_{token}_{i}".encode("utf-8")
                digest = hashlib.md5(h_in).digest()
                val = ((digest[0] % 3) - 1)
                raw_dense[i] += float(val)

        query_bits = 0
        for i in range(VECTOR_DIM):
            if raw_dense[i] > 0:
                query_bits |= (1 << i)

        conn = duckdb.connect()
        conn.execute("INSTALL httpfs; LOAD httpfs;")
        rows = conn.execute(f"SELECT doc_id, source_wire, title, summary, bit_packed_hex FROM '{parquet_url}'").fetchall()

        scored = []
        for r in rows:
            doc_id, wire, title, summary, bit_hex = r
            doc_bits = int(bit_hex, 16)
            xor_diff = query_bits ^ doc_bits
            distance = bin(xor_diff).count("1")
            similarity = 1.0 - (distance / VECTOR_DIM)
            scored.append({
                "similarity": round(similarity, 4),
                "doc_id": doc_id,
                "wire": wire,
                "title": title,
                "summary": summary
            })

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]

    # 2. Microsecond Deterministic Wasm Execution
    def execute_wasm(self, module_name: str, function_name: str, *args):
        wasm_url = f"https://mysukriramli.github.io/agent-wasm-runtime-registry/wasm/{module_name}.wasm"
        
        if module_name not in self.wasm_cache:
            req = urllib.request.Request(wasm_url, headers={"User-Agent": "AgentMeshKernel/4.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.wasm_cache[module_name] = resp.read()

        store = Store()
        module = Module(store.engine, self.wasm_cache[module_name])
        instance = Instance(store, module, [])
        func = instance.exports(store)[function_name]
        return func(store, *args)

    # 3. Remote 4D Spacetime Bounding Box Query (HTTP Range Requests)
    def query_spacetime_tensor(self, min_mag: float = 3.0, layer: str = "CRUST_SHALLOW", limit: int = 10) -> list[dict]:
        parquet_url = "https://mysukriramli.github.io/H3-4D-Spacetime-Tensor/spacetime.parquet"
        conn = duckdb.connect()
        conn.execute("INSTALL httpfs; LOAD httpfs;")
        
        query = f"""
            SELECT tensor_coord, h3_index, latitude, longitude, depth_altitude_layer, time_bucket_utc, magnitude
            FROM '{parquet_url}'
            WHERE magnitude >= {min_mag} AND depth_altitude_layer = '{layer}'
            ORDER BY observed_at_utc DESC
            LIMIT {limit}
        """
        cur = conn.execute(query)
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    # 4. Generate Non-Conflicting CRDT Delta Payload
    def create_crdt_delta(self, agent_id: str, entity_id: str, key: str, value, lamport: int = 1) -> dict:
        return {
            "delta_id": str(uuid.uuid4()),
            "agent_id": agent_id,
            "lamport_timestamp": lamport,
            "operations": [
                {
                    "type": "SET",
                    "entity_id": entity_id,
                    "key": key,
                    "value": value,
                    "wall_time_utc": datetime.now(timezone.utc).isoformat()
                }
            ]
        }

    # 5. Pre-Execution Prompt Sanitization Check
    def sanitize_input(self, text: str) -> tuple[bool, str]:
        sigs_url = "https://mysukriramli.github.io/prompt-injection-signatures-wire/v1/signatures.json"
        req = urllib.request.Request(sigs_url, headers={"User-Agent": "AgentMeshKernel/4.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for s in data.get("signatures", []):
                    if re.search(s["regex_rule"], text):
                        return False, f"Matched {s['sig_id']} ({s['category']})"
        except Exception:
            pass
        return True, "CLEAN"
