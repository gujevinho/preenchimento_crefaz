import os
import uuid
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from automation import preencher_formulario

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="Form Automation API", version="1.0.0")

# ----------------------------------------------------------------------
# Autenticação simples via API Key (header: X-API-Key)
# Configure a chave real na variável de ambiente API_KEY no Render.
# ----------------------------------------------------------------------
API_KEY = os.getenv("API_KEY", "troque-esta-chave")


def verificar_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida ou ausente")


# ----------------------------------------------------------------------
# Armazenamento simples do status dos jobs em memória.
# Se o serviço reiniciar, o histórico se perde — suficiente para uso
# simples. Para algo mais robusto, trocar por Redis futuramente.
# ----------------------------------------------------------------------
jobs: Dict[str, Dict[str, Any]] = {}


class FormularioRequest(BaseModel):
    dados: Dict[str, Any]


class JobResponse(BaseModel):
    job_id: str
    status: str


def executar_job(job_id: str, dados: dict):
    jobs[job_id]["status"] = "em_execucao"
    resultado = preencher_formulario(dados)
    jobs[job_id]["status"] = "concluido" if resultado.get("sucesso") else "erro"
    jobs[job_id]["resultado"] = resultado
    jobs[job_id]["finalizado_em"] = datetime.now(timezone.utc).isoformat()


@app.get("/")
def raiz():
    return {"status": "online", "servico": "Form Automation API"}


@app.get("/health")
def health():
    """Endpoint de health check — usado pelo Render para monitorar o serviço."""
    return {"status": "ok"}


@app.post("/preencher-formulario", response_model=JobResponse, dependencies=[])
def preencher(request: FormularioRequest, background_tasks: BackgroundTasks,
              x_api_key: Optional[str] = Header(None)):
    verificar_api_key(x_api_key)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "na_fila",
        "criado_em": datetime.now(timezone.utc).isoformat(),
        "resultado": None,
    }

    background_tasks.add_task(executar_job, job_id, request.dados)

    return JobResponse(job_id=job_id, status="na_fila")


@app.get("/status/{job_id}")
def status_job(job_id: str, x_api_key: Optional[str] = Header(None)):
    verificar_api_key(x_api_key)

    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return {"job_id": job_id, **job}
