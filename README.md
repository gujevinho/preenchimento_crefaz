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

Requer Google Chrome instalado na máquina (o `webdriver-manager` baixa o chromedriver compatível automaticamente).

```bash
pip install -r requirements.txt
export CREFAZON_LOGIN="seu_login"
export CREFAZON_SENHA="sua_senha"
export API_KEY="chave-de-teste"
uvicorn main:app --reload
```

Ou, para testar já no ambiente idêntico ao de produção (com Docker):

```bash
docker build -t form-automation-api .
docker run -p 8000:8000 \
  -e CREFAZON_LOGIN="seu_login" \
  -e CREFAZON_SENHA="sua_senha" \
  -e API_KEY="chave-de-teste" \
  -e PORT=8000 \
  form-automation-api
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

## Deploy no Render (via Docker)

O ambiente nativo do Render (Python/Poetry) **não permite `apt-get install`** durante o build — o filesystem é somente leitura fora de um container. Por isso o Selenium precisa ser empacotado com **Docker**, que já vem pronto no projeto (`Dockerfile`).

### Opção A — Blueprint automático (recomendado)
1. Suba esta pasta para o repositório no GitHub (incluindo o `Dockerfile`)
2. No Render, **New > Blueprint**
3. Aponte para o repositório — o `render.yaml` já está configurado com `runtime: docker`
4. Preencha manualmente `CREFAZON_LOGIN` e `CREFAZON_SENHA` no painel de Environment
5. A `API_KEY` é gerada automaticamente

### Opção B — Manual
1. **New > Web Service** apontando pro repositório
2. Em **Language/Runtime**, selecione **Docker** (não Python) — o Render detecta o `Dockerfile` automaticamente
3. Em **Environment**, adicione `API_KEY`, `CREFAZON_LOGIN` e `CREFAZON_SENHA`
4. Plano: use pelo menos o **Starter** — Chrome + Selenium consome bastante RAM, o plano Free tende a travar ou hibernar no meio da automação

⚠️ **Importante:** ao criar o serviço, garanta que o Render está configurado como **Docker**, não Python. Se ele detectar `requirements.txt` e tentar rodar como ambiente Python nativo, vai cair no mesmo erro de `apt-get` que você já viu.

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
