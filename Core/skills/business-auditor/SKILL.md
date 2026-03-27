---
name: business-auditor
description: Proactively audits business performance and financial data to generate a "Monday Morning CEO Briefing". Use to summarize weekly achievements, calculate revenue trends, and identify business bottlenecks from the /Done and Business_Goals.md files.
---

# Business Auditor (CEO Briefing)

## Overview
This skill transforms the AI from a reactive assistant into a proactive business partner. It performs a weekly cross-domain audit.

## Workflow
1. **Gather**: Read `Business_Goals.md` and all files in `/Done/` created in the last 7 days.
2. **Analyze**: Compare actual outcomes against target metrics.
3. **Draft**: Create a new report in `/Briefings/YYYY-MM-DD_CEO_Briefing.md`.
4. **Notify**: Add a summary highlight to the top of `Dashboard.md`.

## Data Sources
- `Business_Goals.md`: For Q1 targets.
- `/Done/*.md`: For completed tasks.
- `/Logs/*.json`: For technical audit trail.
