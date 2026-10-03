# Memory Schema

CREATE TABLE memory_entries (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,

memory_type VARCHAR(50) NOT NULL,

title VARCHAR(500) NOT NULL,
content TEXT NOT NULL,

importance INTEGER NOT NULL DEFAULT 0,
confidence NUMERIC(4,3),

metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

);

CREATE INDEX idx_memory_type ON memory_entries(memory_type);
CREATE INDEX idx_memory_project ON memory_entries(project_id);
CREATE INDEX idx_memory_company ON memory_entries(company_id);
