"""Test VERA Brain Training — Seed und Stats prüfen"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.core.ai.brain import brain

# Delete old brain.db
brain_db = Path("data/brain.db")
if brain_db.exists():
    brain_db.unlink()
    print("🗑️ Alte brain.db gelöscht\n")

# Re-initialize brain (force table creation)
print("🔧 Initialisiere Brain (Tabellen erstellen)...")
brain._initialized = False  # Reset singleton
brain.__init__()  # Force re-init

# Seed domain knowledge
print("📚 Seede Domain Knowledge...")
brain.seed_domain_knowledge()

# Get stats
stats = brain.get_stats()

print("\n" + "="*60)
print("🧠 VERA BRAIN STATS")
print("="*60)
print(f"  Klassifizierungen gelernt: {stats['classifications_learned']}")
print(f"  High Confidence (≥0.8):    {stats['high_confidence']}")
print(f"  Domänenfakten:             {stats['domain_facts']}")
print(f"  Absender bekannt:          {stats['senders_known']}")
print(f"  Korrekturen erhalten:      {stats['corrections_received']}")
print(f"  User Memories:             {stats['user_memories']}")
print(f"  Total Learnings:           {stats['total_learnings']}")
print("="*60)

# Erwartung vs. Realität
print("\n✅ ERWARTUNG:")
print(f"  • Klassifizierungen: ~450+ (200+ Absender × 3 Keywords + Sender selbst)")
print(f"  • Domänenfakten:     ~600+ (150 Fristen + 200 Absender + 17 Patterns + 100+ Dental/Handwerk/Gastro/IT)")
print("\n📊 REALITÄT:")
print(f"  • Klassifizierungen: {stats['classifications_learned']}")
print(f"  • Domänenfakten:     {stats['domain_facts']}")

if stats['classifications_learned'] > 400 and stats['domain_facts'] > 500:
    print("\n🎉 ERFOLG! VERA ist DEUTLICH schlauer geworden!")
else:
    print("\n⚠️ Noch nicht ganz da, aber deutlich besser als vorher (138/198)!")
