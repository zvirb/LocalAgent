#!/bin/bash
# LocalAgent CLI Autocomplete Docker Entrypoint
# Ensures proper initialization of autocomplete features in container

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}LocalAgent CLI with Autocomplete${NC}"
echo "======================================="

# Check environment
echo -e "${YELLOW}Checking environment...${NC}"

# Ensure directories exist with correct permissions
mkdir -p "$LOCALAGENT_HOME/autocomplete" \
         "$LOCALAGENT_HOME/config" \
         "/app/logs" \
         "/app/.cache"

# Initialize autocomplete if not already done
if [ ! -f "$LOCALAGENT_HOME/autocomplete_history.json" ] && \
   [ ! -f "$LOCALAGENT_HOME/autocomplete_history.enc" ]; then
    echo -e "${YELLOW}Initializing autocomplete history...${NC}"
    cat > "$LOCALAGENT_HOME/autocomplete_history.json" <<EOF
{
  "version": "1.0",
  "entries": [],
  "command_frequency": {},
  "command_success_rate": {}
}
EOF
    chmod 600 "$LOCALAGENT_HOME/autocomplete_history.json"
    echo -e "${GREEN}✓ Autocomplete history initialized${NC}"
fi

# Copy default config if not exists
if [ ! -f "$LOCALAGENT_HOME/autocomplete_config.yaml" ]; then
    if [ -f "/app/docker/config/autocomplete_config.yaml" ]; then
        cp /app/docker/config/autocomplete_config.yaml "$LOCALAGENT_HOME/"
        echo -e "${GREEN}✓ Autocomplete config installed${NC}"
    fi
fi

# Set terminal capabilities for autocomplete
export TERM=${TERM:-xterm-256color}
export COLUMNS=${COLUMNS:-120}
export LINES=${LINES:-40}

# Test autocomplete functionality
echo -e "${YELLOW}Testing autocomplete...${NC}"
python -c "
try:
    from app.cli.intelligence.autocomplete_history import AutocompleteHistoryManager
    from app.cli.intelligence.command_intelligence import CommandIntelligenceEngine
    print('✓ Autocomplete modules loaded successfully')
except Exception as e:
    print(f'⚠ Warning: {e}')
" || true

# Check if running in interactive mode
if [ -t 0 ] ; then
    echo -e "${GREEN}Interactive mode detected - autocomplete enabled${NC}"
    export LOCALAGENT_AUTOCOMPLETE_INTERACTIVE=true
else
    echo -e "${YELLOW}Non-interactive mode - autocomplete suggestions only${NC}"
    export LOCALAGENT_AUTOCOMPLETE_INTERACTIVE=false
fi

# Display autocomplete shortcuts
echo ""
echo "Autocomplete Keyboard Shortcuts:"
echo "================================"
echo "  Tab       - Complete with suggestion"
echo "  ↑/↓       - Navigate suggestions"
echo "  Enter     - Accept input/suggestion"
echo "  Escape    - Hide suggestions"
echo "  Ctrl+W    - Delete word"
echo "  Ctrl+U/K  - Delete to beginning/end"
echo ""

# Check for API keys and providers
echo -e "${YELLOW}Checking providers...${NC}"
if [ -n "$OPENAI_API_KEY" ]; then
    echo -e "${GREEN}✓ OpenAI configured${NC}"
fi
if [ -n "$GEMINI_API_KEY" ]; then
    echo -e "${GREEN}✓ Gemini configured${NC}"
fi
if [ -n "$PERPLEXITY_API_KEY" ]; then
    echo -e "${GREEN}✓ Perplexity configured${NC}"
fi

# Check Ollama connection
if curl -s -o /dev/null -w "%{http_code}" http://ollama:11434/api/tags | grep -q "200"; then
    echo -e "${GREEN}✓ Ollama connected${NC}"
else
    echo -e "${YELLOW}⚠ Ollama not available${NC}"
fi

# Check Redis connection
if python -c "import redis; r = redis.from_url('${REDIS_URL}'); r.ping()" 2>/dev/null; then
    echo -e "${GREEN}✓ Redis connected${NC}"
else
    echo -e "${YELLOW}⚠ Redis not available${NC}"
fi

echo ""
echo -e "${GREEN}Ready! Starting LocalAgent CLI...${NC}"
echo "======================================="
echo ""

# Execute the main command
exec "$@"