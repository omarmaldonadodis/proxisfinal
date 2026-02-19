#!/bin/bash
# scripts/cli_docker.sh - Wrapper para ejecutar CLI en Docker

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Función helper
run_in_docker() {
    local script=$1
    shift
    
    echo -e "${YELLOW}🐳 Ejecutando en Docker: ${script}${NC}"
    
    docker exec -it adspower_api python cli/${script}.py "$@"
}

# Comandos disponibles
case "$1" in
    # ========================================
    # PROFILE MANAGEMENT
    # ========================================
    profile:create)
        shift
        run_in_docker "create_profile" create "$@"
        ;;
    
    profile:list)
        shift
        run_in_docker "create_profile" list "$@"
        ;;
    
    profile:bulk)
        shift
        run_in_docker "bulk_operations" create-profiles "$@"
        ;;
    
    # ========================================
    # HEALTH CHECKS
    # ========================================
    health:computers)
        run_in_docker "health_check" computers
        ;;
    
    health:proxies)
        shift
        run_in_docker "health_check" proxies "$@"
        ;;
    
    # ========================================
    # BACKUP MANAGEMENT
    # ========================================
    backup:create)
        echo -e "${YELLOW}📦 Creating backup...${NC}"
        docker exec adspower_api python cli/backup.py create
        ;;
    
    backup:list)
        echo -e "${YELLOW}📋 Listing backups...${NC}"
        docker exec adspower_api python cli/backup.py list
        ;;
    
    backup:restore)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Usage: $0 backup:restore <backup_file>${NC}"
            exit 1
        fi
        echo -e "${RED}⚠️  WARNING: This will overwrite current database!${NC}"
        read -p "Continue? (yes/no) " confirm
        if [ "$confirm" = "yes" ]; then
            docker exec adspower_api python cli/backup.py restore "$2"
        else
            echo -e "${YELLOW}Cancelled${NC}"
        fi
        ;;
    
    # ========================================
    # DOCKER MANAGEMENT
    # ========================================
    docker:logs)
        docker logs -f adspower_api
        ;;
    
    docker:logs:celery)
        docker logs -f adspower_celery_worker
        ;;
    
    docker:restart)
        echo -e "${YELLOW}♻️  Restarting services...${NC}"
        cd docker && docker-compose restart
        ;;
    
    docker:rebuild)
        echo -e "${YELLOW}🔨 Rebuilding containers...${NC}"
        cd docker && docker-compose down && docker-compose up -d --build
        ;;
    
    # ========================================
    # DATABASE OPERATIONS
    # ========================================
    db:migrate)
        echo -e "${YELLOW}🔄 Running migrations...${NC}"
        docker exec adspower_api alembic upgrade head
        ;;
    
    db:shell)
        echo -e "${YELLOW}🐘 Opening PostgreSQL shell...${NC}"
        docker exec -it adspower_postgres psql -U adspower -d adspower_db
        ;;
    
    # ========================================
    # HELP
    # ========================================
    help|*)
        echo ""
        echo -e "${GREEN}🚀 AdsPower Orchestrator - Docker CLI${NC}"
        echo "=========================================="
        echo ""
        echo -e "${YELLOW}Profile Management:${NC}"
        echo "  $0 profile:create --computer-id 1 --name 'Profile Name'"
        echo "  $0 profile:list --limit 20"
        echo "  $0 profile:bulk 10 --computer-id 1 --auto-warmup"
        echo ""
        echo -e "${YELLOW}Health Checks:${NC}"
        echo "  $0 health:computers"
        echo "  $0 health:proxies --limit 50"
        echo ""
        echo -e "${YELLOW}Backup Management:${NC}"
        echo "  $0 backup:create"
        echo "  $0 backup:list"
        echo "  $0 backup:restore <backup_file>"
        echo ""
        echo -e "${YELLOW}Docker Management:${NC}"
        echo "  $0 docker:logs"
        echo "  $0 docker:logs:celery"
        echo "  $0 docker:restart"
        echo "  $0 docker:rebuild"
        echo ""
        echo -e "${YELLOW}Database:${NC}"
        echo "  $0 db:migrate"
        echo "  $0 db:shell"
        echo ""
        ;;
esac