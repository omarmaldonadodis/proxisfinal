#!/usr/bin/env python3
"""
Script para verificar sincronización entre DB y AdsPower
Compara proxies en DB vs proxies en AdsPower
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.proxy import Proxy
from app.models.profile import Profile
from app.models.computer import Computer
from app.integrations.adspower_client import AdsPowerClient
from loguru import logger

async def verify_sync():
    """Verifica que los proxies en DB coincidan con AdsPower"""
    
    async with AsyncSessionLocal() as db:
        # Obtener todos los proxies activos
        result = await db.execute(
            select(Proxy).where(Proxy.status == "active")
        )
        proxies = list(result.scalars().all())
        
        print(f"\n{'='*80}")
        print(f"VERIFICACIÓN DE SINCRONIZACIÓN DB ↔ ADSPOWER")
        print(f"{'='*80}\n")
        print(f"📊 Total proxies activos en DB: {len(proxies)}\n")
        
        total_profiles = 0
        synced = 0
        not_synced = 0
        errors = 0
        
        for proxy in proxies:
            # Obtener profiles que usan este proxy
            result = await db.execute(
                select(Profile).where(Profile.proxy_id == proxy.id)
            )
            profiles = list(result.scalars().all())
            
            if not profiles:
                continue
            
            total_profiles += len(profiles)
            
            print(f"{'─'*80}")
            print(f"🔍 Proxy #{proxy.id}: {proxy.city}, {proxy.country}")
            print(f"   Username: {proxy.username[:50]}...")
            print(f"   Profiles: {len(profiles)}")
            print(f"{'─'*80}")
            
            for profile in profiles:
                # Obtener computer
                result = await db.execute(
                    select(Computer).where(Computer.id == profile.computer_id)
                )
                computer = result.scalar_one_or_none()
                
                if not computer:
                    print(f"   ❌ Profile {profile.id}: Computer no encontrado")
                    errors += 1
                    continue
                
                try:
                    # Conectar a AdsPower
                    client = AdsPowerClient(
                        api_url=computer.adspower_api_url,
                        api_key=computer.adspower_api_key
                    )
                    
                    # Obtener datos del profile en AdsPower
                    adspower_data = await client.get_profile(profile.adspower_id)
                    
                    # Verificar proxy
                    adspower_proxy = adspower_data.get("user_proxy_config", {})
                    
                    db_proxy_user = proxy.username
                    adspower_proxy_user = adspower_proxy.get("proxy_user", "")
                    
                    if db_proxy_user == adspower_proxy_user:
                        print(f"   ✅ Profile {profile.id} ({profile.name}): SINCRONIZADO")
                        synced += 1
                    else:
                        print(f"   ❌ Profile {profile.id} ({profile.name}): DESINCRONIZADO")
                        print(f"      DB:       {db_proxy_user[:40]}...")
                        print(f"      AdsPower: {adspower_proxy_user[:40]}...")
                        not_synced += 1
                
                except Exception as e:
                    print(f"   ❌ Profile {profile.id}: Error - {str(e)[:60]}")
                    errors += 1
            
            print()
        
        print(f"{'='*80}")
        print(f"RESUMEN")
        print(f"{'='*80}")
        print(f"Total profiles verificados: {total_profiles}")
        print(f"✅ Sincronizados:          {synced}")
        print(f"❌ Desincronizados:        {not_synced}")
        print(f"⚠️  Errores:                {errors}")
        
        if not_synced > 0:
            print(f"\n💡 SOLUCIÓN:")
            print(f"   Ejecutar: POST /api/v1/proxy-rotation/sync-all")
            print(f"   O manualmente: curl -X POST http://localhost:8000/api/v1/proxy-rotation/sync-all")
        
        print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(verify_sync())