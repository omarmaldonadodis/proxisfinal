#!/usr/bin/env python3
# cli/bulk_operations.py
import typer
from rich.console import Console
from rich.progress import Progress
import asyncio
from app.database import AsyncSessionLocal
from app.services.profile_service import ProfileService
from app.schemas.profile import ProfileCreate

app = typer.Typer()
console = Console()

@app.command()
def create_profiles(
    count: int = typer.Argument(..., help="Number of profiles to create"),
    computer_id: int = typer.Option(..., help="Computer ID"),
    proxy_type: str = typer.Option("mobile", help="Proxy type"),
    country: str = typer.Option("ec", help="Country code"),
    auto_warmup: bool = typer.Option(False, help="Auto warmup")
):
    """Create multiple profiles"""
    
    async def _bulk_create():
        async with AsyncSessionLocal() as db:
            service = ProfileService(db)
            
            results = {
                'successful': 0,
                'failed': 0
            }
            
            with Progress() as progress:
                task = progress.add_task(f"Creating {count} profiles...", total=count)
                
                for i in range(count):
                    try:
                        profile_in = ProfileCreate(
                            computer_id=computer_id,
                            name=f"Bulk_Profile_{i+1}",
                            proxy_type=proxy_type,
                            proxy_country=country,
                            auto_warmup=auto_warmup,
                            warmup_duration_minutes=15
                        )
                        
                        await service.create_profile(profile_in)
                        results['successful'] += 1
                        
                    except Exception as e:
                        console.print(f"[red]Error creating profile {i+1}: {e}[/red]")
                        results['failed'] += 1
                    
                    progress.update(task, advance=1)
            
            console.print(f"[green]✓ Bulk creation completed[/green]")
            console.print(f"  Successful: {results['successful']}")
            console.print(f"  Failed: {results['failed']}")
    
    asyncio.run(_bulk_create())

if __name__ == "__main__":
    app()