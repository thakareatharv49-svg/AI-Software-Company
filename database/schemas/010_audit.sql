# Audit Schema

CREATE TABLE audit_logs (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
company_id UUID REFERENCES companies(id) ON DELETE CASCADE,

actor_type VARCHAR(50) NOT NULL,
actor_id UUID,

action VARCHAR(255) NOT NULL,

resource_type VARCHAR(100),
resource_id UUID,

input_summary TEXT,
result_summary TEXT,

risk_level VARCHAR(50) NOT NULL DEFAULT 'low',

success BOOLEAN NOT NULL,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

);

CREATE INDEX idx_audit_created ON audit_logs(created_at);
CREATE INDEX idx_audit_actor ON audit_logs(actor_type, actor_id);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
