# Event Schema

CREATE TABLE events (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
event_type VARCHAR(100) NOT NULL,

company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,

payload JSONB NOT NULL DEFAULT '{}'::jsonb,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

);

CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_project ON events(project_id);
CREATE INDEX idx_events_task ON events(task_id);
CREATE INDEX idx_events_created ON events(created_at);
