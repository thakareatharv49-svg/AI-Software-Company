# Quality Schema

CREATE TABLE test_runs (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,

test_type VARCHAR(50) NOT NULL,

status VARCHAR(50) NOT NULL,

total_tests INTEGER NOT NULL DEFAULT 0,
passed_tests INTEGER NOT NULL DEFAULT 0,
failed_tests INTEGER NOT NULL DEFAULT 0,

output TEXT,

started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
completed_at TIMESTAMPTZ
```

);

CREATE TABLE security_scans (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

scanner VARCHAR(255) NOT NULL,
status VARCHAR(50) NOT NULL,

findings JSONB NOT NULL DEFAULT '[]'::jsonb,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

);

CREATE TABLE code_reviews (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

reviewer_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,

status VARCHAR(50) NOT NULL,

findings JSONB NOT NULL DEFAULT '[]'::jsonb,
summary TEXT,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
completed_at TIMESTAMPTZ
```

);
