#!/bin/bash
# =============================================================================
# Script para geração automática de CHANGELOG
# =============================================================================
# Uso: ./scripts/generate_changelog.sh [versao]
# Exemplo: ./scripts/generate_changelog.sh v2.1.0
# =============================================================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretório do projeto (raiz do git)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Verifica se é um repositório git
if [ ! -d ".git" ]; then
    echo -e "${RED}Erro: Este não é um repositório git${NC}"
    exit 1
fi

# Obtém a última tag ou usa o argumento
if [ -n "$1" ]; then
    VERSION="$1"
else
    VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
fi

# Função para converter tipo de commit para seção do changelog
get_section() {
    local type="$1"
    case "$type" in
        feat) echo "Added" ;;
        fix) echo "Fixed" ;;
        refactor) echo "Changed" ;;
        perf) echo "Changed" ;;
        docs) echo "Changed" ;;
        style) echo "Changed" ;;
        test) echo "Added" ;;
        chore) echo "Changed" ;;
        *) echo "Changed" ;;
    esac
}

# Função para extrair mensagem do commit
extract_message() {
    local commit="$1"
    # Remove o tipo e escopo (feat(api): )
    echo "$commit" | sed -E 's/^[a-z]+(\([a-z0-9-]+\))?: //' | sed -E 's/^\*\*|(\*\*)+$//g'
}

# Obter commits desde a última tag
echo -e "${GREEN}Gerando changelog desde $VERSION...${NC}"

# Data da tag atual ou data atual
TAG_DATE=$(git log -1 --format=%ai "$VERSION" 2>/dev/null || date +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)

# Inicializa arrays para cada seção
declare -A sections
sections["Added"]=""
sections["Changed"]=""
sections["Fixed"]=""
sections["Removed"]=""
sections["Security"]=""

# Processa commits
COMMITS=$(git log --oneline "$VERSION..HEAD" 2>/dev/null | head -50)

if [ -z "$COMMITS" ]; then
    # Se não há commits desde a tag, pega todos os commits se não houver argumento
    if [ -z "$1" ]; then
        COMMITS=$(git log --oneline -50)
    fi
fi

for line in $COMMITS; do
    # Obtém o hash completo do commit
    commit_hash=$(echo "$line" | awk '{print $1}')
    
    # Obtém a mensagem completa do commit
    full_message=$(git log -1 --format=%s "$commit_hash")
    
    # Extrai o tipo de commit
    type=$(echo "$full_message" | sed -E 's/^([a-z]+)(\([a-z0-9-]+\))?:.*/\1/')
    
    # Obtém a seção apropriada
    section=$(get_section "$type")
    
    # Formata a entrada
    entry="- $(extract_message "$full_message")"
    
    # Adiciona à seção apropriada
    sections["$section"]="${sections["$section"]}\n${entry}"
done

# Gera o changelog
echo ""
echo "## [$VERSION] - $TODAY"

for section_name in "Added" "Changed" "Fixed" "Removed" "Security"; do
    if [ -n "${sections[$section_name]}" ]; then
        echo ""
        echo "### $section_name"
        echo -e "${sections[$section_name]}"
    fi
done

echo ""
echo "---

*Gerado automaticamente em $TODAY*"
