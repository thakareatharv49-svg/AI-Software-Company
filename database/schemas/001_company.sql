# Company Core Schema

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE companies (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name VARCHAR(255) NOT NULL,
mission TEXT,
status VARCHAR(50) NOT NULL DEFAULT 'active',
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE company_settings (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
key VARCHAR(255) NOT NULL,
value JSONB NOT NULL,
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

```
UNIQUE(company_id, key)
```

);
