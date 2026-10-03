# Tool Schema

CREATE TABLE tools (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
name VARCHAR(255) NOT NULL,
version VARCHAR(50) NOT NULL DEFAULT '1.0.0',

description TEXT,

input_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
output_schema JSONB NOT NULL DEFAULT '{}'::jsonb,

permissions JSONB NOT NULL DEFAULT '{}'::jsonb,

risk_level VARCHAR(50) NOT NULL DEFAULT 'low',

enabled BOOLEAN NOT NULL DEFAULT TRUE,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

UNIQUE(name, version)
```

);

CREATE TABLE agent_tools (
agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,

```
PRIMARY KEY(agent_id, tool_id)
```

);

CREATE TABLE tool_calls (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
agent_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE RESTRICT,

input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
output_data JSONB,

status VARCHAR(50) NOT NULL DEFAULT 'running',

error TEXT,

started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
completed_at TIMESTAMPTZ
```

);
