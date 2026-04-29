"""One-time migration to backfill slugs for existing teams."""
import asyncio
import os
import re
import asyncpg


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


async def main():
    dsn = os.environ.get("DATABASE_URL", "postgresql://localhost/locker")
    conn = await asyncpg.connect(dsn)
    # Add column if not exists
    await conn.execute("ALTER TABLE teams ADD COLUMN IF NOT EXISTS slug TEXT UNIQUE")
    rows = await conn.fetch("SELECT id, name FROM teams WHERE slug IS NULL")
    for row in rows:
        slug = slugify(row["name"])
        # Handle duplicates by appending suffix
        base_slug = slug
        counter = 1
        while True:
            try:
                await conn.execute("UPDATE teams SET slug = $1 WHERE id = $2", slug, row["id"])
                print(f"  {row['name']} -> {slug}")
                break
            except asyncpg.UniqueViolationError:
                slug = f"{base_slug}-{counter}"
                counter += 1
    await conn.close()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
