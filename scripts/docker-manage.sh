#!/bin/bash

# Docker Management Script for Chat Platform
# This script provides various management commands for the Docker setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show help
show_help() {
    echo "Docker Management Script for Chat Platform"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start [dev|prod|core]  - Start services"
    echo "  stop                   - Stop all services"
    echo "  restart [dev|prod|core] - Restart services"
    echo "  status                 - Show service status"
    echo "  logs [service]         - Show logs for service"
    echo "  shell [service]        - Open shell in service container"
    echo "  build                  - Build application image"
    echo "  clean                  - Clean up containers and images"
    echo "  backup                 - Backup database and Redis data"
    echo "  restore                - Restore from backup"
    echo "  health                 - Check service health"
    echo "  stats                  - Show resource usage"
    echo "  help                   - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start dev           - Start development environment"
    echo "  $0 logs app            - Show application logs"
    echo "  $0 shell postgres      - Open PostgreSQL shell"
    echo "  $0 backup              - Backup all data"
}

# Start services
start_services() {
    local profile="${1:-dev}"
    
    case $profile in
        "dev")
            print_status "Starting development environment..."
            docker-compose --profile development up -d
            ;;
        "prod")
            print_status "Starting production environment..."
            docker-compose --profile production up -d
            ;;
        "core")
            print_status "Starting core services..."
            docker-compose up -d postgres redis app
            ;;
        *)
            print_error "Invalid profile: $profile"
            echo "Valid profiles: dev, prod, core"
            exit 1
            ;;
    esac
    
    print_success "Services started with profile: $profile"
    show_status
}

# Stop services
stop_services() {
    print_status "Stopping all services..."
    docker-compose down
    print_success "All services stopped"
}

# Restart services
restart_services() {
    local profile="${1:-dev}"
    
    print_status "Restarting services with profile: $profile"
    docker-compose down
    start_services "$profile"
}

# Show service status
show_status() {
    print_status "Service Status:"
    docker-compose ps
    
    echo ""
    print_status "Service URLs:"
    echo "  🌐 Application: http://localhost:8000"
    echo "  📊 API Docs: http://localhost:8000/docs"
    echo "  ❤️  Health Check: http://localhost:8000/health"
    echo "  📈 Cache Stats: http://localhost:8000/cache/stats"
    
    if docker-compose ps | grep -q "pgadmin"; then
        echo "  🗄️  PgAdmin: http://localhost:5050"
    fi
    
    if docker-compose ps | grep -q "redis-commander"; then
        echo "  🔴 Redis Commander: http://localhost:8081"
    fi
    
    if docker-compose ps | grep -q "nginx"; then
        echo "  🌍 Nginx (Production): http://localhost"
    fi
}

# Show logs
show_logs() {
    local service="${1:-app}"
    
    print_status "Showing logs for service: $service"
    docker-compose logs -f "$service"
}

# Open shell in service
open_shell() {
    local service="${1:-app}"
    
    print_status "Opening shell in service: $service"
    
    case $service in
        "postgres")
            docker-compose exec postgres psql -U postgres -d chat_platform
            ;;
        "redis")
            docker-compose exec redis redis-cli -a redis_password
            ;;
        *)
            docker-compose exec "$service" /bin/bash
            ;;
    esac
}

# Build application
build_app() {
    print_status "Building application image..."
    docker-compose build app
    print_success "Application image built"
}

# Clean up
clean_up() {
    print_warning "This will remove all containers, images, and volumes. Are you sure? (y/N)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Cleaning up Docker resources..."
        
        # Stop and remove containers
        docker-compose down -v
        
        # Remove images
        docker-compose down --rmi all
        
        # Remove volumes
        docker volume prune -f
        
        # Remove unused images
        docker image prune -f
        
        print_success "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Backup data
backup_data() {
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    
    print_status "Creating backup in $backup_dir..."
    mkdir -p "$backup_dir"
    
    # Backup PostgreSQL
    print_status "Backing up PostgreSQL database..."
    docker-compose exec -T postgres pg_dump -U postgres chat_platform > "$backup_dir/postgres_backup.sql"
    
    # Backup Redis
    print_status "Backing up Redis data..."
    docker-compose exec -T redis redis-cli -a redis_password --rdb /data/dump.rdb
    docker cp "$(docker-compose ps -q redis):/data/dump.rdb" "$backup_dir/redis_backup.rdb"
    
    # Create backup info
    cat > "$backup_dir/backup_info.txt" << EOF
Backup created: $(date)
Services: postgres, redis
PostgreSQL version: $(docker-compose exec -T postgres psql -U postgres -t -c "SELECT version();")
Redis version: $(docker-compose exec -T redis redis-cli -a redis_password --version)
EOF
    
    print_success "Backup completed: $backup_dir"
}

# Restore data
restore_data() {
    local backup_dir="$1"
    
    if [ -z "$backup_dir" ]; then
        print_error "Please specify backup directory"
        echo "Usage: $0 restore <backup_directory>"
        exit 1
    fi
    
    if [ ! -d "$backup_dir" ]; then
        print_error "Backup directory not found: $backup_dir"
        exit 1
    fi
    
    print_warning "This will restore data from backup. Are you sure? (y/N)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Restoring data from $backup_dir..."
        
        # Restore PostgreSQL
        if [ -f "$backup_dir/postgres_backup.sql" ]; then
            print_status "Restoring PostgreSQL database..."
            docker-compose exec -T postgres psql -U postgres -d chat_platform < "$backup_dir/postgres_backup.sql"
        fi
        
        # Restore Redis
        if [ -f "$backup_dir/redis_backup.rdb" ]; then
            print_status "Restoring Redis data..."
            docker cp "$backup_dir/redis_backup.rdb" "$(docker-compose ps -q redis):/data/dump.rdb"
            docker-compose restart redis
        fi
        
        print_success "Data restored from $backup_dir"
    else
        print_status "Restore cancelled"
    fi
}

# Check health
check_health() {
    print_status "Checking service health..."
    
    # Check application health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Application is healthy"
    else
        print_error "Application is not responding"
    fi
    
    # Check PostgreSQL
    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        print_success "PostgreSQL is healthy"
    else
        print_error "PostgreSQL is not responding"
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli -a redis_password ping > /dev/null 2>&1; then
        print_success "Redis is healthy"
    else
        print_error "Redis is not responding"
    fi
}

# Show resource usage
show_stats() {
    print_status "Resource usage:"
    docker stats --no-stream
}

# Main execution
main() {
    case "${1:-help}" in
        "start")
            start_services "$2"
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services "$2"
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs "$2"
            ;;
        "shell")
            open_shell "$2"
            ;;
        "build")
            build_app
            ;;
        "clean")
            clean_up
            ;;
        "backup")
            backup_data
            ;;
        "restore")
            restore_data "$2"
            ;;
        "health")
            check_health
            ;;
        "stats")
            show_stats
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function
main "$@"
