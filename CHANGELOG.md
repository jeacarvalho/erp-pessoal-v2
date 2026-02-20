# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-02-20
### Added
- Configuração centralizada de ambientes via variáveis de ambiente
- Módulo `backend/app/config.py` com classe Config singleton
- Variável `BACKEND_URL` para frontends web (Streamlit, Flet)
- Variável `API_BASE_URL` para configuração do backend
- Documentação completa de DEV/PROD no AGENTS.md

### Changed
- `web/app_streamlit.py`: URL do backend agora configurável via env var
- `web/app/main.py`: URL do backend agora configurável via env var
- `web/app/main_web.py`: URL do backend agora configurável via env var
- `docker-compose.yml`: Adicionadas variáveis de ambiente para API
- `.env.example`: Documentação completa das variáveis

### Fixed
- Correção de importação duplicada do FastAPI em `backend/app/main.py`
- Adição de importação faltando do `Generator` em `backend/app/main.py`

## [2.0.0] - 2026-02-11
### Added
- App mobile com scanner NFC-e e design system
- Docker e pipeline CI/CD para deploy manual
- Configuração básica para deploy em produção
- Integração API com Axios e tratamento robusto de erros
- Importação bulk de arquivos XML na web app
- Testes unitários para validação de importação XML
- Correção de inconsistência no campo EAN

### Changed
- Migração para nova estrutura do projeto

## [1.0.0] - 2026-02-10
### Added
- Primeira versão funcional do ERP Pessoal
- Backend FastAPI com SQLAlchemy
- Interface Streamlit para dashboard
- Interface Flet para desktop
- Importação de notas fiscais via XML
- Importação de notas fiscais via URL (scraping)
- Categorização de gastos
- Cadastro de produtos por EAN
- Mapeamento automático de produtos

---

## Formato de Commits

Este projeto segue o padrão [Conventional Commits](https://www.conventionalcommits.org/):

```
<tipo>(<escopo>): <descrição>

Exemplos:
feat(api): adiciona endpoint de categorias
fix(scraper): corrige parsing de URL específica
docs(readme): atualiza instruções de instalação
refactor(models): simplifica relação entre entidades
test(api): adiciona teste de integração
```

### Tipos de Commit

| Tipo | Descrição |
|------|-----------|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `docs` | Documentação |
| `style` | Formatação (sem mudança de código) |
| `refactor` | Refatoração |
| `test` | Adição/atualização de testes |
| `chore` | Tarefas de manutenção |

---

## Como Gerar Changelog

```bash
# Gerar changelog desde a última tag
./scripts/generate_changelog.sh

# Criar nova versão
git tag -a v2.1.0 -m "Release v2.1.0"
git push origin v2.1.0
```
