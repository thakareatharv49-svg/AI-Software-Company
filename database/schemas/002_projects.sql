# Project Schema

CREATE TABLE projects (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

```
name VARCHAR(255) NOT NULL,
slug VARCHAR(255) NOT NULL,
description TEXT,

state VARCHAR(50) NOT NULL DEFAULT 'IDEA',
priority INTEGER NOT NULL DEFAULT 0,

repository_url TEXT,
repository_id VARCHAR(255),

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
completed_at TIMESTAMPTZ,

UNIQUE(company_id, slug)
```

);

CREATE TABLE project_requirements (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

```
title VARCHAR(255) NOT NULL,
description TEXT NOT NULL,
requirement_type VARCHAR(50) NOT NULL DEFAULT 'functional',

priority INTEGER NOT NULL DEFAULT 0,
status VARCHAR(50) NOT NULL DEFAULT 'pending',

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

);

CREATE TABLE project_decisions (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

```
title VARCHAR(255) NOT NULL,
decision TEXT NOT NULL,
rationale TEXT,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

);
