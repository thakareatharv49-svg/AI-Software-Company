# GitHub Schema

CREATE TABLE repositories (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

provider VARCHAR(50) NOT NULL DEFAULT 'github',

external_id VARCHAR(255),
name VARCHAR(255) NOT NULL,
url TEXT NOT NULL,

default_branch VARCHAR(255) NOT NULL DEFAULT 'main',

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

);

CREATE TABLE pull_requests (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,

external_id VARCHAR(255),
title VARCHAR(500) NOT NULL,
url TEXT,

source_branch VARCHAR(255),
target_branch VARCHAR(255),

status VARCHAR(50) NOT NULL DEFAULT 'open',

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
merged_at TIMESTAMPTZ
```

);

CREATE TABLE releases (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

```
repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,

version VARCHAR(100) NOT NULL,
url TEXT,

status VARCHAR(50) NOT NULL DEFAULT 'created',

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

);
