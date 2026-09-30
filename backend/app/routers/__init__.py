from . import auth, duplicates, jobs, mappings, metrics, reports, uploads


routers = [auth.router, uploads.router, mappings.router, duplicates.router, metrics.router, reports.router, jobs.router]
