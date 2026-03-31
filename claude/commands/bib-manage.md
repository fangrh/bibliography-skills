# /bib-manage

Manage bibliography operations including duplicate detection, metadata validation, cleanup, and migration.

## Usage

```
/bib-manage <action> [options]
```

## Actions

| Action | Description |
|---------|-------------|
| `check-duplicates` | Find duplicate entries in papis.bib based on DOI, title, and author matching |
| `sync-to-main` | Copy verified references from papis.bib to main.bib with corrected metadata |
| `validate-metadata` | Check and fix incomplete or incorrect metadata fields (DOI, year, journal, etc.) |
| `cleanup` | Remove unused entries and fix formatting issues |
| `migrate` | Import an existing .bib file into the papis-managed bibliography |

## Examples

Check for duplicate references:
```
/bib-manage check-duplicates
```

Sync verified references to main bibliography:
```
/bib-manage sync-to-main
```

Validate and fix metadata issues:
```
/bib-manage validate-metadata
```

Clean up unused entries and formatting:
```
/bib-manage cleanup
```

Import an existing bibliography:
```
/bib-manage migrate --input references.bib
```
