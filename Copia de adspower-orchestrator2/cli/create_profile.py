#!/usr/bin/env python3
# cli/create_profile.py
import typer
from rich.console import Console
from rich.table import Table
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.services.profile_service import ProfileService
from app.schemas.profile import ProfileCreate

app = typer.Typer()
console = Console()

@app.command()
def create(
    computer_id: int = typer.Option(..., help="Computer ID"),
    name: str = typer.Option(None, help="Profile name"),
    proxy_type: str = typer.Option("mobile", help="Proxy type: mobile or residential"),
    country: str = typer.Option("ec", help="Country code"),
    city: str = typer.Option(None, help="City name"),
    auto_warmup: bool = typer.Option(False, help="Auto warmup profile"),
    warmup_duration: int = typer.Option(20, help="Warmup duration in minutes")
):
    """Create a new profile"""
    
    async def _create():
        async with AsyncSessionLocal() as db:
            service = ProfileService(db)
            
            profile_in = ProfileCreate(
                computer_id=computer_id,
                name=name,
                proxy_type=proxy_type,
                proxy_country=country,
                proxy_city=city,
                auto_warmup=auto_warmup,
                warmup_duration_minutes=warmup_duration
            )
            
            console.print(f"[yellow]Creating profile on computer {computer_id}...[/yellow]")
            
            try:
                profile = await service.create_profile(profile_in)
                
                console.print(f"[green]✓ Profile created successfully![/green]")
                console.print(f"  ID: {profile.id}")
                console.print(f"  Name: {profile.name}")
                console.print(f"  AdsPower ID: {profile.adspower_id}")
                console.print(f"  Status: {profile.status}")
                
                if auto_warmup:
                    console.print(f"[yellow]  Warmup task started ({warmup_duration} minutes)[/yellow]")
                
            except Exception as e:
                console.print(f"[red]✗ Error: {e}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_create())

@app.command()
def list(
    computer_id: int = typer.Option(None, help="Filter by computer ID"),
    limit: int = typer.Option(20, help="Max results")
):
    """List profiles"""
    
    async def _list():
        async with AsyncSessionLocal() as db:
            service = ProfileService(db)
            
            profiles, total = await service.list_profiles(
                skip=0,
                limit=limit,
                computer_id=computer_id
            )
            
            table = Table(title=f"Profiles (Total: {total})")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("AdsPower ID", style="yellow")
            table.add_column("Computer", style="magenta")
            table.add_column("Status", style="blue")
            table.add_column("Warmed", style="white")
            
            for profile in profiles:
                table.add_row(
                    str(profile.id),
                    profile.name,
                    profile.adspower_id,
                    f"Computer {profile.computer_id}",
                    profile.status.value,
                    "✓" if profile.is_warmed else "✗"
                )
            
            console.print(table)
    
    asyncio.run(_list())

if __name__ == "__main__":
    app()