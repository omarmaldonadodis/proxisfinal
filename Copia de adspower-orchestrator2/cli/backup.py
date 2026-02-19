#!/usr/bin/env python3
# cli/backup.py
import typer
from rich.console import Console
from rich.progress import Progress
import subprocess
import os
from datetime import datetime
from app.config import settings

app = typer.Typer()
console = Console()

@app.command()
def create(
    output_dir: str = typer.Option(settings.BACKUP_PATH, help="Output directory")
):
    """Create database backup"""
    
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(output_dir, f'backup_{timestamp}.sql')
        
        console.print(f"[yellow]Creating backup...[/yellow]")
        console.print(f"Output: {backup_file}")
        
        # Parse DATABASE_SYNC_URL
        db_url = settings.DATABASE_SYNC_URL
        parts = db_url.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        host_port = host_db[0].split(':')
        
        user = user_pass[0]
        password = user_pass[1]
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        dbname = host_db[1]
        
        # Execute pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Backing up...", total=100)
            
            command = [
                'pg_dump',
                '-h', host,
                '-p', port,
                '-U', user,
                '-d', dbname,
                '-f', backup_file,
                '--format=plain',
                '--no-owner',
                '--no-acl'
            ]
            
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            progress.update(task, completed=100)
        
        if result.returncode == 0:
            file_size = os.path.getsize(backup_file)
            console.print(f"[green]✓ Backup created successfully![/green]")
            console.print(f"  File: {backup_file}")
            console.print(f"  Size: {file_size / 1024 / 1024:.2f} MB")
        else:
            console.print(f"[red]✗ Backup failed![/red]")
            console.print(f"Error: {result.stderr}")
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def restore(
    backup_file: str = typer.Argument(..., help="Backup file to restore")
):
    """Restore database from backup"""
    
    if not os.path.exists(backup_file):
        console.print(f"[red]✗ Backup file not found: {backup_file}[/red]")
        raise typer.Exit(1)
    
    confirm = typer.confirm("⚠️  This will overwrite the current database. Continue?")
    if not confirm:
        console.print("[yellow]Restore cancelled[/yellow]")
        raise typer.Exit(0)
    
    try:
        console.print(f"[yellow]Restoring from backup...[/yellow]")
        console.print(f"File: {backup_file}")
        
        # Parse DATABASE_SYNC_URL
        db_url = settings.DATABASE_SYNC_URL
        parts = db_url.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        host_port = host_db[0].split(':')
        
        user = user_pass[0]
        password = user_pass[1]
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        dbname = host_db[1]
        
        # Execute psql
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Restoring...", total=100)
            
            command = [
                'psql',
                '-h', host,
                '-p', port,
                '-U', user,
                '-d', dbname,
                '-f', backup_file
            ]
            
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            progress.update(task, completed=100)
        
        if result.returncode == 0:
            console.print(f"[green]✓ Database restored successfully![/green]")
        else:
            console.print(f"[red]✗ Restore failed![/red]")
            console.print(f"Error: {result.stderr}")
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def list(
    backup_dir: str = typer.Option(settings.BACKUP_PATH, help="Backup directory")
):
    """List available backups"""
    
    if not os.path.exists(backup_dir):
        console.print(f"[yellow]No backups found in {backup_dir}[/yellow]")
        return
    
    files = [
        f for f in os.listdir(backup_dir)
        if f.startswith('backup_') and f.endswith('.sql')
    ]
    
    if not files:
        console.print(f"[yellow]No backups found[/yellow]")
        return
    
    files.sort(reverse=True)
    
    from rich.table import Table
    
    table = Table(title=f"Available Backups ({len(files)})")
    table.add_column("File", style="cyan")
    table.add_column("Date", style="green")
    table.add_column("Size", style="yellow")
    
    for f in files:
        filepath = os.path.join(backup_dir, f)
        size = os.path.getsize(filepath)
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        
        table.add_row(
            f,
            mtime.strftime('%Y-%m-%d %H:%M:%S'),
            f"{size / 1024 / 1024:.2f} MB"
        )
    
    console.print(table)

if __name__ == "__main__":
    app()