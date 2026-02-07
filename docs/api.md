# API Reference

Base URL: `http://127.0.0.1:<port>`

## Health

`GET /health`

Response:

```json
{ "status": "ok" }
```

## Projects

`GET /projects`

Response:

```json
{ "projects": [{ "id": "myproject", "path": "/path/to/project" }] }
```

`POST /project/create`

```json
{
  "name": "My Project",
  "seed": 42,
  "time_span_years": 2000,
  "root_dir": "/optional/root"
}
```

`POST /project/load`

```json
{ "project_dir": "/path/to/project" }
```

`POST /project/save`

```json
{ "project": { "project_name": "My Project", "...": "..." } }
```

`GET /project/{project_id}/tree`

Response:

```json
{ "languages": { "proto": { "...": "..." } } }
```

## Languages

`GET /project/{project_id}/languages`

`GET /project/{project_id}/language/{language_id}`

`POST /project/{project_id}/preview-child`

```json
{
  "parent_language_id": "proto",
  "child_name": "Daughter",
  "child_id": "daughter",
  "changeset": { "changeset_id": "chg_proto_daughter", "rules": [] },
  "override_settings": {}
}
```

`POST /project/{project_id}/create-child`

`POST /project/{project_id}/save-changeset`

`POST /project/{project_id}/changeset/generate`

`GET /project/{project_id}/compare?parent_id=proto&child_id=daughter&sample_count=20`

`POST /project/{project_id}/language/{language_id}/samples`

`POST /project/{project_id}/language/{language_id}/reroll`

## Meta

`GET /meta/presets`

`GET /meta/templates`
