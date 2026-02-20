#!/bin/bash
# =============================================================================
# Script para criar uma nova release/tag
# =============================================================================
# Uso: ./scripts/release.sh [tipo]
# Tipos: patch, minor, major
# Exemplo: ./scripts/release.sh patch  -> v1.0.1
#          ./scripts/release.sh minor  -> v1.1.0
#          ./scripts/release.sh major  -> v2.0.0
# =============================================================================

set -e

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ -z "$1" ]; then
    echo "Uso: $0 [patch|minor|major] [mensagem]"
    echo ""
    echo "Exemplos:"
    echo "  $0 patch           # Cria v1.0.1"
    echo "  $0 minor           # Cria v1.1.0"
    echo "  $0 major           # Cria v2.0.0"
    echo "  $0 patch 'fix XYZ' # Cria v1.0.1 com mensagem customizada"
    exit 1
fi

RELEASE_TYPE="$1"
MESSAGE="${2:-Release}"

# Obtém a versão atual
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/v//' || echo "0.0.0")

# Incrementa versão
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR="${VERSION_PARTS[0]}"
MINOR="${VERSION_PARTS[1]:-0}"
PATCH="${VERSION_PARTS[2]:-0}"

case "$RELEASE_TYPE" in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        echo "Tipo de release inválido: $RELEASE_TYPE"
        exit 1
        ;;
esac

NEW_VERSION="v${MAJOR}.${MINOR}.${PATCH}"

echo -e "${GREEN}Criando release $NEW_VERSION${NC}"
echo ""

# Gera changelog
echo -e "${YELLOW}Gerando changelog...${NC}"
./scripts/generate_changelog.sh "$NEW_VERSION"

echo ""
echo -e "${GREEN}Versão $NEW_VERSION criada!${NC}"
echo ""
echo "Próximos passos:"
echo "  1. Edite o CHANGELOG.md com o output acima"
echo "  2. Execute: git tag -a $NEW_VERSION -m '$MESSAGE'"
echo "  3. Execute: git push origin $NEW_VERSION"
