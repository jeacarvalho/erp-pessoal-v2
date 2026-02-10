# ERP Pessoal - Soberania de Dados

Este repositório contém um ERP Pessoal focado em soberania de dados, com os seguintes componentes:

- Backend: FastAPI + SQLite
- Web: Flet (frontend web)
- Mobile: Flet (aplicativo móvel com leitura de notas via QR Code)

## Estrutura de Pastas

- `backend/`
  - `app/`
  - `tests/`
- `web/`
  - `app/`
  - `tests/`
- `mobile/`
  - `app/`
  - `tests/`

## Executando o Backend com Docker

Certifique-se de ter o Docker e o Docker Compose instalados.

```bash
docker compose up --build
```

O backend ficará disponível em `http://localhost:8000`.

## Pipeline de CI (GitHub Actions)

A pipeline de CI é executada em todo `push` ou `pull_request` para a branch `main` e:

- Configura Python 3.10.
- Instala as dependências definidas em `requirements.txt`.
- Executa `pytest` recursivamente em todo o projeto.

