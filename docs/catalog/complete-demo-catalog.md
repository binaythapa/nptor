# Complete Demo Catalog

Run this command in a development database after applying migrations:

```powershell
python manage.py seed_nptor_catalog
```

The unified seed builds the existing professional Snowflake catalog, government catalog, academic/entrance preparation records, reusable domains/categories/questions/exams/tracks, and reusable courses.

## Coverage

- Professional: SnowPro Core, AWS Solutions Architect, Azure Administrator
- Academic/entrance: MBA, MBBS, IOE, Class 11
- Government: existing Nepal/India/USA government catalog programs, jobs, versions and stages
- Assessment: domains, hierarchical categories, original questions, choices, all supported question types, exams, allocations, tracks and track-exam ordering
- Learning: reusable courses with sections and article, video, practice and quiz lessons
- Idempotency: rerunning the unified command updates deterministic seed records without multiplying the catalog

The data is original development/demo content. It is not an import of official papers, paid coaching banks, textbooks, or copyrighted course material. Government and certification-specific requirements should always be checked against the current official source.
