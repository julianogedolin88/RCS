# RCS

MVP para envio de mensagens **RCS for Business (Google RBM)** com Rich Card, imagem e botão de ação.

## Objetivo inicial

- enviar Rich Card para um número em E.164 (ex.: `+5518999999999`)
- imagem por URL HTTPS pública
- título e descrição
- botão `Abrir URL`
- disparo para uma lista de destinatários
- consulta de capacidades RCS do aparelho
- endpoint de webhook preparado para evolução
- credenciais sempre fora do Git

## Stack

- Python 3.12
- FastAPI
- Google Service Account / OAuth2
- Docker

## Configuração

1. Copie `.env.example` para `.env`.
2. Informe o `RCS_AGENT_ID`.
3. Aponte `GOOGLE_SERVICE_ACCOUNT_FILE` para o JSON da Service Account ou use `GOOGLE_SERVICE_ACCOUNT_JSON`.
4. Para números brasileiros, mantenha `RCS_API_REGION=us` (endpoint recomendado para prefixos `+5`).

Nunca faça commit da chave JSON da Service Account.

## Executar localmente

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abra `http://localhost:8000`.

## Docker

```bash
docker build -t rcs-mvp .
docker run --rm -p 8000:8000 --env-file .env -v /caminho/credencial.json:/run/secrets/rcs-service-account.json:ro rcs-mvp
```

## Endpoints

- `GET /health`
- `GET /api/v1/rcs/capabilities/{phone}`
- `POST /api/v1/rcs/send`
- `POST /api/v1/rcs/broadcast`
- `POST /api/v1/rcs/webhook`

### Exemplo de envio

```json
{
  "phone": "+5518999999999",
  "title": "Oferta especial",
  "description": "Veja os detalhes da condição disponível para você.",
  "image_url": "https://seu-dominio.com/imagens/oferta.jpg",
  "button_text": "Ver detalhes",
  "button_url": "https://seu-dominio.com/oferta",
  "traffic_type": "PROMOTION"
}
```

## Observações do Google RCS for Business

- O destinatário precisa estar habilitado e acessível via RCS for Business.
- Rich Cards aceitam mídia, título, descrição e ações sugeridas.
- O botão `Abrir URL` usa uma suggested action.
- `messageTrafficType` é enviado explicitamente pelo projeto.
- O telefone deve estar em formato E.164.

## Próximas etapas

1. conectar o Agent ID e a Service Account reais;
2. realizar o primeiro envio em dispositivo de teste;
3. persistir campanhas e resultados em banco;
4. processar eventos de entrega/leitura e cliques do webhook;
5. adicionar fila para grandes lotes, retentativas e controle de opt-in/opt-out;
6. adicionar fallback opcional para outro canal quando o número não tiver RCS.
