#!/usr/bin/env python3
# cli/health_check.py
import typer
from rich.console import Console
from rich.table import Table
import asyncio
from app.database import AsyncSessionLocal
from app.services.computer_service import ComputerService
from app.services.proxy_service import ProxyService

app = typer.Typer()
console = Console()

@app.command()
def computers():
    """Health check all computers"""
    
    async def _check():
        async with AsyncSessionLocal() as db:
            service = ComputerService(db)
            
            computers_list, _ = await service.list_computers(limit=1000)
            
            table = Table(title="Computers Health Check")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("AdsPower", style="magenta")
            table.add_column("Profiles", style="blue")
            
            for computer in computers_list:
                console.print(f"[yellow]Checking {computer.name}...[/yellow]")
                
                health = await service.health_check(computer.id)
                
                status_icon = "✓" if health['is_healthy'] else "✗"
                adspower_icon = "✓" if health['adspower_connected'] else "✗"
                
                table.add_row(
                    str(computer.id),
                    computer.name,
                    f"{status_icon} {computer.status.value}",
                    f"{adspower_icon}",
                    f"{health['current_profiles']}/{health['max_profiles']}"
                )
            
            console.print(table)
    
    asyncio.run(_check())

@app.command()
def proxies(limit: int = typer.Option(50, help="Max proxies to check")):
    """Health check proxies"""
    
    async def _check():
        async with AsyncSessionLocal() as db:
            service = ProxyService(db)
            
            console.print(f"[yellow]Checking up to {limit} proxies...[/yellow]")
            
            result = await service.health_check_batch(limit=limit)
            
            console.print(f"[green]✓ Health check completed[/green]")
            console.print(f"  Total checked: {result['total']}")
            console.print(f"  Successful: {result['success']}")
            console.print(f"  Failed: {result['failed']}")
    
    asyncio.run(_check())

if __name__ == "__main__":
    app()