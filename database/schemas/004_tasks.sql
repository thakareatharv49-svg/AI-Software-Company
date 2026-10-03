# Task Schema

CREATE TABLE tasks (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
parent_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,

title VARCHAR(255) NOT NULL,
description TEXT NOT NULL,

status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
priority INTEGER NOT NULL DEFAULT 0,

assigned_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,

retry_count INTEGER NOT NULL DEFAULT 0,
max_retries INTEGER NOT NULL DEFAULT 5,

input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
output_data JSONB NOT NULL DEFAULT '{}'::jsonb,

error TEXT,

started_at TIMESTAMPTZ,
completed_at TIMESTAMPTZ,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

);

CREATE TABLE task_dependencies (
task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
depends_on_task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,

```
PRIMARY KEY(task_id, depends_on_task_id),

CHECK(task_id <> depends_on_task_id)
```

);
