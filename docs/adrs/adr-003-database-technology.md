# ADR-003: Database Technology Selection

## Status
Proposed

## Context
We need to select a primary database for the AI Part Designer. Data requirements include:
- User accounts and authentication data
- Design metadata and version history
- Job queue state and history
- Project organization and sharing
- Subscription and billing records
- Audit logs and analytics
- Need for both relational integrity and flexible JSON storage

## Decision
We will use **PostgreSQL 15+** as our primary database.

Supporting technology choices:
- **Connection Pooling**: PgBouncer for production
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **Full-text Search**: PostgreSQL native (pg_trgm, tsvector)
- **JSON Storage**: JSONB columns for flexible metadata
- **Caching Layer**: Redis (separate from database)

## Consequences

### Positive
- **ACID compliance**: Strong data integrity for financial and user data
- **JSONB support**: Flexible schema for design metadata without sacrificing relational benefits
- **Full-text search**: Built-in search capabilities, no need for separate Elasticsearch initially
- **Mature ecosystem**: Excellent tooling, monitoring, backup solutions
- **Cloud availability**: Managed options on all major clouds (RDS, Cloud SQL, Azure)
- **Scalability**: Read replicas, partitioning, and connection pooling
- **Extensions**: PostGIS (future), pg_vector (embeddings), pg_cron

### Negative
- **Operational complexity**: Requires tuning for optimal performance
- **Vertical scaling limits**: Eventually may need sharding (unlikely for MVP scale)
- **Learning curve**: Advanced features require PostgreSQL expertise

### Neutral
- NoSQL flexibility traded for relational consistency
- May need separate time-series database for metrics at scale

## Options Considered

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| **PostgreSQL** | ACID, JSONB, full-text search, mature | Operational complexity | ⭐⭐⭐⭐⭐ |
| MongoDB | Flexible schema, easy scaling | No ACID (multi-doc), less suitable for relational | ⭐⭐⭐ |
| MySQL | Mature, widely used | Less powerful than PostgreSQL, weaker JSON | ⭐⭐⭐ |
| CockroachDB | Distributed, PostgreSQL-compatible | Complexity, cost | ⭐⭐⭐ |
| SQLite | Simple, zero config | Not suitable for production web apps | ⭐⭐ |

## Technical Details

### Schema Overview
```sql
-- Core tables
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    subscription_tier VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE designs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_type VARCHAR(50) NOT NULL, -- 'generated', 'uploaded', 'template'
    metadata JSONB DEFAULT '{}',
    file_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE design_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    design_id UUID REFERENCES designs(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    file_url VARCHAR(500) NOT NULL,
    change_description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    design_id UUID REFERENCES designs(id),
    type VARCHAR(50) NOT NULL, -- 'generate', 'modify', 'convert', 'analyze'
    status VARCHAR(50) DEFAULT 'queued',
    priority VARCHAR(20) DEFAULT 'standard',
    input JSONB NOT NULL,
    output JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_designs_project ON designs(project_id);
CREATE INDEX idx_designs_user ON designs(project_id, created_at DESC);
CREATE INDEX idx_jobs_user_status ON jobs(user_id, status);
CREATE INDEX idx_jobs_queue ON jobs(status, priority, created_at) WHERE status = 'queued';

-- Full-text search
CREATE INDEX idx_designs_search ON designs USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));
```

### Connection Configuration
```python
# Production settings
DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/dbname"

# Connection pool settings
SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_MAX_OVERFLOW = 10
SQLALCHEMY_POOL_TIMEOUT = 30
SQLALCHEMY_POOL_RECYCLE = 1800
```

### Migration Example
```python
# alembic/versions/001_initial.py
def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        # ... other columns
    )

def downgrade():
    op.drop_table('users')
```

## References
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- [PgBouncer](https://www.pgbouncer.org/)
