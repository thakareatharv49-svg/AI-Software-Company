# Agent Schema

CREATE TABLE agents (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

```
name VARCHAR(255) NOT NULL,
role VARCHAR(255) NOT NULL,
description TEXT,

version VARCHAR(50) NOT NULL DEFAULT '1.0.0',

status VARCHAR(50) NOT NULL DEFAULT 'available',

model_config JSONB NOT NULL DEFAULT '{}'::jsonb,
capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
permissions JSONB NOT NULL DEFAULT '{}'::jsonb,
resource_limits JSONB NOT NULL DEFAULT '{}'::jsonb,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

UNIQUE(company_id, name)
```

);

CREATE TABLE agent_runs (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
task_id UUID,

model_name VARCHAR(255),

status VARCHAR(50) NOT NULL DEFAULT 'running',

started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
completed_at TIMESTAMPTZ,

input_summary TEXT,
output_summary TEXT,
error TEXT,

metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

);
