# AI Tooling

Brief notes on how team members used AI-assisted development tools on FraudPulse.

## Macharia Kibandi

Macharia used Claude (Anthropic) throughout backend development of FraudPulse. The AI assistant was used to design and implement the alerts and cases domain — including models, schemas, services, and REST endpoints — and to maintain consistency across the stack as the schema evolved. Claude also wrote and updated the test suite as the codebase changed, assisted with frontend integration by updating Angular services and components to match the backend API.

All output was reviewed before use. Design decisions were made by Macharia with Claude providing analysis of the options and their trade-offs.

## Victor Asena

I used a mix of AI tools throughout my work on FraudPulse — **OpenAI Codex**, **GitHub Copilot**, **Claude Code**, and **Claude (web)** — across the frontend, authentication, deployment, and backend integration.

My work spanned scaffolding the Angular frontend (Tailwind UI and mock workflows) and its responsive layouts, wiring Supabase authentication (login, route guard, and JWT verification), and building out the CI/CD and OCI deployment pipeline — GHCR image builds, SSH-based deploys, and the Nginx/Docker runtime configuration. On the backend I wired the `POST /transactions` flow end to end and aligned the DB schema, added the overview aggregation endpoint, and implemented the access-request approval flow alongside the public demo dashboard.

I used Copilot and Codex mainly for in-editor completions and quick edits, and Claude Code and Claude web for larger changes, debugging deployment issues, and thinking through design trade-offs. All output was reviewed before it was committed, and the design decisions were mine, with the tools providing suggestions and analysis of the options.

## Olalekan Erinoso

_Entry pending._

## James Kilonzo

I used the **Cursor AI agent** to speed up day-to-day development across frontend and integration work, including the AI support assistant, UI updates, and project documentation. The agent helped me draft UI components, refine implementations, and iterate on fixes after code review while keeping changes aligned with existing project conventions.

For documentation, I prepared drafts with the required links and context, then used Cursor to accelerate writing the markdown files. I reviewed each document afterward to correct factual errors, broken links, and inconsistencies before committing.
