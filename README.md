# Form Automation API

API para disparar remotamente a automação de preenchimento de formulário web.

## Estrutura

- `main.py` — API FastAPI (endpoints, autenticação, controle de jobs)
- `automation.py` — lógica de automação (Playwright) — **substitua pelo seu script real**
- `requirements.txt` — dependências
- `render.yaml` — blueprint de deploy automático no Render

## Como funciona

1. Outra aplicação faz um `POST /preencher-formulario` com os parâmetros em JSON
2. A API responde **imediatamente** com um `job_id` (não espera o preenchimento terminar)
3. A automação roda em segundo plano (`BackgroundTasks`)
4. A aplicação que chamou pode consultar `GET /status/{job_id}` para saber o resultado

Isso evita timeout HTTP em automações que demoram alguns segundos.

## Rodando localmente

```bash
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload
```

Acesse `http://localhost:8000/docs` para o Swagger interativo.

## Segurança — variáveis de ambiente obrigatórias

O código **não contém mais nenhuma credencial**. Antes de rodar, configure:

| Variável | Descrição |
|---|---|
| `API_KEY` | Chave que protege sua API (enviada no header `X-API-Key`) |
| `CREFAZON_LOGIN` | Login do sistema Crefazon |
| `CREFAZON_SENHA` | Senha do sistema Crefazon |

⚠️ **A senha que estava no script original (`Amorzinho@2001`) foi exposta em texto puro no histórico desta conversa — recomendo trocá-la no painel da Crefazon antes de colocar isso em produção.**

Nunca commite um arquivo `.env` com valores reais no git. Use um `.gitignore` com `.env` incluído.

## Deploy no Render

Selenium precisa do **Google Chrome instalado no servidor** (diferente do Playwright, que baixa o navegador sozinho). O `render.yaml` já inclui isso no build command.

### Opção A — Blueprint automático (recomendado)
1. Suba esta pasta para um repositório no GitHub (sem incluir nenhum `.env`)
2. No Render, clique em **New > Blueprint**
3. Aponte para o repositório — o Render lê o `render.yaml` e configura a estrutura
4. Preencha manualmente `CREFAZON_LOGIN` e `CREFAZON_SENHA` no painel (ficam como `sync: false` — o Render não define isso sozinho, por segurança)
5. A `API_KEY` é gerada automaticamente

### Opção B — Manual
1. **New > Web Service** apontando pro repositório
2. **Build Command:**
   ```
   apt-get update && apt-get install -y wget gnupg && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && apt-get update && apt-get install -y google-chrome-stable && pip install -r requirements.txt
   ```
3. **Start Command:**
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. Em **Environment**, adicione `API_KEY`, `CREFAZON_LOGIN` e `CREFAZON_SENHA`
5. Plano: use pelo menos o **Starter** — o Chrome + Selenium consome bastante RAM, o plano Free tende a travar ou hibernar no meio da automação

**Se o `apt-get` falhar no ambiente nativo do Render** (algumas contas restringem isso), a alternativa é fazer deploy via **Docker** — nesse caso me avise que monto um `Dockerfile` com Chrome + Chromedriver pré-instalados, que é mais garantido de funcionar.

## Chamando a API (exemplo)

```bash
curl -X POST https://seu-servico.onrender.com/preencher-formulario \
  -H "Content-Type: application/json" \
  -H "X-API-Key: SUA_CHAVE_AQUI" \
  -d '{
    "dados": {
      "cpf": "24748333820",
      "nome": "Leandro Gujev Firmino",
      "data_nascimento": "14/12/1974",
      "telefone": "17996795804",
      "cep": "15501096",
      "ocupacao": "Assalariado",
      "possui_veiculo": true
    }
  }'
```

Resposta:
```json
{"job_id": "a1b2c3d4-...", "status": "na_fila"}
```

Consultando o resultado:
```bash
curl https://seu-servico.onrender.com/status/a1b2c3d4-... \
  -H "X-API-Key: SUA_CHAVE_AQUI"
```

## Próximos passos possíveis

- Trocar o armazenamento de jobs em memória por Redis, se precisar sobreviver a reinícios do serviço
- Adicionar webhook de retorno (a API chama sua aplicação de volta quando o job terminar), em vez de polling em `/status`
- Adicionar retry automático em caso de falha na automação
